# Kubernetes Deployment Manifests

Production-ready Kubernetes manifests for Glasswatch.

## Quick Start

```bash
# 1. Create namespace and secrets
kubectl apply -f namespace.yaml
kubectl create secret generic glasswatch-secrets --from-env-file=../../.env.production

# 2. Apply configuration
kubectl apply -f configmap.yaml

# 3. Deploy infrastructure (database, cache)
kubectl apply -f postgres.yaml
kubectl apply -f redis.yaml

# 4. Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app=glasswatch,component=postgres --timeout=300s
kubectl wait --for=condition=ready pod -l app=glasswatch,component=redis --timeout=300s

# 5. Deploy application
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# 6. Deploy autoscaling and policies
kubectl apply -f hpa.yaml
kubectl apply -f pdb.yaml
kubectl apply -f networkpolicy.yaml

# 7. Deploy backup jobs
kubectl apply -f cronjob-backup.yaml
```

## Manifest Overview

| File | Description |
|------|-------------|
| `namespace.yaml` | Glasswatch namespace |
| `configmap.yaml` | Non-sensitive configuration |
| `secrets.yaml` | Template for secrets (DO NOT commit with real values) |
| `deployment.yaml` | Backend application deployment |
| `service.yaml` | ClusterIP service for backend |
| `ingress.yaml` | Ingress with TLS termination |
| `hpa.yaml` | Horizontal Pod Autoscaler (3-10 replicas) |
| `pdb.yaml` | Pod Disruption Budget (min 2 available) |
| `postgres.yaml` | PostgreSQL StatefulSet |
| `redis.yaml` | Redis StatefulSet |
| `cronjob-backup.yaml` | Automated backup jobs |
| `networkpolicy.yaml` | Network security policies |

## Prerequisites

### Required Tools
- `kubectl` 1.28+
- Access to Kubernetes cluster
- `helm` (for installing nginx-ingress, cert-manager)

### Required Cluster Add-ons
- **Ingress Controller:** nginx-ingress, Traefik, or cloud provider
- **Cert Manager:** For automatic SSL certificates
- **Metrics Server:** For HPA to function
- **Storage Class:** `fast-ssd` or update manifests

## Configuration Steps

### 1. Update ConfigMap

Edit `configmap.yaml`:
- Set `BACKEND_CORS_ORIGINS` to your frontend domain
- Set `BACKUP_S3_BUCKET` if using S3 backups
- Update `AWS_REGION` if needed

### 2. Create Secrets

**Option A: From .env file**

```bash
kubectl create secret generic glasswatch-secrets \
  --from-literal=DATABASE_USER=glasswatch \
  --from-literal=DATABASE_PASSWORD=$(openssl rand -base64 32) \
  --from-literal=SECRET_KEY=$(openssl rand -hex 32) \
  --from-literal=BACKUP_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

**Option B: From file**

Create `.env.production`:
```bash
DATABASE_USER=glasswatch
DATABASE_PASSWORD=your-secure-password
SECRET_KEY=your-secret-key
BACKUP_ENCRYPTION_KEY=your-fernet-key
```

Then:
```bash
kubectl create secret generic glasswatch-secrets --from-env-file=.env.production
```

### 3. Update Ingress Domains

Edit `ingress.yaml` and replace:
- `api.glasswatch.example.com` → your API domain
- `app.glasswatch.example.com` → your frontend domain

### 4. Update Storage Class

If your cluster uses a different storage class than `fast-ssd`, update:
- `deployment.yaml` → `glasswatch-backup-pvc`
- `postgres.yaml` → `volumeClaimTemplates`
- `redis.yaml` → `volumeClaimTemplates`

### 5. Update Image Registry

Edit `deployment.yaml` and update:
```yaml
image: glasswatch/backend:latest
```

To your actual registry:
```yaml
image: your-registry.example.com/glasswatch/backend:v1.0.0
```

### 6. Update IAM Roles (AWS EKS)

Edit `deployment.yaml` and `cronjob-backup.yaml`, update:
```yaml
eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/glasswatch-backend
```

Replace `ACCOUNT_ID` with your AWS account ID.

## Deployment Order

Important: Deploy in this order to avoid dependency issues:

1. **Namespace & Secrets** (foundation)
2. **ConfigMap** (configuration)
3. **Infrastructure** (Postgres, Redis)
4. **Application** (Backend deployment, service)
5. **Networking** (Ingress, NetworkPolicies)
6. **Scaling** (HPA, PDB)
7. **Backup Jobs** (CronJobs)

## Post-Deployment

### Run Database Migrations

```bash
BACKEND_POD=$(kubectl get pod -n glasswatch -l app=glasswatch,component=backend -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n glasswatch $BACKEND_POD -- alembic upgrade head
```

### Verify Deployment

```bash
# Check all resources
kubectl get all -n glasswatch

# Check ingress
kubectl get ingress -n glasswatch

# Test health endpoint
curl https://api.glasswatch.example.com/health

# Check logs
kubectl logs -n glasswatch -l app=glasswatch,component=backend --tail=100
```

### Test Backup

```bash
# Trigger manual backup
kubectl create job --from=cronjob/glasswatch-daily-backup manual-backup-test -n glasswatch

# Check job status
kubectl get jobs -n glasswatch

# View backup logs
kubectl logs -n glasswatch job/manual-backup-test
```

## Scaling

### Manual Scaling

```bash
kubectl scale deployment glasswatch-backend --replicas=5 -n glasswatch
```

### Adjust HPA

Edit `hpa.yaml` to change min/max replicas or target CPU percentage.

## Monitoring

### Resource Usage

```bash
# Pod resource usage
kubectl top pods -n glasswatch

# Node resource usage
kubectl top nodes
```

### Logs

```bash
# Stream backend logs
kubectl logs -f -n glasswatch -l app=glasswatch,component=backend

# Stream all logs
kubectl logs -f -n glasswatch --all-containers=true

# Logs from specific pod
kubectl logs -n glasswatch <pod-name>
```

### Events

```bash
# Recent events
kubectl get events -n glasswatch --sort-by='.lastTimestamp'

# Watch events
kubectl get events -n glasswatch --watch
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n glasswatch

# Common issues:
# - ImagePullBackOff: Check image name and registry credentials
# - CrashLoopBackOff: Check logs for application errors
# - Pending: Check resource requests vs available capacity
```

### Database Connection Issues

```bash
# Test connectivity
kubectl exec -it <backend-pod> -n glasswatch -- nc -zv glasswatch-postgres 5432

# Check PostgreSQL logs
kubectl logs -n glasswatch <postgres-pod>

# Verify secrets
kubectl get secret glasswatch-secrets -n glasswatch -o jsonpath='{.data.DATABASE_PASSWORD}' | base64 -d
```

### Ingress Not Working

```bash
# Check ingress status
kubectl describe ingress glasswatch-ingress -n glasswatch

# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller

# Verify cert-manager
kubectl get certificate -n glasswatch
kubectl describe certificate glasswatch-tls-cert -n glasswatch
```

## Security Notes

### Secrets Management

- Never commit `secrets.yaml` with real values
- Use external secret management (AWS Secrets Manager, HashiCorp Vault)
- Rotate secrets regularly
- Use RBAC to limit secret access

### Network Policies

The included `networkpolicy.yaml` restricts:
- Backend pods can only access Postgres and Redis
- Postgres/Redis only accept connections from authorized pods
- All pods can access DNS and external HTTPS

Adjust based on your security requirements.

### Pod Security

All pods run as non-root user (UID 1000 or 999):
- `runAsNonRoot: true`
- `allowPrivilegeEscalation: false`
- Capabilities dropped

## High Availability Checklist

- [ ] Min 3 backend replicas (PDB ensures min 2 available)
- [ ] HPA configured for auto-scaling
- [ ] Pod anti-affinity rules (optional - spread across nodes)
- [ ] Database replication configured (Patroni or managed DB)
- [ ] Redis persistence enabled (AOF + RDB)
- [ ] Regular backup testing
- [ ] Monitoring and alerting configured
- [ ] Disaster recovery plan tested

## Clean Up

### Remove Application (Keep Data)

```bash
kubectl delete -f deployment.yaml
kubectl delete -f service.yaml
kubectl delete -f ingress.yaml
kubectl delete -f hpa.yaml
kubectl delete -f pdb.yaml
kubectl delete -f cronjob-backup.yaml
```

### Remove Everything (Including Data)

**⚠️ WARNING: This deletes all data permanently!**

```bash
kubectl delete namespace glasswatch
```

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [nginx-ingress Documentation](https://kubernetes.github.io/ingress-nginx/)
- [Glasswatch Deployment Guide](../../docs/DEPLOYMENT.md)
- [Disaster Recovery Plan](../../DISASTER_RECOVERY.md)

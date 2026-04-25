# Glasswatch Deployment Guide

Comprehensive guide for deploying Glasswatch to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Options](#deployment-options)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Docker Compose Deployment](#docker-compose-deployment)
5. [Environment Variables Reference](#environment-variables-reference)
6. [SSL/TLS Setup](#ssltls-setup)
7. [Database Migration](#database-migration)
8. [Rollback Procedure](#rollback-procedure)
9. [Scaling Guide](#scaling-guide)
10. [Troubleshooting](#troubleshooting)

---

## Railway Deployment (Managed Hosting)

Glasswatch runs in production on [Railway](https://railway.app). This is the fastest path to a hosted deployment.

### Services

| Service | URL |
|---|---|
| Backend | `https://glasswatch-production.up.railway.app` |
| Frontend | `https://frontend-production-ef3e.up.railway.app` |
| PostgreSQL | Managed by Railway |
| Redis | Managed by Railway |

### Deploy to Railway

1. Fork the repository
2. Create a new Railway project and connect your fork
3. Add the following services: **Backend** (Dockerfile.prod), **Frontend** (Dockerfile.frontend), **PostgreSQL**, **Redis**
4. Set required environment variables (see [Environment Variables Reference](#5-environment-variables-reference))
5. Railway will build and deploy automatically on push to `main`
6. Run database migrations after first deploy:
   ```bash
   railway run --service backend alembic upgrade head
   ```

### Required Railway Env Vars

```bash
DATABASE_URL=<Railway PostgreSQL connection string>
REDIS_URL=<Railway Redis connection string>
SECRET_KEY=<random hex string>
BACKEND_CORS_ORIGINS=https://frontend-production-ef3e.up.railway.app
```

Optional (SSO, simulators, etc.) — see full reference below.

---

## 1. Prerequisites

### Infrastructure Requirements

**Minimum (Single Server):**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 100 GB SSD
- Network: 100 Mbps

**Recommended (Production):**
- CPU: 8+ cores
- RAM: 16+ GB
- Storage: 500 GB NVMe SSD
- Network: 1 Gbps
- Load balancer (ALB, NLB, or nginx)

### Software Requirements

- **Kubernetes:** 1.28+ (for K8s deployment)
- **Docker:** 24.0+ and Docker Compose 2.20+ (for Docker deployment)
- **PostgreSQL:** 16+
- **Redis:** 7+
- **Python:** 3.11+
- **kubectl:** Latest (for K8s deployment)

### Domain & DNS

- Domain name for API: `api.glasswatch.example.com`
- Domain name for app: `app.glasswatch.example.com`
- DNS A records pointing to your load balancer or server IP

### SSL Certificate

- Option 1: Let's Encrypt (automated with cert-manager)
- Option 2: Commercial certificate from provider
- Option 3: Self-signed (dev/staging only)

---

## 2. Deployment Options

### Option A: Kubernetes (Recommended for Production)

**Pros:**
- High availability
- Auto-scaling
- Zero-downtime deployments
- Multi-cloud portable

**Cons:**
- More complex setup
- Higher infrastructure cost
- Requires K8s expertise

**Use when:**
- Expecting > 100 concurrent users
- Need 99.9%+ uptime
- Multiple environments (dev/staging/prod)

### Option B: Docker Compose (Good for Single Server)

**Pros:**
- Simple setup
- Lower cost
- Easy to understand

**Cons:**
- Single point of failure
- Manual scaling
- More downtime during updates

**Use when:**
- Small to medium deployment
- Budget constrained
- Single server is sufficient

---

## 3. Kubernetes Deployment

### 3.1 Cluster Setup

#### AWS EKS

```bash
# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Create cluster
eksctl create cluster \
  --name glasswatch-prod \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --managed
```

#### GKE (Google Cloud)

```bash
gcloud container clusters create glasswatch-prod \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-4 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10
```

#### DigitalOcean Kubernetes

```bash
doctl kubernetes cluster create glasswatch-prod \
  --region nyc1 \
  --version 1.28 \
  --count 3 \
  --size s-4vcpu-8gb
```

### 3.2 Install Prerequisites

#### cert-manager (for SSL certificates)

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.yaml

# Create Let's Encrypt ClusterIssuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ops@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

#### nginx-ingress

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2
```

#### metrics-server (for HPA)

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### 3.3 Configure Secrets

```bash
# Generate strong passwords
DATABASE_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -hex 32)
BACKUP_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Create secrets
kubectl create namespace glasswatch

kubectl create secret generic glasswatch-secrets \
  --namespace glasswatch \
  --from-literal=DATABASE_USER=glasswatch \
  --from-literal=DATABASE_PASSWORD="$DATABASE_PASSWORD" \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --from-literal=BACKUP_ENCRYPTION_KEY="$BACKUP_ENCRYPTION_KEY"

# Optional: Add WorkOS credentials
kubectl create secret generic glasswatch-secrets \
  --namespace glasswatch \
  --from-literal=WORKOS_API_KEY="your-workos-api-key" \
  --from-literal=WORKOS_CLIENT_ID="your-workos-client-id" \
  --dry-run=client -o yaml | kubectl apply -f -

# Optional: Add AWS credentials (or use IAM roles)
kubectl create secret generic glasswatch-secrets \
  --namespace glasswatch \
  --from-literal=AWS_ACCESS_KEY_ID="your-access-key" \
  --from-literal=AWS_SECRET_ACCESS_KEY="your-secret-key" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 3.4 Update ConfigMap

Edit `deploy/k8s/configmap.yaml` and update:

```yaml
data:
  # Update these values
  BACKEND_CORS_ORIGINS: "https://app.glasswatch.example.com"
  BACKUP_S3_BUCKET: "your-backup-bucket"
  AWS_REGION: "us-east-1"
```

### 3.5 Update Ingress Hostnames

Edit `deploy/k8s/ingress.yaml` and update:

```yaml
spec:
  tls:
  - hosts:
    - api.glasswatch.example.com  # Your actual domain
```

### 3.6 Deploy Application

```bash
# Apply all manifests
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/postgres.yaml
kubectl apply -f deploy/k8s/redis.yaml

# Wait for database to be ready
kubectl wait --namespace glasswatch \
  --for=condition=ready pod \
  --selector=app=glasswatch,component=postgres \
  --timeout=300s

# Deploy backend
kubectl apply -f deploy/k8s/deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/ingress.yaml
kubectl apply -f deploy/k8s/hpa.yaml
kubectl apply -f deploy/k8s/pdb.yaml
kubectl apply -f deploy/k8s/networkpolicy.yaml

# Deploy backup CronJobs
kubectl apply -f deploy/k8s/cronjob-backup.yaml
```

### 3.7 Run Database Migrations

```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pod -n glasswatch -l app=glasswatch,component=backend -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -n glasswatch $BACKEND_POD -- alembic upgrade head
```

### 3.8 Verify Deployment

```bash
# Check pod status
kubectl get pods -n glasswatch

# Check services
kubectl get svc -n glasswatch

# Check ingress
kubectl get ingress -n glasswatch

# Test health endpoint
curl https://api.glasswatch.example.com/health

# Check logs
kubectl logs -n glasswatch -l app=glasswatch,component=backend --tail=100
```

---

## 4. Docker Compose Deployment

### 4.1 Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in for group changes
```

### 4.2 Clone Repository

```bash
git clone https://github.com/your-org/glasswatch.git
cd glasswatch
```

### 4.3 Configure Environment

```bash
# Create .env file
cat > .env <<EOF
# Database
DATABASE_NAME=glasswatch
DATABASE_USER=glasswatch
DATABASE_PASSWORD=$(openssl rand -base64 32)
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Application Security
SECRET_KEY=$(openssl rand -hex 32)

# Backup
BACKUP_S3_BUCKET=your-backup-bucket
BACKUP_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# AWS (optional - for S3 backups)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# WorkOS (optional - for SSO)
WORKOS_API_KEY=your-workos-api-key
WORKOS_CLIENT_ID=your-workos-client-id

# CORS
BACKEND_CORS_ORIGINS=https://app.glasswatch.example.com

# Data directory
DATA_DIR=/opt/glasswatch/data
EOF

# Protect .env file
chmod 600 .env
```

### 4.4 Create Data Directories

```bash
sudo mkdir -p /opt/glasswatch/data/{postgres,redis,backups}
sudo chown -R $(id -u):$(id -g) /opt/glasswatch/data
```

### 4.5 Setup SSL Certificates

#### Option A: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install certbot

# Stop nginx if running
docker-compose -f docker-compose.prod.yml down nginx

# Get certificate
sudo certbot certonly --standalone \
  -d api.glasswatch.example.com \
  -d app.glasswatch.example.com \
  --email ops@example.com \
  --agree-tos

# Copy certificates to project
sudo mkdir -p ssl
sudo cp /etc/letsencrypt/live/api.glasswatch.example.com/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/api.glasswatch.example.com/privkey.pem ssl/
sudo chown -R $(id -u):$(id -g) ssl/
```

#### Option B: Self-signed (Dev/Staging Only)

```bash
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/privkey.pem \
  -out ssl/fullchain.pem \
  -subj "/CN=api.glasswatch.example.com"
```

### 4.6 Update nginx.conf

Edit `nginx.conf` and replace `api.glasswatch.example.com` with your actual domain.

### 4.7 Build and Start Services

```bash
# Build production image
docker-compose -f docker-compose.prod.yml build

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

### 4.8 Run Database Migrations

```bash
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 4.9 Verify Deployment

```bash
# Health check
curl https://api.glasswatch.example.com/health

# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Check backup service
docker-compose -f docker-compose.prod.yml exec backup python3 scripts/backup_cli.py status
```

---

## 5. Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_PASSWORD` | PostgreSQL password | `supersecretpassword` |
| `SECRET_KEY` | JWT signing key | `hex-encoded-random-string` |
| `BACKUP_ENCRYPTION_KEY` | Backup encryption key (Fernet) | `base64-encoded-fernet-key` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_NAME` | `glasswatch` | Database name |
| `DATABASE_USER` | `glasswatch` | Database user |
| `DATABASE_POOL_SIZE` | `20` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | `10` | Max overflow connections |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `BACKEND_CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins (comma-separated) |
| `AWS_REGION` | `us-east-1` | AWS region for S3/KMS |
| `AWS_ACCESS_KEY_ID` | - | AWS access key (or use IAM roles) |
| `AWS_SECRET_ACCESS_KEY` | - | AWS secret key (or use IAM roles) |
| `WORKOS_API_KEY` | - | WorkOS API key (for SSO) |
| `WORKOS_CLIENT_ID` | - | WorkOS client ID (for SSO) |
| `NVD_API_KEY` | - | NVD API key (for vulnerability data) |
| `BACKUP_S3_BUCKET` | - | S3 bucket for backups |
| `BACKUP_DIR` | `/var/backups/glasswatch` | Local backup directory |
| `PATCH_WEATHER_ENABLED` | `true` | Enable patch weather feature |
| `OPTIMIZATION_MAX_TIME_SECONDS` | `30` | Max time for optimization |
| `SIMULATOR_MODE` | `false` | Enable External API Simulators on port 8099 (dev/testing only — **do not enable in production**) |
| `WORKOS_API_KEY` | - | WorkOS API key (activates enterprise SSO; disables demo login) |
| `WORKOS_CLIENT_ID` | - | WorkOS client ID (required when `WORKOS_API_KEY` is set) |

---

## 6. SSL/TLS Setup

### Let's Encrypt with cert-manager (Kubernetes)

Automatic! cert-manager handles certificate issuance and renewal.

Verify:
```bash
kubectl get certificate -n glasswatch
kubectl describe certificate glasswatch-tls-cert -n glasswatch
```

### Let's Encrypt with certbot (Docker Compose)

Set up auto-renewal:

```bash
# Add cron job for renewal
sudo crontab -e

# Add this line:
0 3 * * * certbot renew --quiet --post-hook "docker-compose -f /path/to/glasswatch/docker-compose.prod.yml restart nginx"
```

### Commercial Certificate

1. Purchase certificate from provider (DigiCert, Sectigo, etc.)
2. Generate CSR:
   ```bash
   openssl req -new -newkey rsa:2048 -nodes \
     -keyout ssl/privkey.pem \
     -out ssl/cert.csr
   ```
3. Submit CSR to provider
4. Download certificate and intermediate chain
5. Combine:
   ```bash
   cat certificate.crt intermediate.crt > ssl/fullchain.pem
   ```

---

## 7. Database Migration

### Initial Migration (New Deployment)

```bash
# Kubernetes
kubectl exec -n glasswatch $BACKEND_POD -- alembic upgrade head

# Docker Compose
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Updating to New Version

```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild image (if needed)
docker-compose -f docker-compose.prod.yml build backend
# or for K8s: docker build -f Dockerfile.prod -t your-registry/glasswatch:v1.1.0 .

# 3. Run migrations BEFORE deploying new code
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 4. Deploy new version
docker-compose -f docker-compose.prod.yml up -d backend
```

### Rollback Migration

```bash
# Check migration history
docker-compose -f docker-compose.prod.yml exec backend alembic history

# Downgrade to specific revision
docker-compose -f docker-compose.prod.yml exec backend alembic downgrade <revision>

# Downgrade one step
docker-compose -f docker-compose.prod.yml exec backend alembic downgrade -1
```

---

## 8. Rollback Procedure

### Kubernetes Rollback

```bash
# Check rollout history
kubectl rollout history deployment/glasswatch-backend -n glasswatch

# Rollback to previous version
kubectl rollout undo deployment/glasswatch-backend -n glasswatch

# Rollback to specific revision
kubectl rollout undo deployment/glasswatch-backend --to-revision=3 -n glasswatch

# Watch rollback progress
kubectl rollout status deployment/glasswatch-backend -n glasswatch
```

### Docker Compose Rollback

```bash
# 1. Stop current version
docker-compose -f docker-compose.prod.yml down backend

# 2. Checkout previous version
git log --oneline  # Find commit hash
git checkout <commit-hash>

# 3. Rebuild and start
docker-compose -f docker-compose.prod.yml build backend
docker-compose -f docker-compose.prod.yml up -d backend

# 4. Rollback database if needed
docker-compose -f docker-compose.prod.yml exec backend alembic downgrade -1
```

---

## 9. Scaling Guide

### Kubernetes Horizontal Scaling

```bash
# Manual scaling
kubectl scale deployment glasswatch-backend --replicas=5 -n glasswatch

# HPA already configured (min 3, max 10, 70% CPU target)
kubectl get hpa -n glasswatch

# Adjust HPA
kubectl edit hpa glasswatch-backend-hpa -n glasswatch
```

### Kubernetes Vertical Scaling

Edit `deploy/k8s/deployment.yaml`:

```yaml
resources:
  requests:
    memory: "1Gi"    # Increase from 512Mi
    cpu: "500m"      # Increase from 250m
  limits:
    memory: "4Gi"    # Increase from 2Gi
    cpu: "2000m"     # Increase from 1000m
```

Apply:
```bash
kubectl apply -f deploy/k8s/deployment.yaml
```

### Docker Compose Scaling

```bash
# Add more backend replicas
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# Update nginx.conf to load balance:
upstream backend {
    server backend:8000;
    server backend:8001;
    server backend:8002;
}
```

### Database Scaling

**Read Replicas:**
- PostgreSQL supports streaming replication
- Configure read-only replicas for reporting/analytics
- Update connection pooling to route read queries to replicas

**Vertical Scaling:**
- Increase PostgreSQL resources in deployment YAML or docker-compose
- Monitor `shared_buffers`, `work_mem`, `maintenance_work_mem`

---

## 10. Troubleshooting

### Pod Not Starting (Kubernetes)

```bash
# Check pod status
kubectl get pods -n glasswatch

# Describe pod for events
kubectl describe pod <pod-name> -n glasswatch

# Check logs
kubectl logs <pod-name> -n glasswatch

# Check previous crash logs
kubectl logs <pod-name> -n glasswatch --previous
```

**Common issues:**
- `ImagePullBackOff`: Image not found or credentials missing
- `CrashLoopBackOff`: Application crash on startup (check logs)
- `Pending`: Insufficient resources or PVC not bound

### Database Connection Errors

```bash
# Test database connectivity
kubectl exec -it <backend-pod> -n glasswatch -- psql -h glasswatch-postgres -U glasswatch -d glasswatch

# Check PostgreSQL logs
kubectl logs -n glasswatch <postgres-pod>

# Check secrets
kubectl get secret glasswatch-secrets -n glasswatch -o yaml
```

### SSL Certificate Issues

```bash
# Check certificate status (K8s)
kubectl describe certificate glasswatch-tls-cert -n glasswatch

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager

# Manual certificate renewal (Docker Compose)
sudo certbot renew --force-renewal
```

### High Memory Usage

```bash
# Check pod memory (K8s)
kubectl top pods -n glasswatch

# Check container stats (Docker)
docker stats

# Check for memory leaks in logs
kubectl logs -n glasswatch <backend-pod> | grep -i "memory\|oom"
```

### Backup Failures

```bash
# Check backup CronJob status
kubectl get cronjobs -n glasswatch
kubectl get jobs -n glasswatch

# Check backup logs
kubectl logs -n glasswatch <backup-job-pod>

# Manual backup test
kubectl exec -n glasswatch <backend-pod> -- python3 scripts/backup_cli.py create
```

### Performance Issues

```bash
# Check database query performance
kubectl exec -it <postgres-pod> -n glasswatch -- psql -U glasswatch -d glasswatch \
  -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check connection pool status
kubectl logs <backend-pod> -n glasswatch | grep -i "pool\|connection"

# Check Redis cache hit rate
kubectl exec -it <redis-pod> -n glasswatch -- redis-cli INFO stats | grep hit
```

---

## Appendix A: Pre-Deployment Checklist

- [ ] DNS records configured
- [ ] SSL certificates obtained
- [ ] Secrets generated and stored securely
- [ ] Database credentials set
- [ ] CORS origins configured
- [ ] S3 bucket created (for backups)
- [ ] AWS IAM roles configured (if using)
- [ ] WorkOS configured (if using SSO)
- [ ] Firewall rules configured
- [ ] Monitoring/alerting setup
- [ ] Backup strategy tested
- [ ] Disaster recovery plan reviewed
- [ ] Load testing completed
- [ ] Security audit passed

---

## Appendix B: Useful Commands

### Kubernetes

```bash
# Watch pod status
kubectl get pods -n glasswatch -w

# Port forward for local access
kubectl port-forward -n glasswatch svc/glasswatch-backend 8000:8000

# Execute command in pod
kubectl exec -it <pod-name> -n glasswatch -- /bin/bash

# Get pod logs (streaming)
kubectl logs -f <pod-name> -n glasswatch

# Restart deployment
kubectl rollout restart deployment/glasswatch-backend -n glasswatch
```

### Docker Compose

```bash
# View logs (all services)
docker-compose -f docker-compose.prod.yml logs -f

# View logs (specific service)
docker-compose -f docker-compose.prod.yml logs -f backend

# Execute command in service
docker-compose -f docker-compose.prod.yml exec backend /bin/bash

# Restart service
docker-compose -f docker-compose.prod.yml restart backend

# Stop all services
docker-compose -f docker-compose.prod.yml down

# Remove all data (⚠️ DANGER)
docker-compose -f docker-compose.prod.yml down -v
```

---

**Document Version:** 1.0  
**Last Updated:** April 2026  
**Next Review:** Quarterly

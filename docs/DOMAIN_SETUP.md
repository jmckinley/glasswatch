# PatchGuide.ai Domain Setup

**Domain**: patchguide.ai  
**Status**: Owned ✅  
**Acquired**: 2026-04-19

## Next Steps

### 1. DNS Configuration
```
# Primary nameservers (update at registrar)
TBD - depends on hosting provider

# Required DNS records:
patchguide.ai.           A      <app-ip>
www.patchguide.ai.       CNAME  patchguide.ai.
api.patchguide.ai.       CNAME  patchguide.ai.
*.patchguide.ai.         CNAME  patchguide.ai.  # For tenant subdomains
```

### 2. Email Setup
```
# MX records for email
patchguide.ai.  MX  10  mx1.patchguide.ai.
patchguide.ai.  MX  20  mx2.patchguide.ai.

# SPF record
patchguide.ai.  TXT  "v=spf1 include:_spf.google.com ~all"

# DKIM (generate keys)
patchguide.ai.  TXT  "v=DKIM1; k=rsa; p=..."

# DMARC
_dmarc.patchguide.ai.  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@patchguide.ai"
```

### 3. SSL/TLS Certificates
```bash
# Let's Encrypt wildcard cert
certbot certonly --dns-route53 \
  -d patchguide.ai \
  -d *.patchguide.ai

# Or use AWS Certificate Manager for free certs
```

### 4. Multi-Tenant Architecture

**Subdomain Strategy**:
```
# Customer tenants
acme.patchguide.ai
globex.patchguide.ai
initech.patchguide.ai

# Platform services
app.patchguide.ai      # Main web app
api.patchguide.ai      # REST API
docs.patchguide.ai     # Documentation
status.patchguide.ai   # Status page
```

**Custom Domain Support**:
```
# Allow customers to use their own domains
patches.acmecorp.com -> CNAME acme.patchguide.ai
```

### 5. Email Addresses

**Operational**:
- support@patchguide.ai
- security@patchguide.ai
- abuse@patchguide.ai
- privacy@patchguide.ai

**Marketing**:
- hello@patchguide.ai
- sales@patchguide.ai
- demo@patchguide.ai

**Technical**:
- api@patchguide.ai (API notifications)
- noreply@patchguide.ai
- alerts@patchguide.ai

### 6. Hosting Options

**Option A: AWS Route 53 + CloudFront**
```
Route 53 -> CloudFront -> ALB -> EKS
- Global CDN
- DDoS protection
- Auto-scaling
```

**Option B: Vercel (Frontend) + AWS (Backend)**
```
Vercel (Next.js app) -> API Gateway -> Lambda/ECS
- Zero-config frontend
- Serverless scaling
```

**Option C: Full Kubernetes**
```
cert-manager + ingress-nginx -> K8s services
- Complete control
- Multi-cloud ready
```

### 7. Brand Assets

Create at patchguide.ai:
- Logo (SVG format)
- Favicon (32x32, 64x64, 128x128)
- Social media images (OpenGraph)
- Email templates

### 8. Legal Pages

Required at patchguide.ai:
- Terms of Service
- Privacy Policy
- Security Policy
- Acceptable Use Policy
- Cookie Policy
- GDPR compliance page

### 9. Status Page

**Setup statuspage.io or similar**:
- status.patchguide.ai
- Real-time uptime monitoring
- Incident communication
- Subscriber notifications

### 10. Marketing Site

**Landing page priorities**:
1. Hero: "AI-Powered Patch Optimization"
2. Problem: Vulnerability overload
3. Solution: Business-driven patching
4. Demo: Interactive patch scheduler
5. Pricing: Free trial, then tiered
6. CTA: "Start Free Trial"

## Timeline

**Week 1** (Now):
- [x] Acquire domain ✅
- [ ] Set up DNS at registrar
- [ ] Configure basic A record for landing page
- [ ] Set up Google Workspace or email provider

**Week 2**:
- [ ] SSL certificates
- [ ] Deploy landing page to Vercel
- [ ] Set up status page
- [ ] Create brand assets

**Week 3**:
- [ ] Production infrastructure (K8s/EKS)
- [ ] Subdomain routing
- [ ] API endpoints live
- [ ] Email templates

**Week 4**:
- [ ] Legal pages
- [ ] Support portal
- [ ] Documentation site
- [ ] Beta launch 🚀

## Contact

Owner: John McKinley  
Email: john@greatfallsventures.com  
GitHub: jmckinley/glasswatch
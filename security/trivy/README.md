# Trivy Security Scanner for ULL Infrastructure

## Overview

Trivy provides comprehensive security scanning for container images, filesystems, infrastructure-as-code, and Kubernetes clusters. It detects vulnerabilities, misconfigurations, secrets, and license issues.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Trivy Security Scanner                     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Container   │  │  Filesystem  │  │     IaC      │      │
│  │    Images    │  │    Scan      │  │    Scan      │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         └────────────────┼─────────────────┘               │
│                          ▼                                  │
│              ┌─────────────────────┐                       │
│              │   Report Generator  │                       │
│              │   (JSON/Table/SARIF)│                       │
│              └─────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Install Trivy

```bash
# macOS
brew install trivy

# Linux
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Docker
docker pull aquasec/trivy:latest
```

### Run Scans

```bash
# Scan all (filesystem + IaC + Kubernetes)
./security/trivy/trivy-scan.sh all all

# Scan specific image
./security/trivy/trivy-scan.sh ghcr.io/ull/engine:latest image

# Scan filesystem
./security/trivy/trivy-scan.sh . fs

# Scan IaC
./security/trivy/trivy-scan.sh . iac

# Scan Kubernetes cluster
./security/trivy/trivy-scan.sh cluster k8s
```

### Manual Trivy Commands

```bash
# Scan container image
trivy image ghcr.io/ull/engine:latest

# Scan with specific severities
trivy image --severity CRITICAL,HIGH ghcr.io/ull/engine:latest

# Scan filesystem
trivy fs --scanners vuln,secret,misconfig .

# Scan Kubernetes
trivy k8s --scanners vuln,misconfig cluster

# Scan IaC
trivy config .

# Output as SARIF for GitHub Code Scanning
trivy image --format sarif --output results.sarif ghcr.io/ull/engine:latest
```

## Deployment

### Kubernetes CronJob

```bash
# Deploy Trivy scanner
kubectl apply -f security/trivy/trivy-cronjob.yaml

# Check scan status
kubectl get cronjob -n security trivy-scanner

# View scan logs
kubectl logs -n security -l app=trivy --tail=100

# Get reports
kubectl cp security/trivy-scanner-xxx:/reports ./reports
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'ghcr.io/ull/engine:latest'
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'

- name: Upload Trivy scan results to GitHub Security tab
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: 'trivy-results.sarif'
```

## Configuration

### Severity Levels

| Level | Description | Action |
|-------|-------------|--------|
| CRITICAL | Immediate threat | Block deployment |
| HIGH | Significant risk | Require approval |
| MEDIUM | Moderate risk | Track and remediate |
| LOW | Minor issue | Best effort fix |

### Scan Types

| Type | Command | Use Case |
|------|---------|----------|
| Image | `trivy image` | Container images |
| Filesystem | `trivy fs` | Source code, configs |
| IaC | `trivy config` | K8s manifests, Terraform |
| Kubernetes | `trivy k8s` | Running cluster |
| Repository | `trivy repo` | Git repositories |

## Custom Rules

### Secret Detection

Custom secret rules are defined in `trivy-config.yaml`:

```yaml
secret:
  config:
    rules:
      - id: ull-api-key
        category: ULL
        severity: CRITICAL
        regex: 'ull[_-]?api[_-]?key["\s:=]+[a-zA-Z0-9]{32,}'
```

### Misconfiguration Policies

OPA-based policies are in `security/trivy/opa-policies/`.

## Report Format

Reports are generated in multiple formats:

- **JSON**: Machine-readable for automation
- **Table**: Human-readable summary
- **SARIF**: GitHub Code Scanning integration
- **HTML**: Detailed web report

## Ignoring Vulnerabilities

Add CVEs to `.trivyignore` with justification:

```yaml
CVE-2024-12345
Justification: Not applicable to our use case
Expires: 2024-12-31
```

## Troubleshooting

### High memory usage

```bash
# Limit concurrency
trivy image --parallel 1 ghcr.io/ull/engine:latest
```

### Database download issues

```bash
# Use mirror
trivy image --db-repository mirror.example.com/trivy-db ghcr.io/ull/engine:latest
```

### False positives

1. Verify the vulnerability is a false positive
2. Add to `.trivyignore` with justification
3. Set expiration date for re-evaluation

## Maintenance

### Update Trivy database

```bash
# Manual update
trivy image --download-db-only

# In Kubernetes
kubectl exec -n security deploy/trivy -- trivy --download-db-only
```

### Review ignored CVEs

```bash
# List ignored CVEs
cat security/trivy/.trivyignore

# Remove expired entries
# Edit .trivyignore and remove entries past expiration
```

## References

- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Trivy GitHub](https://github.com/aquasecurity/trivy)
- [Trivy Rules](https://github.com/aquasecurity/trivy/tree/main/pkg/fanal/secret)

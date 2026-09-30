# Falco Security Monitoring for ULL Infrastructure

## Overview

Falco provides runtime security monitoring for the Ultra-Low-Latency (ULL) infrastructure. It detects anomalous behavior, privilege escalation, container escapes, and other security threats in real-time.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Node 1    │  │   Node 2    │  │   Node 3    │         │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │         │
│  │ │  Falco  │ │  │ │  Falco  │ │  │ │  Falco  │ │         │
│  │ │ Daemon  │ │  │ │ Daemon  │ │  │ │ Daemon  │ │         │
│  │ └────┬────┘ │  │ └────┬────┘ │  │ └────┬────┘ │         │
│  └──────┼──────┘  └──────┼──────┘  └──────┼──────┘         │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          ▼                                   │
│              ┌─────────────────────┐                        │
│              │   Alert Manager     │                        │
│              │   (Prometheus)      │                        │
│              └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## Deployment

### Prerequisites

- Kubernetes cluster 1.24+
- Helm 3.x
- kubectl configured

### Install

```bash
# Create namespace
kubectl create namespace security

# Apply RBAC and ConfigMaps
kubectl apply -f security/falco/falco-configmap.yaml
kubectl apply -f security/falco/falco-deployment.yaml

# Or use Helm
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update
helm install falco falcosecurity/falco \
  -n security \
  -f security/falco/falco-values.yaml
```

### Verify

```bash
# Check Falco pods
kubectl get pods -n security -l app=falco

# View logs
kubectl logs -n security -l app=falco -f

# Check health
kubectl port-forward -n security svc/falco 8765:8765
curl http://localhost:8765/healthz
```

## Custom Rules

The following custom rules are defined for ULL infrastructure:

| Rule | Priority | Description |
|------|----------|-------------|
| `ULL_Sensitive_File_Access` | WARNING | Detects access to sensitive trading config files |
| `ULL_Outbound_Connection_Non_Standard` | CRITICAL | Detects unexpected outbound connections |
| `ULL_Process_Injection` | EMERGENCY | Detects process injection attempts |
| `ULL_Privilege_Escalation` | CRITICAL | Detects privilege escalation in containers |
| `ULL_Crypto_Mining` | EMERGENCY | Detects cryptomining patterns |
| `ULL_K8s_Secret_Access` | CRITICAL | Detects unauthorized K8s secret access |
| `ULL_Core_Dump` | WARNING | Detects core dump generation |
| `ULL_Network_Scan` | WARNING | Detects network scanning behavior |
| `ULL_Config_Modification` | WARNING | Detects runtime config changes |
| `ULL_Docker_Escape` | EMERGENCY | Detects container escape attempts |
| `ULL_High_Frequency_Exec` | WARNING | Detects abnormal process execution rates |
| `ULL_Syscall_Anomaly` | CRITICAL | Detects dangerous syscalls |

## Alert Routing

Alerts are routed to:
- **Prometheus Alertmanager** for aggregation and routing
- **File output** at `/var/log/falco/events.log` for audit
- **Stdout** for container log aggregation

## Tuning

### Exclude Noisy Rules

Edit `falco-configmap.yaml` and add to `falco.yaml`:

```yaml
skip_apps:
  - kube-system
  - security
```

### Adjust Thresholds

Modify rule conditions in `falco-configmap.yaml`:

```yaml
# Example: Increase threshold for high-frequency exec
evt.rate(proc.name, 10s) > 100  # was 50
```

## Maintenance

### Update Rules

```bash
kubectl create configmap falco-custom-rules \
  -n security \
  --from-file=custom-rules.yaml=security/falco/falco-configmap.yaml \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart Falco
kubectl rollout restart daemonset/falco -n security
```

### Upgrade Falco

```bash
helm upgrade falco falcosecurity/falco \
  -n security \
  -f security/falco/falco-values.yaml
```

## Troubleshooting

### Falco not detecting events

```bash
# Check if modern BPF is working
kubectl exec -n security -it ds/falco -- cat /sys/kernel/security/lsm

# Check Falco logs
kubectl logs -n security -l app=falco --tail=100

# Verify rules are loaded
kubectl exec -n security -it ds/falco -- falco --list
```

### High CPU usage

```bash
# Reduce syscall capture rate
# Edit falco-values.yaml:
falco:
  syscall_event_drops:
    rate: 0.1  # was 0.03333
```

## References

- [Falco Documentation](https://falco.org/docs/)
- [Falco Rules](https://github.com/falcosecurity/rules)
- [Falco Helm Chart](https://github.com/falcosecurity/charts)

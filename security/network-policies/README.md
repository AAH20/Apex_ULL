# Network Policies for ULL Infrastructure

## Overview

Network policies enforce zero-trust networking for the Ultra-Low-Latency (ULL) infrastructure. All traffic is denied by default, and only explicitly allowed traffic patterns are permitted.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ULL Namespace                            │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Gateway   │◄──►│   Engine    │◄──►│  Market Data│     │
│  │             │    │             │    │             │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                  │             │
│         │           ┌──────┴──────┐           │             │
│         │           │             │           │             │
│         │      ┌────┴───┐   ┌────┴───┐      │             │
│         │      │  DB    │   │ Cache  │      │             │
│         │      └────────┘   └────────┘      │             │
│         │                                    │             │
│  ┌──────┴──────┐                      ┌──────┴──────┐     │
│  │   Ingress   │                      │  External   │     │
│  │  Controller │                      │   APIs      │     │
│  └─────────────┘                      └─────────────┘     │
│                                                              │
│  Default: DENY ALL                                           │
│  Allowed: Explicitly defined traffic patterns                │
└─────────────────────────────────────────────────────────────┘
```

## Deployment

### Prerequisites

- Kubernetes cluster with NetworkPolicy support (Calico, Cilium, or Weave)
- kubectl configured

### Install

```bash
# Create namespace
kubectl create namespace ull

# Apply network policies
kubectl apply -f security/network-policies/ull-network-policies.yaml

# Verify
kubectl get networkpolicies -n ull
```

### Verify

```bash
# List all network policies
kubectl get networkpolicies -n ull

# Check policy details
kubectl describe networkpolicy default-deny-all -n ull

# Test connectivity (should fail)
kubectl run test-pod --image=busybox -n ull --rm -it -- ping 8.8.8.8

# Test allowed connectivity (should work)
kubectl run test-pod --image=busybox -n ull --rm -it -- nslookup kubernetes.default
```

## Policy Categories

### Default Deny

| Policy | Description |
|--------|-------------|
| `default-deny-all` | Denies all ingress and egress traffic |

### DNS

| Policy | Description |
|--------|-------------|
| `allow-dns` | Allows DNS resolution to kube-system |

### Ingress

| Policy | Description |
|--------|-------------|
| `allow-ingress-controller` | Allows traffic from ingress-nginx to gateway |
| `allow-kubelet-health-checks` | Allows health checks from node CIDR |
| `allow-prometheus-monitoring` | Allows Prometheus scraping |

### Internal Communication

| Policy | Description |
|--------|-------------|
| `allow-internal-communication` | Allows traffic between ULL components |

### External Egress

| Policy | Description |
|--------|-------------|
| `allow-external-market-data` | Allows market data provider connections |
| `allow-external-apis` | Allows external API connections |
| `allow-fix-egress` | Allows FIX protocol connections |
| `allow-payment-networks` | Allows payment network connections |
| `allow-smtp-relay` | Allows SMTP relay connections |
| `allow-ntp` | Allows NTP time synchronization |
| `allow-container-registry` | Allows container registry pulls |

### Internal Services

| Policy | Description |
|--------|-------------|
| `allow-database-egress` | Allows database connections |
| `allow-redis-egress` | Allows Redis cache connections |
| `allow-kafka-egress` | Allows Kafka connections |
| `allow-elasticsearch-egress` | Allows Elasticsearch connections |

### Observability

| Policy | Description |
|--------|-------------|
| `allow-logging-egress` | Allows log shipping |
| `allow-metrics-egress` | Allows metrics shipping |
| `allow-tracing-egress` | Allows trace shipping |

### Backup

| Policy | Description |
|--------|-------------|
| `allow-backup-egress` | Allows backup storage connections |

## Traffic Flow

### Inbound Traffic

```
Internet → Ingress Controller → Gateway → Engine → Database/Cache
```

### Outbound Traffic

```
Engine → External APIs (HTTPS)
Engine → Market Data Providers (HTTPS/WSS)
Engine → Payment Networks (HTTPS)
Engine → SMTP Relay (SMTP)
All → NTP (UDP 123)
All → Container Registry (HTTPS)
```

### Internal Traffic

```
Gateway ↔ Engine ↔ Market Data
Engine → Database (PostgreSQL)
Engine → Cache (Redis)
Engine → Kafka
Engine → Elasticsearch
```

## Testing

### Test Default Deny

```bash
# This should FAIL (no egress allowed by default)
kubectl run test-deny --image=busybox -n ull --rm -it -- ping 8.8.8.8
```

### Test DNS Allow

```bash
# This should WORK (DNS is allowed)
kubectl run test-dns --image=busybox -n ull --rm -it -- nslookup kubernetes.default
```

### Test Internal Communication

```bash
# This should WORK (internal communication is allowed)
kubectl run test-internal --image=busybox -n ull --rm -it -- wget -O- http://ull-engine:8080/healthz
```

### Test External Block

```bash
# This should FAIL (no external egress by default)
kubectl run test-external --image=busybox -n ull --rm -it -- wget -O- http://example.com
```

## Troubleshooting

### Pods can't communicate

```bash
# Check if network policies are applied
kubectl get networkpolicies -n ull

# Check if CNI supports NetworkPolicy
kubectl get pods -n kube-system | grep -E "calico|cilium|weave"

# Check policy details
kubectl describe networkpolicy <policy-name> -n ull

# Check pod labels (policies use label selectors)
kubectl get pods -n ull --show-labels
```

### DNS not working

```bash
# Verify DNS policy exists
kubectl get networkpolicy allow-dns -n ull

# Check CoreDNS is running
kubectl get pods -n kube-system -l k8s-app=coredns

# Test DNS from a pod
kubectl run test-dns --image=busybox -n ull --rm -it -- nslookup kubernetes.default
```

### External connections blocked

```bash
# Verify egress policy exists
kubectl get networkpolicy allow-external-apis -n ull

# Check pod labels match policy selector
kubectl get pods -n ull --show-labels

# Check destination IP is not in except CIDR
kubectl exec -n ull <pod-name> -- wget -O- http://<external-ip>
```

## Maintenance

### Add New Policy

1. Create new NetworkPolicy manifest
2. Apply to cluster
3. Test connectivity
4. Update documentation

### Modify Existing Policy

1. Edit policy manifest
2. Apply changes
3. Verify no disruption
4. Update documentation

### Remove Policy

1. Delete policy
2. Verify traffic is blocked by default-deny
3. Update documentation

## Security Considerations

### Principle of Least Privilege

- All traffic is denied by default
- Only explicitly allowed traffic is permitted
- Policies use label selectors for flexibility

### Segmentation

- Internal components can only talk to each other
- External access is restricted to specific components
- Observability traffic is isolated

### Monitoring

- Falco monitors network anomalies
- Trivy scans for misconfigurations
- OPA enforces policy compliance

## References

- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Calico Network Policies](https://docs.tigera.io/calico/latest/security/kubernetes-network-policy)
- [Cilium Network Policies](https://docs.cilium.io/en/stable/security/policy/)

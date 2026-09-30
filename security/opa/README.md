# OPA Gatekeeper Security Policies for ULL Infrastructure

## Overview

OPA Gatekeeper provides policy-based admission control for Kubernetes. It enforces security policies on all resources created in the cluster, ensuring compliance with ULL security standards.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes API Server                     │
│                          │                                   │
│                          ▼                                   │
│              ┌─────────────────────┐                        │
│              │  Gatekeeper Webhook │                        │
│              │  (Mutating/Validating)│                       │
│              └──────────┬──────────┘                        │
│                         │                                    │
│                         ▼                                    │
│              ┌─────────────────────┐                        │
│              │  OPA Engine         │                        │
│              │  (Policy Evaluation)│                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│                         ▼                                    │
│              ┌─────────────────────┐                        │
│              │  Constraint         │                        │
│              │  Templates          │                        │
│              └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## Deployment

### Prerequisites

- Kubernetes cluster 1.24+
- kubectl configured

### Install Gatekeeper

```bash
# Install Gatekeeper
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.17/deploy/gatekeeper.yaml

# Wait for deployment
kubectl wait --for=condition=available --timeout=300s deployment/gatekeeper-controller-manager -n gatekeeper-system

# Apply ULL constraints
kubectl apply -f security/opa/constraints/ull-constraint-templates.yaml
kubectl apply -f security/opa/constraints/ull-constraints.yaml
kubectl apply -f security/opa/gatekeeper-config.yaml
```

### Verify Installation

```bash
# Check Gatekeeper pods
kubectl get pods -n gatekeeper-system

# List constraint templates
kubectl get constrainttemplates

# List constraints
kubectl get constraints

# Check constraint details
kubectl describe constraint ull-must-have-labels
```

## Constraint Templates

| Template | Description |
|----------|-------------|
| `ULLRequiredLabels` | Requires specific labels on resources |
| `ULLRequiredProbes` | Requires liveness/readiness probes |
| `ULLAllowedRepos` | Restricts container registries |
| `ULLRequiredResources` | Requires resource limits |
| `ULLForbiddenImages` | Blocks specific images |
| `ULLRequiredSecurityContext` | Enforces security context |
| `ULLRequiredNetworkPolicy` | Requires NetworkPolicies |
| `ULLForbiddenCapabilities` | Blocks dangerous capabilities |
| `ULLRequiredPodDisruptionBudget` | Requires PDBs |

## Constraints

| Constraint | Template | Scope |
|------------|----------|-------|
| `ull-must-have-labels` | ULLRequiredLabels | All ULL resources |
| `ull-must-have-probes` | ULLRequiredProbes | ULL pods |
| `ull-restricted-repos` | ULLAllowedRepos | ULL pods |
| `ull-must-have-resources` | ULLRequiredResources | ULL pods |
| `ull-forbidden-images` | ULLForbiddenImages | ULL pods |
| `ull-security-context` | ULLRequiredSecurityContext | ULL pods |
| `ull-forbidden-capabilities` | ULLForbiddenCapabilities | ULL pods |
| `ull-pdb-required` | ULLRequiredPodDisruptionBudget | ULL deployments |
| `ull-network-policy-required` | ULLRequiredNetworkPolicy | ULL NetworkPolicies |

## Policy Categories

### Pod Security

- **Run as non-root**: Containers must not run as root
- **Read-only root filesystem**: Prevents runtime modifications
- **No privilege escalation**: Blocks `allowPrivilegeEscalation`
- **Drop all capabilities**: Removes unnecessary Linux capabilities
- **No host namespaces**: Blocks hostNetwork, hostPID, hostIPC

### Resource Management

- **Resource limits**: CPU and memory limits required
- **Resource requests**: CPU and memory requests required
- **PodDisruptionBudget**: Ensures high availability

### Image Security

- **Approved registries**: Only trusted image registries
- **No latest tag**: Requires specific image tags
- **No forbidden images**: Blocks known vulnerable images

### Network Security

- **NetworkPolicies required**: All namespaces must have policies
- **No hostPath volumes**: Prevents host filesystem access
- **No emptyDir for data**: Requires persistent volumes

### Monitoring

- **Liveness probes**: Ensures container health
- **Readiness probes**: Ensures traffic routing
- **Prometheus metrics**: Required for observability

## Testing Policies

### Test Valid Deployment

```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: valid-pod
  labels:
    app.kubernetes.io/name: test
    app.kubernetes.io/component: test
    app.kubernetes.io/part-of: ull
    app.kubernetes.io/managed-by: helm
spec:
  securityContext:
    runAsNonRoot: true
    readOnlyRootFilesystem: true
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: test
    image: ghcr.io/ull/engine:v1.0.0
    imagePullPolicy: Always
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
          - ALL
    resources:
      limits:
        cpu: "1"
        memory: 512Mi
      requests:
        cpu: 100m
        memory: 128Mi
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8080
      initialDelaySeconds: 10
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /readyz
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 5
EOF
```

### Test Invalid Deployment

```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: invalid-pod
  labels:
    app.kubernetes.io/part-of: ull
spec:
  containers:
  - name: test
    image: nginx:latest
EOF
```

This should fail with multiple constraint violations.

## Troubleshooting

### Constraint not enforcing

```bash
# Check if constraint is registered
kubectl get constrainttemplate ullrequiredlabels

# Check constraint status
kubectl describe constraint ull-must-have-labels

# Check Gatekeeper logs
kubectl logs -n gatekeeper-system -l control-plane=controller-manager
```

### False positives

1. Review the constraint template logic
2. Add exceptions to the constraint
3. Update the Rego policy

### Performance issues

```bash
# Check Gatekeeper resource usage
kubectl top pods -n gatekeeper-system

# Increase resources
kubectl edit deployment gatekeeper-controller-manager -n gatekeeper-system
```

## Maintenance

### Update Constraints

```bash
# Edit constraint
kubectl edit constraint ull-must-have-labels

# Or apply updated file
kubectl apply -f security/opa/constraints/ull-constraints.yaml
```

### Add New Policies

1. Create new ConstraintTemplate
2. Create new Constraint
3. Test in non-production first
4. Deploy to production

### Audit Policies

```bash
# List all constraints
kubectl get constraints -o json

# Check constraint violations
kubectl get constraints -o json | jq '.items[].status.violations'
```

## References

- [OPA Gatekeeper Documentation](https://open-policy-agent.github.io/gatekeeper/)
- [Rego Language](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [Gatekeeper Library](https://github.com/open-policy-agent/gatekeeper-library)

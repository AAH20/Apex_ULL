# OPA Gatekeeper deployment for ULL infrastructure
# Namespace: gatekeeper-system

# Install Gatekeeper
# kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.17/deploy/gatekeeper.yaml

# Then apply ULL-specific constraints
# kubectl apply -f security/opa/constraints/ull-constraint-templates.yaml
# kubectl apply -f security/opa/constraints/ull-constraints.yaml
# kubectl apply -f security/opa/gatekeeper-config.yaml

# Verify installation
# kubectl get pods -n gatekeeper-system
# kubectl get constrainttemplates
# kubectl get constraints

# Test a deployment
# kubectl apply -f - <<EOF
# apiVersion: v1
# kind: Pod
# metadata:
#   name: test-pod
#   labels:
#     app.kubernetes.io/part-of: ull
# spec:
#   containers:
#   - name: test
#     image: nginx:latest
# EOF

# This should fail with constraint violations

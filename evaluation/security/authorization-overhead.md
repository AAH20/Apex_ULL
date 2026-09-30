# Authorization Overhead Evaluation

## 1. Scope

Measures latency introduced by access control decisions in ULL infrastructure:
- **RBAC**: Role-based access control resolution
- **ABAC**: Attribute-based access control with policy evaluation
- **PBAC**: Policy-based access control (OPA, Cedar, Casbin)
- **ReBAC**: Relationship-based access control (Google Zanzibar model)
- **ACL**: Access control list lookups

---

## 2. Measurement Methodology

### 2.1 RBAC Resolution

| Phase | What to Measure | How |
|-------|----------------|-----|
| Role lookup | User → roles mapping | Cache/DB timing |
| Permission resolution | Roles → permissions expansion | In-memory set operations |
| Hierarchical role resolution | Role inheritance traversal | Graph traversal timing |
| Permission check | Final allow/deny decision | Instrumented middleware |

**Tooling:**
```python
# Example: RBAC resolution micro-benchmark
import time

def measure_rbac(user_id, resource, action):
    start = time.perf_counter_ns()
    roles = role_cache.get(user_id)           # Role lookup
    permissions = set()
    for role in roles:
        permissions |= role_permissions[role]  # Permission expansion
    allowed = (resource, action) in permissions  # Decision
    elapsed = time.perf_counter_ns() - start
    return elapsed, allowed
```

### 2.2 ABAC / Policy Engine Evaluation

| Phase | What to Measure | How |
|-------|----------------|-----|
| Policy retrieval | Load policy from store | OPA/Cedar/Casbin timing |
| Attribute resolution | Subject/resource/environment attributes | Context gathering |
| Policy evaluation | Rego / Cedar / Casbin model evaluation | Engine-specific benchmark |
| Decision caching | Cached decision hit rate | Cache metrics |

**Tooling:**
```bash
# OPA policy evaluation timing
curl -o /dev/null -s -w "total:%{time_total}\n" \
  -X POST http://localhost:8181/v1/data/authz/allow \
  -H "Content-Type: application/json" \
  -d '{"input":{"user":"alice","action":"read","resource":"doc1"}}'

# Cedar policy validation
# (use cedar-cli or application instrumentation)

# Casbin model evaluation
# (instrumented Enforcer.Enforce() timing)
```

### 2.3 ReBAC / Relationship-Based

| Phase | What to Measure | How |
|-------|----------------|-----|
| Relationship lookup | User → object relationship graph | Graph DB / Spicedb timing |
| Permission expansion | Relationship → permission traversal | Recursive graph walk |
| Consistency check | Zanzibar-style consistency token | Spicedb / Google Zanzibar |

**Tooling:**
```bash
# SpiceDB permission check
time spicedb permission check \
  --endpoint=localhost:50051 \
  --insecure \
  document:doc1#viewer@user:alice

# SpiceDB relationship read
time spicedb relationship read \
  --endpoint=localhost:50051 \
  --insecure \
  document:doc1#viewer
```

---

## 3. Benchmark Standards

| Standard | Relevance |
|----------|-----------|
| **NIST SP 800-162 (ABAC)** | Attribute-based access control definition |
| **NIST SP 800-178 (RBAC)** | Role-based access control |
| **XACML 3.0** | eXtensible Access Control Markup Language |
| **ALFA** | Abbreviated Language for Authorization |
| **Open Policy Agent (Rego)** | Cloud-native policy engine |
| **AWS Cedar** | AWS's policy language for authorization |
| **Google Zanzibar** | Relationship-based access control model |
| **OAuth 2.0 Scope** | Scope-based authorization |
| **UMA 2.0 (User-Managed Access)** | Authorization for resource owners |

---

## 4. Industry Averages

### 4.1 RBAC Resolution Latency

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| Role lookup (in-memory cache) | 0.01–0.05 ms | Hash map lookup |
| Role lookup (Redis) | 0.05–0.2 ms | Network + cache |
| Role lookup (database) | 0.5–5 ms | Disk I/O bound |
| Permission expansion (flat) | 0.01–0.1 ms | Set union operations |
| Permission expansion (hierarchical) | 0.05–0.5 ms | Graph traversal |
| Full RBAC decision (cached) | 0.05–0.2 ms | End-to-end |
| Full RBAC decision (uncached) | 0.5–5 ms | With DB lookups |

### 4.2 ABAC / Policy Engine Latency

| Engine | Typical Latency | Notes |
|--------|----------------|-------|
| OPA (Rego, simple policy) | 0.1–1 ms | Single rule evaluation |
| OPA (Rego, complex policy) | 1–10 ms | Multiple rules, data joins |
| OPA (bundle cached) | 0.05–0.5 ms | Pre-loaded policies |
| Cedar (simple) | 0.05–0.5 ms | Single policy |
| Cedar (complex) | 0.5–5 ms | Multiple policies, hierarchy |
| Casbin (RBAC model) | 0.05–0.5 ms | In-memory enforcement |
| Casbin (ABAC model) | 0.5–5 ms | Attribute matching |
| XACML PDP | 1–10 ms | XML parsing + evaluation |

### 4.3 ReBAC / Relationship-Based Latency

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| SpiceDB permission check | 0.5–2 ms | Single relationship |
| SpiceDB permission check (deep) | 2–10 ms | Multi-level traversal |
| SpiceDB relationship read | 0.2–1 ms | Direct lookup |
| Google Zanzibar (Check) | 1–5 ms | Production at scale |
| Google Zanzibar (Expand) | 0.5–2 ms | Permission expansion |

### 4.4 Decision Caching Impact

| Cache Type | Hit Latency | Miss Latency | Typical Hit Rate |
|------------|-------------|--------------|-----------------|
| In-memory LRU | 0.01–0.05 ms | 0.5–5 ms | 80–95% |
| Redis cache | 0.05–0.2 ms | 0.5–5 ms | 85–98% |
| No cache | N/A | 0.5–5 ms | 0% |

---

## 5. ULL Optimization Strategies

| Strategy | Applicability | Expected Savings |
|----------|--------------|-----------------|
| Pre-computed permission sets | RBAC | Eliminate runtime expansion |
| Decision caching (in-memory) | All authz | 10–100x on cache hits |
| Decision caching (Redis) | Distributed authz | 5–20x on cache hits |
| Policy compilation (OPA → WASM) | OPA/Rego | 2–5x evaluation speed |
| Cedar over OPA for simple policies | AWS environments | 2–10x faster evaluation |
| Relationship pre-computation | ReBAC | Avoid runtime graph traversal |
| Attribute caching | ABAC | Reduce context gathering |
| Async authorization (non-blocking) | Non-critical paths | Don't block request path |
| Edge authorization | CDN/edge | Offload from origin |
| Batch authorization | Multiple resources | Amortize policy evaluation |

---

## 6. Measurement Checklist

- [ ] RBAC role lookup latency (cache, Redis, DB)
- [ ] RBAC permission expansion latency (flat, hierarchical)
- [ ] Full RBAC decision latency (cached, uncached)
- [ ] OPA/Rego policy evaluation latency (simple, complex)
- [ ] Cedar policy evaluation latency (simple, complex)
- [ ] Casbin enforcement latency (RBAC, ABAC models)
- [ ] SpiceDB permission check latency (shallow, deep)
- [ ] XACML PDP evaluation latency
- [ ] Decision cache hit rate and latency
- [ ] Policy bundle load time (OPA)
- [ ] Attribute resolution latency (ABAC)
- [ ] Relationship graph traversal latency (ReBAC)
- [ ] Authorization middleware overhead (p50, p99, p999)
- [ ] Cold vs. warm policy cache comparison
- [ ] Concurrent authorization throughput

# Authentication Overhead Evaluation

## 1. Scope

Measures latency introduced by identity verification in ULL infrastructure:
- **Token-based**: JWT validation, OAuth 2.0 token introspection, API key verification
- **Session-based**: Session lookup, session validation, cookie verification
- **Certificate-based**: mTLS client cert validation, certificate chain verification
- **Multi-factor**: TOTP, WebAuthn/FIDO2, push notification round-trips
- **Identity provider**: OIDC discovery, IdP round-trip, SAML assertion validation

---

## 2. Measurement Methodology

### 2.1 Token-Based Authentication

| Phase | What to Measure | How |
|-------|----------------|-----|
| JWT signature verification | Ed25519 / RS256 / ES256 verify | Micro-benchmark with cached JWKS |
| JWT claim validation | exp, iss, aud, nbf checks | Application timing |
| OAuth token introspection | `/introspect` endpoint round-trip | `curl -w '%{time_total}'` |
| API key lookup | Database / cache lookup | Instrumented middleware |
| JWKS fetch & cache | Key rotation fetch latency | `curl` + cache timing |

**Tooling:**
```bash
# JWT verification micro-benchmark
# (language-specific: e.g., python-jose, jwt-go, jsonwebtoken)

# OAuth introspection timing
curl -o /dev/null -s -w "dns:%{time_namelookup} tcp:%{time_connect} \
  tls:%{time_appconnect} ttfb:%{time_starttransfer} total:%{time_total}\n" \
  -X POST https://idp.example.com/introspect \
  -d "token=$TOKEN"

# API key lookup (Redis)
redis-cli --latency-history -i 1
```

### 2.2 Session-Based Authentication

| Phase | What to Measure | How |
|-------|----------------|-----|
| Session ID extraction | Cookie/header parse | Application timing |
| Session store lookup | Redis/DB GET | `redis-cli --latency` or DB timing |
| Session validation | Expiry, IP binding, user agent check | Application timing |
| Session refresh | Sliding expiration update | Write latency to session store |
| Cookie signing | HMAC-SHA256 cookie verify | Micro-benchmark |

### 2.3 Certificate-Based Authentication

| Phase | What to Measure | How |
|-------|----------------|-----|
| Client cert extraction | TLS layer handshake | OpenSSL s_server timing |
| Chain validation | X.509 path building | `openssl verify -CAfile` |
| CRL/OCSP check | Revocation status | `openssl ocsp` timing |
| mTLS handshake total | Full mutual TLS | `openssl s_time` with client cert |

### 2.4 Multi-Factor Authentication

| Phase | What to Measure | How |
|-------|----------------|-----|
| TOTP verification | HMAC-SHA1 window check | Micro-benchmark |
| WebAuthn/FIDO2 assertion | Signature verify + counter check | Browser/Server timing |
| Push notification | Round-trip to device | End-to-end timing |
| SMS/Email OTP | Generation + delivery + verify | End-to-end timing |

---

## 3. Benchmark Standards

| Standard | Relevance |
|----------|-----------|
| **RFC 7519 (JWT)** | JSON Web Token format and validation |
| **RFC 7517 (JWK)** | JSON Web Key format |
| **RFC 6749 (OAuth 2.0)** | Token endpoint, grant types |
| **RFC 7662 (Token Introspection)** | OAuth 2.0 token introspection |
| **RFC 7009 (Token Revocation)** | Token revocation endpoint |
| **OpenID Connect Core 1.0** | ID token validation, discovery |
| **FIDO2 / WebAuthn** | Passwordless authentication |
| **NIST SP 800-63B** | Digital identity guidelines, AAL levels |
| **SAML 2.0** | XML-based authentication assertions |

---

## 4. Industry Averages

### 4.1 JWT Verification Latency

| Algorithm | Verify Latency | Sign Latency | Notes |
|-----------|---------------|-------------|-------|
| Ed25519 | 0.05–0.2 ms | 0.05–0.2 ms | Fastest asymmetric |
| ES256 (P-256) | 0.2–1 ms | 0.3–1.5 ms | ECDSA on P-256 |
| RS256 (RSA-2048) | 0.1–0.5 ms | 1–5 ms | Fast verify, slow sign |
| RS256 (RSA-4096) | 0.3–1.5 ms | 10–50 ms | Strong but slow |
| HS256 (HMAC-SHA256) | 0.01–0.05 ms | 0.01–0.05 ms | Symmetric, fastest |

### 4.2 Token Introspection & OAuth

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| OAuth token introspection (local) | 0.1–0.5 ms | Cached introspection |
| OAuth token introspection (remote IdP) | 1–10 ms | Network round-trip |
| OIDC discovery document fetch | 50–500 ms | Cached after first fetch |
| OIDC ID token validation | 0.2–2 ms | Signature + claims |
| SAML assertion validation | 1–10 ms | XML parsing + signature |

### 4.3 Session-Based Authentication

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| Session lookup (Redis, local) | 0.05–0.2 ms | In-memory, sub-ms |
| Session lookup (Redis, remote) | 0.2–1 ms | Network + Redis |
| Session lookup (DB) | 0.5–5 ms | Disk I/O bound |
| Cookie HMAC verification | 0.01–0.05 ms | Symmetric, fast |
| Session write/refresh | 0.1–1 ms | Redis write |

### 4.4 Certificate-Based Authentication

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| mTLS handshake (full) | +0.5–2 ms | Over standard TLS |
| X.509 chain validation | 0.1–1 ms | Depends on chain depth |
| OCSP stapling check | 0.05–0.5 ms | If stapled |
| OCSP responder query | 10–100 ms | Network call |
| CRL check (cached) | 0.01–0.1 ms | Local file parse |
| CRL download | 50–500 ms | Periodic fetch |

### 4.5 Multi-Factor Authentication

| Method | Typical Latency | Notes |
|--------|----------------|-------|
| TOTP verification | 0.01–0.1 ms | Local HMAC check |
| WebAuthn/FIDO2 | 50–200 ms | User interaction + crypto |
| Push notification | 1–10 s | User response time |
| SMS OTP | 5–30 s | Delivery + user entry |
| Email OTP | 10–60 s | Delivery + user entry |

---

## 5. ULL Optimization Strategies

| Strategy | Applicability | Expected Savings |
|----------|--------------|-----------------|
| Local JWT verification (JWKS cache) | All JWT-based auth | Eliminates IdP round-trip |
| Ed25519 for JWT signing | Internal services | 10–50x faster than RS256 |
| Redis session cache with pipelining | Session-based auth | Sub-ms lookup |
| Token binding to connection | API key auth | Prevent token replay |
| Async MFA (non-blocking) | MFA flows | Don't block request path |
| mTLS with session resumption | Service mesh | Avoid repeated handshakes |
| Short-lived tokens + refresh | OAuth | Reduce introspection calls |
| Edge authentication | CDN/edge | Offload from origin |

---

## 6. Measurement Checklist

- [ ] JWT verification latency by algorithm (Ed25519, ES256, RS256, HS256)
- [ ] JWT signing latency by algorithm
- [ ] JWKS fetch and cache hit latency
- [ ] OAuth token introspection latency (local vs. remote)
- [ ] OIDC discovery + ID token validation latency
- [ ] Session lookup latency (Redis local, Redis remote, DB)
- [ ] Cookie signing/verification latency
- [ ] mTLS handshake overhead vs. standard TLS
- [ ] X.509 chain validation latency
- [ ] OCSP stapling vs. responder query latency
- [ ] TOTP verification latency
- [ ] WebAuthn/FIDO2 assertion latency
- [ ] Cold vs. warm JWKS cache comparison
- [ ] Token refresh flow latency
- [ ] Authentication middleware overhead (p50, p99, p999)

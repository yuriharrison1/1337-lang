# Security Policy

## Supported Versions

Leetlang is in v0.x — only the latest minor version is supported for
security fixes. After v1.0 we will adopt a formal support window.

| Version | Supported |
|---------|-----------|
| 0.5.x   | ✅        |
| < 0.5   | ❌        |

## Reporting a Vulnerability

Please report security issues privately to security@leetlang.org.

Do **not** open public GitHub issues for security matters.

Expected response times:
- Acknowledgment: within 72 hours
- Initial assessment: within 7 days
- Patch or mitigation timeline: communicated after assessment

## Scope

In-scope:
- Buffer overflows, panics-as-DoS, arithmetic overflows in `leet-core`
- Wire format desync / parser bugs in `codec.rs`
- Auth/identity weaknesses in `compute_align_hash` or handshake
- Bridge layer: injection via RAW fields, rule bypasses

Out of scope:
- Vulnerabilities in third-party LLM providers
- Social engineering of agent impersonation at the application layer
- Denial of service from unbounded user-supplied DAGs (application-level
  rate limiting is caller's responsibility)

## Disclosure

After a fix is released, we will publish a CVE and security advisory on
GitHub with credit to the reporter, unless anonymity is requested.

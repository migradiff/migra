# MigraDiff Project Plan (Updated)

## Project Overview

**MigraDiff** is an actively maintained fork of djrobstep/migra (PostgreSQL schema diff tool). 

- **Package:** `migradiff` (PyPI)
- **CLI:** `migra` (backward compatible)
- **Repo:** https://github.com/migradiff/migra
- **Maintainer:** Leo (Lateos)
- **License:** MIT

---

## Business Targets

| Metric | Target | Timeline |
|--------|--------|----------|
| **Revenue (ARR)** | $1–2M | Year 1 |
| **Customer Base** | 200–300 customers | Year 1 |
| **Exit** | Supabase/Redgate | Year 2–3 |
| **Exit Value** | $10–20M | Year 2–3 |

---

## Completed Features

### v1.3.0 (Sessions 009–010)
- `--explain`: plain-English explanation of migrations
- `--from-migrations-dir`: load migrations from directory

### v1.4.0 (Sessions 011–013)
- `--rollback`: generates reversal migration SQL
- `--advise`: deterministic + AI performance/risk assessment
- `--generate`: writes migration SQL from plain-English description

### v1.5.0 (Session 017)
- `--comment-on`: diffs COMMENT ON annotations on objects

### Infrastructure (Session 018)
- ✅ Production CI/CD pipeline
- ✅ Branch protection on master
- ✅ Automated PyPI releases on tags
- ✅ GitHub Actions workflows (lint + test matrix + coverage)

---

## Current Version

**v1.5.1** (released June 4, 2026)

Test counts:
- Baseline: 109 tests
- v1.3.0: 142 tests (after --explain)
- v1.4.0: 175 tests (after AI suite)
- v1.5.0: 190 tests (after COMMENT ON)

---

## Free Tier Roadmap

### Session 019: `--explain-drift` (7–10 days)

**Feature:** Compare two **live PostgreSQL databases** and explain differences.

```bash
migra --from-db "postgresql://user:pass@old.example.com/db" \
       --to-db "postgresql://user:pass@prod.example.com/db" \
       --explain-drift
```

**Output:** Human-readable explanation of schema differences with risk categorization (BREAKING/WARNING/INFO).

**Use case:** "What changed in production? Is it safe?"

**Tests:** 80+ new tests (target: 270+ total)

**Release:** v1.6.0

**Why first:**
- Highest differentiation (competitors don't have this)
- Reuses existing schema inspection logic
- Fills gap: explain migrations vs. reality

---

### Session 020: Multi-Language README (3–5 days)

**Feature:** README in multiple languages (i18n).

Supported languages:
- 🇬🇧 English (default)
- 🇪🇸 Spanish (README.es.md)
- 🇫🇷 French (README.fr.md)
- 🇩🇪 German (README.de.md)
- 🇯🇵 Japanese (README.ja.md)
- 🇨🇳 Chinese (README.zh.md)

**How:** 
- Maintain main README.md (English)
- Create translated versions in repo root
- Link from main README
- Use GitHub language detection for auto-redirect

**Why:**
- Global audience (PostgreSQL is international)
- Drives adoption outside English-speaking markets
- Differentiator (most tools English-only)
- SEO boost (ranked in multiple language searches)

**Release:** v1.6.1

---

### Planned Sessions (Backlog)

| Session | Feature | Effort | Value | Notes |
|---------|---------|--------|-------|-------|
| 021 | `--document` | Medium-High | High | Schema documentation generation |
| 022 | pgvector support | Low | Medium | Modern Postgres vector types |
| 023 | `--suggest-indexes` | Medium | Medium | AI recommends useful indexes |
| 024 | `--dry-run --explain` | Low | Medium | Preview changes without applying |
| 025 | Multi-schema refactor | Medium | High | Better support for multiple schemas |

---

## Enterprise Tier (Post v1.6.0)

**Gating:** HMAC-signed license key (`MIGRADIFF-ENT-{base64}-{hmac}`)

### Features (Roadmap)

| Feature | Phase | Timeline | Notes |
|---------|-------|----------|-------|
| Hosted AI key | Phase 1 | Month 2–3 | Users don't manage Anthropic API key |
| Shadow Run | Phase 1 | Month 3–4 | Firecracker microVMs for safe testing |
| Team RBAC | Phase 2 | Month 4–5 | Multiple users, role-based access |
| Audit trail dashboard | Phase 2 | Month 5–6 | Compliance, change history, who-did-what |
| PR comment injection | Phase 2 | Month 6–7 | GitHub App auto-comments on PRs |
| Compliance reporting | Phase 3 | Month 7–8 | SOC 2, audit logs, retention policies |

---

## Free vs Enterprise Split

### **Free Tier (Local, User-Controlled)**
- `--explain` (explain migrations)
- `--rollback` (generate reversals)
- `--advise` (risk assessment)
- `--generate` (write from plain English)
- `--explain-drift` (compare live databases)
- `--document` (schema documentation)
- `--comment-on` (diff annotations)
- pgvector support
- Docker/GitHub Actions/pre-commit integration
- Multi-language README

**Monetization:** Community adoption, word-of-mouth, visibility to Supabase/Redgate

### **Enterprise Tier (Hosted/Managed)**
- Hosted Anthropic API key management
- Shadow Run (safe migration testing in isolated VMs)
- Team RBAC (multiple users, permissions)
- Audit trail dashboard (compliance, history)
- PR comment injection (GitHub App integration)
- Compliance reporting (SOC 2, audit logs)

**Pricing model:** 
- Free: forever
- Team: $299/month (5 users, audit logs, team management)
- Enterprise: custom pricing (large scale, compliance, SLA)

---

## Key Architecture Decisions

### Build System
- Poetry (dependency management)
- Python 3.10+ (floor version)
- setuptools (explicit dependency for schemainspect compatibility)

### AI Features
- Claude Haiku (cost-effective, fast)
- User's own Anthropic API key (free tier)
- Temperature 0 (deterministic outputs)
- Lazy imports (only load when used)

### Data Provenance
- All AI training data pipelines use cryptographic audit traceability
- Content hash (SHA-256), source_url, harvest_timestamp
- HMAC-SHA-256 signed pipeline_manifest.json
- License quarantine file (no split leakage)

### CI/CD
- GitHub Actions (lint, test matrix, coverage)
- Branch protection on `master` (CI required)
- Automated PyPI release on version tags
- Feature branch workflow (always test before merge)

### Database Support
- PostgreSQL 12+ (tested 14, 15, 16, 17)
- schemainspect for schema introspection
- sqlbag for connection management
- No ORM dependency (raw SQL + AST parsing)

---

## Known Limitations

### schemainspect + setuptools dependency
The `schemainspect` package (upstream: djrobstep, unmaintained) uses deprecated `pkg_resources` which requires `setuptools` at runtime. Added as explicit dependency in pyproject.toml.

**Migration path (future):** Replace with maintained schema inspection library or migrate to Rust.

---

## Version History

| Version | Release Date | Key Features |
|---------|--------------|--------------|
| v1.3.0 | May 2026 | --explain, --from-migrations-dir |
| v1.4.0 | June 1, 2026 | --rollback, --advise, --generate |
| v1.5.0 | June 4, 2026 | COMMENT ON diffing |
| v1.5.1 | June 4, 2026 | Version bump (no feature changes) |
| v1.6.0 | TBD (Session 019) | --explain-drift |
| v1.6.1 | TBD (Session 020) | Multi-language README |

---

## Marketing & Positioning

### Free Tier Positioning
"The AI-powered PostgreSQL migration tool that explains, reverses, and predicts risk in real-time."

### Enterprise Positioning
"Safe, auditable database migrations for teams. Compliance-ready. Built for scale."

### Competitive Advantages
1. **AI-native:** Every migration gets explained and risk-assessed
2. **Safe-by-default:** Detects dangerous patterns before deployment
3. **Multi-language:** Explains diffs, docs, and README in 6+ languages
4. **Live database aware:** `--explain-drift` compares reality, not just migrations
5. **Open source:** Free tier drives adoption, enterprise tier funds development

---

## Acquisition Narrative

**For Redgate (Flyway competitor):**
- Redgate owns Flyway (migration tool)
- MigraDiff fills the "schema analysis" gap
- Combined: Flyway migrations + MigraDiff intelligence = best-in-class

**For Supabase (PostgreSQL platform):**
- Supabase sells managed PostgreSQL
- MigraDiff drives migration adoption
- Combined: Supabase + MigraDiff = seamless developer experience

**Valuation basis:**
- v1.6.0: $3–4M ARR → $15–25M exit (3–5x revenue multiple)
- Enterprise adoption (Year 2): $5–8M ARR → $25–40M exit (5–7x multiple)

---

## Success Metrics (OKRs)

### Q2 2026
- ✅ v1.5.0 shipped
- ✅ CI/CD pipeline live
- ⏳ v1.6.0 shipped (`--explain-drift`)
- ⏳ 50+ GitHub stars
- ⏳ 1k+ monthly PyPI downloads

### Q3 2026
- ⏳ v1.6.1 shipped (multi-language README)
- ⏳ v1.7.0 shipped (`--document`, pgvector support)
- ⏳ 10+ enterprise customers ($30k–$100k MRR)
- ⏳ 100+ GitHub stars
- ⏳ 5k+ monthly PyPI downloads

### Q4 2026
- ⏳ Enterprise tier revenue: $50k/month ARR
- ⏳ Acquisition conversations with Redgate/Supabase
- ⏳ Featured on r/PostgreSQL, HackerNews
- ⏳ 10k+ monthly PyPI downloads

---

## Team & Workload

**Team:** Leo (solo, Lateos founder)

**Time allocation:**
- MigraDiff: 50% (revenue priority)
- npm-scan: 20% (security research)
- Other Lateos projects: 30% (pgAudit, ESLint, WAL-G forks)

**Engineering discipline:**
- Tests first, stop conditions on every prompt
- Three-phase workflow: reproduce → fix → document
- CI/CD validates every change before merge to master
- CLAUDE.md convention anchor for consistency
- Production-grade pipeline: feature branch → PR → CI → merge → release

---

## Next Steps

1. **Session 019:** Implement `--explain-drift` (7–10 days)
   - New feature: `migra --from-db X --to-db Y --explain-drift`
   - 80+ tests (target 270+ total)
   - Release v1.6.0

2. **Session 020:** Multi-language README (3–5 days)
   - README in 6 languages
   - i18n links from main README
   - Release v1.6.1

3. **Post v1.6.0:** Enterprise tier planning
   - Design licensing system
   - Plan hosted features
   - Build enterprise marketing narrative

---

**Document version:** Updated June 4, 2026 (post-Session 018)  
**Last updated by:** Claude (with Leo)  
**Repository:** https://github.com/migradiff/migra

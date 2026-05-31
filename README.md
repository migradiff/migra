# migra — PostgreSQL Schema Diff Tool

[![PyPI version](https://img.shields.io/pypi/v/migradiff)](https://pypi.org/project/migradiff/)
[![Python versions](https://img.shields.io/pypi/pyversions/migradiff)](https://pypi.org/project/migradiff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**The actively maintained fork of [djrobstep/migra](https://github.com/djrobstep/migra).**

migra compares two PostgreSQL database schemas and generates the SQL
migration script needed to transform one into the other. Drop it into
your CI pipeline and stop writing `ALTER TABLE` by hand.

---

## Why This Fork

The original `migra` was officially deprecated in 2024. This fork picks
up where it left off — fixing known issues, adding Python 3.12+ support,
and extending coverage for advanced PostgreSQL features.

If you were using `djrobstep/migra`, this is your drop-in continuation.
Nothing has changed about how the tool works. We're just keeping the
lights on and making it better.

**A note on naming:** This is an independent community fork. The CLI 
command remains `migra` for drop-in backward compatibility with 
existing scripts and pipelines. The package name is `migradiff` to 
distinguish it from the deprecated upstream. If you are looking for 
the original djrobstep/migra, it is archived at 
https://github.com/djrobstep/migra.

---

## Quickstart

### Install

```bash
pip install migradiff
```

Requires Python 3.10+ and a running PostgreSQL instance (12+).

To install from source:

```bash
git clone https://github.com/migradiff/migra
cd migra
pip install -e .
```

> **Note:** PyPI package coming with v1.1.0.

### Basic Usage

Point migra at two database connections and it outputs the DDL needed
to migrate from one to the other:

```bash
migra \
  postgresql://user:pass@localhost/db_production \
  postgresql://user:pass@localhost/db_branch \
  --unsafe
```

Output is plain SQL — pipe it, review it, apply it:

```bash
migra postgres://db_a postgres://db_b > migration.sql
psql postgres://db_production < migration.sql
```

### Schema Dumps (No Live Connection Required)

If you can't or don't want to point migra at a live database, use
`pg_dump -s` to generate a schema dump and diff that instead:

```bash
pg_dump -s postgres://db_production > schema_a.sql
pg_dump -s postgres://db_branch     > schema_b.sql
migra --from-file schema_a.sql schema_b.sql
```

This is the recommended approach for CI pipelines and security-conscious
environments — no production credentials required.

### Migrations Directory (No Live Branch Database Required)

If your target state is defined by a folder of migration files:

```bash
migra --from-migrations-dir ./migrations postgres://db_production
```

MigraDiff applies the migrations to an ephemeral database and diffs the
result. Supports Supabase, Flyway, and standard numeric naming conventions.

### Scoped to a Schema

```bash
# Single schema
migra --schema myschema postgres://db_a postgres://db_b

# Multiple schemas (comma-separated)
migra --schema public,reporting postgres://db_a postgres://db_b
```

### JSON Output

For programmatic consumption or CI pipelines:

```bash
migra --output json postgres://db_a postgres://db_b
```

Output includes per-statement risk classification (`safe`, `warning`,
`destructive`) and a summary with overall risk level.

---

## AI-Powered Explanation (Optional)

MigraDiff can explain any migration in plain English — what each
change does, what risks it carries, and safer alternatives for
destructive operations.

    migra --explain postgres://db_a postgres://db_b

Output:

    --- Migration SQL ---
    ALTER TABLE public.users ADD COLUMN email text;
    DROP TABLE public.legacy_sessions;

    --- AI Explanation ---
    This migration makes 2 changes to your database:

    1. SAFE: Adds an email column (text) to the users table.
       No existing data is affected.

    2. ⚠ DESTRUCTIVE: Drops the legacy_sessions table entirely.
       All data in this table will be permanently lost.
       Consider archiving before dropping.

    Overall risk: HIGH

Powered by Claude (Anthropic). Bring your own API key — no data
is sent to MigraDiff servers.

### Setup

Install the AI extras:

    pip install migradiff[ai]

Configure your API key once:

    migra --setup-ai

Or set the environment variable:

    export ANTHROPIC_API_KEY=sk-ant-...

Get an API key at https://console.anthropic.com

### AI Rollback Generation (--rollback)

Generate the exact reverse migration — the SQL needed to undo
any migration:

    migra --rollback migration.sql
    migra --rollback postgres://db_a postgres://db_b

MigraDiff uses your source schema context to reconstruct DROP
TABLE and DROP COLUMN reversals accurately. Non-reversible
operations (TRUNCATE, bulk DELETE) are flagged explicitly.

Combine with --explain for a complete picture:

    migra --explain --rollback postgres://db_a postgres://db_b

Requires `pip install migradiff[ai]` and an Anthropic API key.

### AI Performance Advisor (--advise)

Before applying any migration, get a performance risk assessment
— locking behavior, table rewrite risk, and zero-downtime
alternatives:

    migra --advise postgres://db_a postgres://db_b
    migra --advise migration.sql

MigraDiff analyzes each statement for PostgreSQL-specific risks:
table locks, full rewrites, irreversible data loss. When a live
connection is provided, table row counts are used to estimate
lock duration at your actual data scale.

Combine all three AI features for a complete picture:

    migra --explain --advise --rollback postgres://db_a postgres://db_b

Requires pip install migradiff[ai] and an Anthropic API key.

### AI Migration Generator (--generate)

Describe what you want in plain English — MigraDiff generates
the migration SQL grounded in your actual schema:

    migra --generate "add email verification to users table" \
      postgres://db_production

Unlike generic AI tools, MigraDiff knows your real table names,
column types, and constraints — no hallucinated column names or
wrong types.

Generate and immediately review the risk:

    migra --generate "add index on orders.user_id" \
      --advise postgres://db_production

Requires pip install migradiff[ai] and an Anthropic API key.

---

## Development Setup

The test suite requires a running PostgreSQL instance. The easiest
way to get one is via Docker Compose:

```bash
docker compose up -d
```

This starts a Postgres 16 container on localhost:5432 with trust
authentication. No password required.

To stop it:

```bash
docker compose down
```

Data persists between restarts via the `migradiff-pgdata` volume.
To reset completely:

```bash
docker compose down -v
```

---

## Docker

No Python environment? Use the official image:

```bash
docker run --rm ghcr.io/migradiff/migra \
  postgres://db_a postgres://db_b
```

---

## GitHub Actions

Add schema diffing to your pull request workflow:

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
```

Fail the build automatically if destructive operations are detected:

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
    fail_on_destructive: "true"
```

Use schema dump files instead of live connections:

```yaml
- uses: migradiff/migra@v1
  with:
    base_file: schema_production.sql
    head_file: schema_branch.sql
```

See [docs/action-usage.md](docs/action-usage.md) for full configuration options.

---

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/migradiff/migra
    rev: v1.1.0
    hooks:
      - id: migra
```

See `pre-commit-config.example.yaml` in the repo root for full
configuration options.

---

## What migra Understands

- Tables, columns, constraints, indexes
- Views and materialized views
- Functions and stored procedures
- Sequences
- Enums, composite types, domains
- Row-Level Security (RLS) policies
- Foreign data wrappers
- Column-level privileges
- Partitioned tables

---

## Improvements Over Upstream

| Area | Upstream (deprecated) | This Fork |
|---|---|---|
| Python 3.12+ | Deprecation warnings | Clean — no warnings |
| RLS policies | Partial, equality bug | Full CREATE/DROP, partition support |
| Error messages | Cryptic on unsupported types | Actionable with object name and issue link |
| --schema flag | Edge cases in multi-schema DBs | Comma-separated, cross-schema dependencies resolved |
| pg_dump input | Not supported | First-class `--from-file` mode |
| JSON output | Not supported | `--output json` with risk classification |
| Docker image | None | `ghcr.io/migradiff/migra` |
| GitHub Action | None | `migradiff/migra-action` |
| Pre-commit hook | None | `.pre-commit-hooks.yaml` |
| Dev environment | Manual Docker commands | `docker compose up -d` |
| AI explanation | None | `--explain` flag with Claude — plain English diff explanation, risk analysis, safer alternatives |

See [CHANGELOG.md](CHANGELOG.md) for the full fix history.

---

## Known Limitations

migra generates the SQL diff — it does not apply it. Review every
generated script before running against production. Destructive
operations (`DROP TABLE`, `DROP COLUMN`) are flagged in JSON output
mode but not blocked in plain SQL mode.

migra requires a live PostgreSQL connection to introspect schemas,
or schema dump files via `--from-file`. It does not parse raw DDL text.

---

## Contributing

Bug reports and PRs are welcome. If you're fixing something that was
reported upstream in `djrobstep/migra`, reference that issue number
in your PR — it helps us track what the community most needs fixed.

```bash
git clone https://github.com/migradiff/migra
cd migra
docker compose up -d
pip install -e ".[dev]"
pytest
```

---

## Enterprise

MigraDiff is MIT licensed. If you are building a commercial product
on top of MigraDiff, we'd love to hear from you —
enterprise@Lateos.ai

---

## License

MIT. See [LICENSE](LICENSE).

---

## Acknowledgements

This project is a fork of [djrobstep/migra](https://github.com/djrobstep/migra),
created and originally maintained by Robert Lechte. The core diffing
engine is his work. We are grateful for it.

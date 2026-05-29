# Changelog

## [Unreleased]

### Added
- Enum evolution diffing: ALTER TYPE ... ADD VALUE IF NOT EXISTS for
  safe additions; DROP + CREATE for removals and reorders;
  removals classified as destructive in --output json mode
- Composite type diffing: detects field additions, removals, and type
  changes; generates safe drop + create DDL
- Domain diffing: detects constraint and base type changes

### Fixed
- Resolved pre-existing E721 flake8 warning (type comparison)
  in test suite — codebase now has zero flake8 warnings
- Materialized view CREATE statements now generated in correct
  dependency order via topological sort; circular dependencies
  produce a clear error instead of incorrect output

### Changed
- Pinned schemainspect==3.1.1663587362 for reproducible builds and
  test results (upgraded from 3.1.1663480743)

---

## [1.1.0] - 2026-05-29

### Fixed
- Resolved all DeprecationWarning and PendingDeprecationWarning raised
  under Python 3.12+ — replaced schemainspect's deprecated
  pkg_resources.resource_stream with importlib.resources via monkey-patch
- Improved error messages for unsupported object types in
  Changes.__getattr__ — errors now include the triggering object name
  and a link to report the issue
- --schema flag now correctly scopes diffs in multi-schema deployments;
  cross-schema dependency handling improved; unknown schema name now
  returns a clear error message
- RLS policy diffing on partition tables — alter_rls_statement no longer
  raises NotImplementedError on partition children
- Fixed InspectedRowPolicy.__eq__ typo (self.name == self.name →
  self.name == other.name) causing silent incorrect policy comparisons
- Updated test fixtures for schemainspect view column alias changes —
  resolves 6 pre-existing test failures

### Added
- docker-compose.yml for one-command local development environment
  with Postgres 16 and persistent volume
- --from-file mode: diff pg_dump -s schema files directly without
  a live database connection — no production credentials required
- .pre-commit-hooks.yaml: pre-commit hook for local schema drift
  detection
- --output json mode: structured diff output with per-statement risk
  classification (safe / warning / destructive) and summary metadata;
  credentials redacted from connection string fields
- Dockerfile: python:3.12-slim base, non-root user, minimal image size
- action.yml: GitHub Actions action for CI schema drift detection;
  supports connection strings, --from-file mode, JSON output,
  and fail_on_destructive flag

### Known Issues
- SQLAlchemy 2.0 deprecation warning in sqlbag dependency
  (createdrop.py:63) — upstream sqlbag is unmaintained; evaluate
  replacing with direct psycopg2 calls in a future session

---

## [1.0.0] - 2025-08-25

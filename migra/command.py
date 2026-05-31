from __future__ import print_function, unicode_literals

import argparse
import json
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timezone

from .migra import Migration
from .statements import UnsafeMigrationException


def _sql_type(sql):
    words = sql.strip().upper().split()
    if not words:
        return "", ""
    first = words[0]
    if first == "CREATE" and len(words) > 1:
        if words[1] == "OR" and len(words) > 3:
            return f"{first} {words[3]}", words[3]
        return f"{first} {words[1]}", words[1]
    if first == "ALTER" and len(words) > 1:
        return f"{first} {words[1]}", words[1]
    if first == "DROP" and len(words) > 1:
        second = words[1]
        if second == "MATERIALIZED" and len(words) > 2:
            return f"{first} {second} {words[2]}", words[2]
        return f"{first} {second}", second
    if first == "TRUNCATE":
        return first, first
    if first == "REVOKE":
        return first, first
    if first == "GRANT":
        return first, first
    return first, first


def _extract_object_name(sql):
    normalized = sql.strip().upper()
    patterns = [
        r"(?:CREATE|ALTER|DROP)\s+(?:OR\s+REPLACE\s+)?(?:\w+\s+)*(?:TABLE\s+(?:IF\s+(?:NOT\s+)?EXISTS\s+)?|VIEW\s+(?:IF\s+(?:NOT\s+)?EXISTS\s+)?|MATERIALIZED\s+VIEW\s+(?:IF\s+EXISTS\s+)?|FUNCTION\s+|SEQUENCE\s+|SCHEMA\s+(?:IF\s+(?:NOT\s+)?EXISTS\s+)?|INDEX\s+(?:IF\s+(?:NOT\s+)?EXISTS\s+)?|TRIGGER\s+|POLICY\s+|RULE\s+|TYPE\s+|DOMAIN\s+|EXTENSION\s+)(.+?)(?:\s|$)",
        r"TRUNCATE\s+(?:TABLE\s+)?(.+?)(?:\s|$|;)",
    ]
    for pat in patterns:
        m = re.search(pat, normalized)
        if m:
            name = re.sub(r"[;(].*$", "", m.group(1).strip()).strip()
            return _original_case(sql, name)
    return ""


def _original_case(original, uppercase_piece):
    idx = original.strip().upper().find(uppercase_piece)
    if idx >= 0:
        return original.strip()[idx : idx + len(uppercase_piece)]  # noqa: E203
    return uppercase_piece


def classify_sql_statement(sql):
    normalized = sql.strip().upper()
    stmt_type, operation = _sql_type(sql)

    m = re.match(
        r"DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(.+?)(?:\s+CASCADE|\s+RESTRICT)?;?\s*$",
        normalized,
    )
    if m:
        name = _original_case(sql, m.group(1).strip())
        return {
            "type": stmt_type,
            "operation": "DROP",
            "object": name,
            "risk": "destructive",
        }

    m = re.match(
        r"DROP\s+TYPE\s+(?:IF\s+EXISTS\s+)?(.+?);?\s*$",
        normalized,
    )
    if m:
        name = _original_case(sql, m.group(1).strip())
        return {
            "type": stmt_type,
            "operation": "DROP",
            "object": name,
            "risk": "destructive",
        }

    m = re.match(
        r"ALTER\s+TABLE\s+(.+?)\s+DROP\s+(?:COLUMN\s+)?(.+?)(?:\s+CASCADE|\s+RESTRICT)?;?\s*$",
        normalized,
    )
    if m:
        name = _original_case(sql, m.group(1).strip())
        return {
            "type": stmt_type,
            "operation": "DROP COLUMN",
            "object": name,
            "risk": "destructive",
        }

    m = re.match(r"TRUNCATE\s+(?:TABLE\s+)?(.+?);?\s*$", normalized)
    if m:
        name = _original_case(sql, m.group(1).strip())
        return {
            "type": stmt_type,
            "operation": "TRUNCATE",
            "object": name,
            "risk": "destructive",
        }

    m = re.match(
        r"ALTER\s+TABLE\s+(.+?)\s+RENAME\s+(?:TO\s+|COLUMN\s+|CONSTRAINT\s+)?(.+?);?\s*$",
        normalized,
    )
    if m:
        name = _original_case(sql, m.group(1).strip())
        return {
            "type": stmt_type,
            "operation": "RENAME",
            "object": name,
            "risk": "warning",
        }

    obj = _extract_object_name(sql)
    first_word = normalized.split()[0] if normalized.split() else ""
    return {
        "type": stmt_type,
        "operation": first_word,
        "object": obj or "",
        "risk": "safe",
    }


def redact_credentials(url):
    return re.sub(r"://([^:@]+):([^@]+)@", r"://***:***@", url)


def format_json_output(statements, source, target):
    stmt_list = []
    has_destructive = False
    has_warning = False

    for sql in statements:
        info = classify_sql_statement(sql)
        stmt_list.append(
            {
                "sql": sql,
                "type": info["type"],
                "operation": info["operation"],
                "object": info["object"],
                "risk": info["risk"],
            }
        )
        if info["risk"] == "destructive":
            has_destructive = True
        elif info["risk"] == "warning":
            has_warning = True

    if has_destructive:
        risk_level = "high"
    elif has_warning:
        risk_level = "medium"
    else:
        risk_level = "low"

    return json.dumps(
        {
            "version": "1.0",
            "source": redact_credentials(source),
            "target": redact_credentials(target),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": {
                "total_statements": len(stmt_list),
                "has_destructive_operations": has_destructive,
                "risk_level": risk_level,
            },
            "statements": stmt_list,
        },
        indent=2,
    )


def _normalize_type(raw_type):
    t = raw_type.strip().upper()
    for kw in ["NOT NULL", "NULL", "DEFAULT", "USING", "CASCADE", "RESTRICT"]:
        idx = t.find(" " + kw)
        if idx > 0:
            t = t[:idx]
    return t.strip()


def _parse_alter_table(stmt):
    m = re.match(
        r"ALTER\s+TABLE\s+(.+?)\s+(DROP|ADD)\s+(?:COLUMN\s+)?(.+)",
        stmt.strip(),
        re.IGNORECASE,
    )
    if not m:
        return None
    table = m.group(1).strip()
    op = m.group(2).upper()
    rest = m.group(3).strip().rstrip(";").strip()
    col_match = re.match(r'"([^"]+)"\s*(.*)', rest)
    if not col_match:
        return None
    col_name = col_match.group(1)
    col_extra = col_match.group(2).strip()
    return table, op, col_name, col_extra


def detect_column_renames(statements, interactive=False, auto_accept=False):
    if not auto_accept and not interactive:
        return list(statements)

    drops = {}
    adds = {}

    for stmt in statements:
        parsed = _parse_alter_table(stmt)
        if parsed:
            table, op, col_name, col_extra = parsed
            if op == "DROP":
                drops.setdefault(table, []).append((col_name, stmt))
            elif op == "ADD":
                adds.setdefault(table, []).append((col_name, col_extra, stmt))

    result = list(statements)
    for table in set(drops.keys()) & set(adds.keys()):
        table_drops = list(drops[table])
        table_adds = list(adds[table])
        used_adds = set()

        for drop_idx, (drop_col, drop_stmt) in enumerate(table_drops):
            for add_idx, (add_col, add_type, add_stmt) in enumerate(table_adds):
                if add_idx in used_adds:
                    continue
                if drop_col == add_col:
                    continue
                if not _normalize_type(add_type):
                    continue

                drop_stmt_idx = result.index(drop_stmt)
                add_stmt_idx = result.index(add_stmt)
                rename = 'alter table {} rename column "{}" to "{}";'.format(
                    table, drop_col, add_col
                )
                result[drop_stmt_idx] = rename
                result[add_stmt_idx] = None
                used_adds.add(add_idx)
                break

    return [s for s in result if s is not None]


def _check_for_destructive(statements):
    """Check if any statement is destructive. Returns list of destructive statements."""
    destructive = []
    for stmt in statements:
        info = classify_sql_statement(stmt)
        if info["risk"] == "destructive":
            destructive.append(stmt)
    return destructive


def _format_destructive_summary(statements):
    """Format a summary of destructive operations for user output."""
    lines = []
    for stmt in statements:
        info = classify_sql_statement(stmt)
        lines.append("  {} {}".format(info["type"], info["object"]))
    return "\n".join(lines)


def _migration_sort_key(filename):
    """Extract sort key from a migration filename."""
    stem = filename.lower().replace(".sql", "")
    m = re.match(r"v?(\d+).*", stem)
    if m:
        return int(m.group(1))
    return 0


def discover_migration_files(directory):
    """Find and sort .sql migration files in a directory."""
    if not os.path.isdir(directory):
        raise ValueError(f"MigraDiff: migrations directory not found: {directory}")

    sql_files = []
    for f in os.listdir(directory):
        if f.endswith(".sql"):
            sql_files.append(f)

    if not sql_files:
        raise ValueError(f"MigraDiff: no .sql migration files found in: {directory}")

    sql_files.sort(key=_migration_sort_key)
    return [os.path.join(directory, f) for f in sql_files]


def apply_migrations(directory):
    """Apply migration files from a directory to a temporary database.
    Returns the temporary database URL.
    """
    from sqlbag import S, temporary_database

    files = discover_migration_files(directory)
    temp_db = temporary_database(host="localhost")
    db_url = temp_db.__enter__()
    try:
        with S(db_url) as s:
            for f in files:
                try:
                    with open(f, "r") as fh:
                        sql = fh.read()
                    if sql.strip():
                        s.execute(sql)
                except Exception as e:
                    raise RuntimeError(
                        f"MigraDiff: Migration file failed to apply:\n"
                        f"  File: {os.path.basename(f)}\n"
                        f"  Error: {e}\n"
                        f"\nFix the migration file and retry."
                    )
        return db_url, temp_db
    except Exception:
        temp_db.__exit__(None, None, None)
        raise


@contextmanager
def migrations_context(directory):
    """Context manager that applies migrations to a temp DB and cleans up."""
    from sqlbag import S, temporary_database

    files = discover_migration_files(directory)
    with temporary_database(host="localhost") as db_url:
        with S(db_url) as s:
            for f in files:
                with open(f, "r") as fh:
                    sql = fh.read()
                if sql.strip():
                    try:
                        s.execute(sql)
                    except Exception as e:
                        raise RuntimeError(
                            f"MigraDiff: Migration file failed to apply:\n"
                            f"  File: {os.path.basename(f)}\n"
                            f"  Error: {e}\n"
                            f"\nFix the migration file and retry."
                        )
        yield db_url


@contextmanager
def _single_file_context(filepath):
    """Load a single SQL file into a temporary database."""
    from sqlbag import S, load_sql_from_file, temporary_database

    with temporary_database(host="localhost") as db_url:
        with S(db_url) as s:
            load_sql_from_file(s, filepath)
        yield db_url


@contextmanager
def arg_context(x):
    if x == "EMPTY":
        yield None

    else:
        from sqlbag import S

        with S(x) as s:
            yield s


@contextmanager
def file_context(x, y):
    from sqlbag import S, load_sql_from_file, temporary_database

    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0:
            load_sql_from_file(s0, x)
        with S(d1) as s1:
            load_sql_from_file(s1, y)
        yield d0, d1


def parse_args(args):
    parser = argparse.ArgumentParser(description="Generate a database migration.")
    parser.add_argument(
        "--unsafe",
        dest="unsafe",
        action="store_true",
        help="Prevent migra from erroring upon generation of drop statements.",
    )
    parser.add_argument(
        "--schema",
        dest="schema",
        default=None,
        help="Restrict output to statements for a particular schema",
    )
    parser.add_argument(
        "--exclude_schema",
        dest="exclude_schema",
        default=None,
        help="Restrict output to statements for all schemas except the specified schema",
    )
    parser.add_argument(
        "--create-extensions-only",
        dest="create_extensions_only",
        action="store_true",
        default=False,
        help='Only output "create extension..." statements, nothing else.',
    )
    parser.add_argument(
        "--ignore-extension-versions",
        dest="ignore_extension_versions",
        action="store_true",
        default=False,
        help="Ignore the versions when comparing extensions.",
    )
    parser.add_argument(
        "--with-privileges",
        dest="with_privileges",
        action="store_true",
        default=False,
        help="Also output privilege differences (ie. grant/revoke statements)",
    )
    parser.add_argument(
        "--force-utf8",
        dest="force_utf8",
        action="store_true",
        default=False,
        help="Force UTF-8 encoding for output",
    )
    parser.add_argument(
        "--from-file",
        dest="from_file",
        action="store_true",
        default=False,
        help="Treat dburl_from and dburl_target as pg_dump -s file paths",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default="sql",
        choices=["sql", "json"],
        help="Output format: plain SQL (default) or structured JSON",
    )
    parser.add_argument(
        "--rename-columns",
        dest="rename_columns",
        action="store_true",
        default=False,
        help="Auto-accept column renames without prompting",
    )
    parser.add_argument(
        "--no-rename-detection",
        dest="no_rename_detection",
        action="store_true",
        default=False,
        help="Disable column rename detection entirely",
    )
    parser.add_argument(
        "--force-destructive",
        dest="force_destructive",
        action="store_true",
        default=False,
        help="Allow destructive operations (DROP TABLE, DROP COLUMN, etc.)",
    )
    parser.add_argument(
        "--safe",
        dest="safe",
        action="store_true",
        default=False,
        help="Explicit safe mode (default): halt on destructive operations",
    )
    parser.add_argument(
        "--from-migrations-dir",
        dest="from_migrations_dir",
        default=None,
        help="Directory of numbered .sql migration files (applied in order)",
    )
    parser.add_argument(
        "--explain",
        dest="explain",
        action="store_true",
        default=False,
        help="Generate an AI-powered plain English explanation of the migration",
    )
    parser.add_argument(
        "--api-key",
        dest="api_key",
        default=None,
        help="Anthropic API key for --explain (overrides env var and config file)",
    )
    parser.add_argument(
        "--setup-ai",
        dest="setup_ai",
        action="store_true",
        default=False,
        help="Interactively configure AI API key and save to config file",
    )
    parser.add_argument(
        "--rollback",
        dest="rollback",
        nargs="?",
        const=True,
        default=False,
        help="Generate the reverse migration (rollback). Optionally accepts a"
        " migration SQL file path.",
    )
    parser.add_argument(
        "--advise",
        dest="advise",
        action="store_true",
        default=False,
        help="Generate an AI-powered performance risk assessment of the migration",
    )
    parser.add_argument(
        "--generate",
        dest="generate",
        nargs="?",
        const=True,
        default=False,
        help="Generate a PostgreSQL migration from a plain English description."
        " Optionally provide the description as an argument.",
    )
    parser.add_argument(
        "dburl_from", nargs="?", help="The database you want to migrate."
    )
    parser.add_argument(
        "dburl_target", nargs="?", help="The database you want to use as the target."
    )
    return parser.parse_args(args)


def run(args, out=None, err=None):
    if not out:
        out = sys.stdout  # pragma: no cover
    if not err:
        err = sys.stderr  # pragma: no cover

    if args.setup_ai:
        from .ai_explain import setup_ai_interactive

        return setup_ai_interactive(out, err)

    # Rollback mode with file (no connection strings needed)
    if args.rollback and isinstance(args.rollback, str):
        from .ai_explain import generate_file_rollback

        result = generate_file_rollback(args.rollback)
        if result["text"]:
            print(result["text"], file=out)
        return 0

    # Generate mode
    if args.generate:
        from .ai_explain import (
            AIGenerator,
            check_safety_rules,
            extract_relevant_schema,
            parse_schema_file_for_tables,
            resolve_api_key,
            redact_api_key,
            classify_statement_risk,
        )

        description = args.generate if isinstance(args.generate, str) else None
        if not description or description is True:
            print(
                "MigraDiff: --generate requires a description.\n"
                'Usage: migra --generate "add email column to users"'
                " postgres://db_url",
                file=err,
            )
            return 1

        try:
            import anthropic  # noqa: F401
        except ImportError:
            print(
                "MigraDiff: --generate requires the AI extras.",
                file=err,
            )
            print("Install with: pip install migradiff[ai]", file=err)
            return 1

        api_key = resolve_api_key(cli_key=args.api_key)
        if not api_key:
            print(
                "MigraDiff: --generate requires an Anthropic API key.",
                file=err,
            )
            print(file=err)
            print("Set it up once with:", file=err)
            print("  migra --setup-ai", file=err)
            print(file=err)
            print("Or set the environment variable:", file=err)
            print("  export ANTHROPIC_API_KEY=sk-ant-...", file=err)
            print(file=err)
            print(
                "Get an API key at: https://console.anthropic.com",
                file=err,
            )
            return 1

        # Safety check first
        safety = check_safety_rules(description)
        if safety["action"] == "refuse":
            print(
                "MigraDiff: Refusing to generate bulk destructive migration.",
                file=err,
            )
            print(safety["reason"], file=err)
            print(
                "If intentional, write the SQL manually and" " use --advise to review.",
                file=err,
            )
            return 1

        # Extract schema context
        schema_context = ""
        if args.from_file and args.dburl_from:
            schema_context = parse_schema_file_for_tables(args.dburl_from)
        elif args.dburl_from and "://" in args.dburl_from:
            try:
                schema_context = extract_relevant_schema(args.dburl_from, description)
            except Exception:
                schema_context = ""

        generator = AIGenerator(api_key)
        try:
            result = generator.generate(description, schema_context)
        except RuntimeError as e:
            print(str(e), file=err)
            return 1
        except Exception as e:
            msg = redact_api_key(str(e))
            print(
                "MigraDiff: AI generation failed: {}".format(msg),
                file=err,
            )
            return 1

        # Output
        if args.output == "json":
            import json as json_mod

            json_out = json_mod.dumps(
                {
                    "version": "1.0",
                    "generated": {
                        "description": description,
                        "sql": result.get("generated_sql", result["text"]),
                        "schema_context_used": result.get("schema_context_used", []),
                        "model": result.get("model", ""),
                        "generated_at": result.get("generated_at", ""),
                        "warnings": ["Review before applying to production"],
                    },
                },
                indent=2,
            )
            print(json_out, file=out)
        else:
            print(result["text"], file=out)

        # If --advise also set, run deterministic risk classification
        if args.advise and result.get("generated_sql"):
            advisory_lines = []
            advisory_lines.append("")
            advisory_lines.append("--- Performance Advisory ---")
            stmts = result["generated_sql"].split("\n")
            for stmt in stmts:
                stmt = stmt.strip()
                if stmt and not stmt.startswith("--"):
                    risk = classify_statement_risk(stmt)
                    advisory_lines.append("")
                    advisory_lines.append("Statement: {}".format(stmt))
                    advisory_lines.append(
                        "Risk: {} {}".format(
                            risk["risk"],
                            (
                                "\u26a0"
                                if risk["risk"] == "HIGH"
                                else (
                                    "\u26a1" if risk["risk"] == "MEDIUM" else "\u2713"
                                )
                            ),
                        )
                    )
                    advisory_lines.append("Issue: {}".format(risk["issue"]))
            if len(advisory_lines) > 2:
                print("\n".join(advisory_lines), file=out)

        return 0

    # Advise mode with file (no connection strings needed)
    if (
        args.advise
        and args.dburl_from
        and not args.from_file
        and not args.from_migrations_dir
    ):
        filepath = args.dburl_from
        if os.path.exists(filepath) and filepath.endswith(".sql"):
            from .ai_explain import resolve_api_key

            api_key = resolve_api_key(cli_key=args.api_key)
            if not api_key:
                print(
                    "MigraDiff: --advise requires an Anthropic API key.",
                    file=err,
                )
                print(file=err)
                print("Set it up once with:", file=err)
                print("  migra --setup-ai", file=err)
                print(file=err)
                print("Or set the environment variable:", file=err)
                print("  export ANTHROPIC_API_KEY=sk-ant-...", file=err)
                print(file=err)
                return 1

            from .ai_explain import generate_file_advisory

            result = generate_file_advisory(filepath, api_key=api_key)
            if result["text"]:
                print(result["text"], file=out)
            return 0

    if not args.from_migrations_dir and not args.from_file and not args.dburl_from:
        print(
            "ERROR: A database URL or --from-file is required.",
            file=err,
        )
        return 1

    if args.unsafe and out.isatty():
        print(
            "WARNING: --unsafe is deprecated. Use --force-destructive instead.",
            file=err,
        )

    args._original_from = args.dburl_from
    args._original_target = args.dburl_target

    if args.from_migrations_dir:
        if not os.path.isdir(args.from_migrations_dir):
            print(
                f"ERROR: --from-migrations-dir directory not found: {args.from_migrations_dir}",
                file=err,
            )
            return 1

        try:
            discover_migration_files(args.from_migrations_dir)
        except ValueError as e:
            print(str(e), file=err)
            return 1

        try:
            if args.from_file:
                with _single_file_context(args.dburl_from) as d0_url:
                    with migrations_context(args.from_migrations_dir) as target_url:
                        args.dburl_from = d0_url
                        args.dburl_target = target_url
                        args._original_target = args.from_migrations_dir
                        return _run_inner(args, out, err)
            elif args.dburl_from:
                with migrations_context(args.from_migrations_dir) as target_url:
                    args._original_target = args.from_migrations_dir
                    args.dburl_target = target_url
                    return _run_inner(args, out, err)
        except RuntimeError as e:
            print(str(e), file=err)
            return 1
        else:
            print(
                "ERROR: --from-migrations-dir requires a base schema source. "
                "Provide a connection string or use --from-file.",
                file=err,
            )
            return 1

    if args.from_file:
        for path in [args.dburl_from, args.dburl_target]:
            if "://" in path:
                print(
                    "ERROR: --from-file expects file paths, but got a URL. "
                    "Drop --from-file to diff live databases.",
                    file=err,
                )
                return 1
            if not os.path.exists(path):
                print(
                    f"ERROR: file not found: {path}",
                    file=err,
                )
                return 1
        try:
            with file_context(args.dburl_from, args.dburl_target) as (
                d0_url,
                d1_url,
            ):
                args.dburl_from = d0_url
                args.dburl_target = d1_url
                return _run_inner(args, out, err)
        except Exception as e:
            print(
                f"ERROR: could not load SQL from files: {e}",
                file=err,
            )
            return 1

    return _run_inner(args, out, err)


def _run_inner(args, out=None, err=None):
    schema = args.schema
    exclude_schema = args.exclude_schema
    with arg_context(args.dburl_from) as ac0, arg_context(args.dburl_target) as ac1:
        m = Migration(
            ac0,
            ac1,
            schema=schema,
            exclude_schema=exclude_schema,
            ignore_extension_versions=args.ignore_extension_versions,
        )
        unsafe_or_force = args.unsafe or args.force_destructive
        if unsafe_or_force:
            m.set_safety(False)
        if args.create_extensions_only:
            m.add_extension_changes(drops=False)
        else:
            m.add_all_changes(privileges=args.with_privileges)

        # Post-processing: rename detection
        statements = list(m.statements)
        if not args.no_rename_detection:
            auto_accept = args.rename_columns
            statements = detect_column_renames(
                statements, interactive=False, auto_accept=auto_accept
            )

        # Safe mode check: halt on destructive operations unless opted in
        if not unsafe_or_force:
            destructive = _check_for_destructive(statements)
            if destructive:
                print(
                    "MigraDiff: Destructive operations detected."
                    " Use --force-destructive to proceed.",
                    file=err,
                )
                print(file=err)
                print("Destructive operations found:", file=err)
                print(_format_destructive_summary(destructive), file=err)
                print(file=err)
                print(
                    "Review these carefully before applying to production.",
                    file=err,
                )
                print(
                    "Run with --force-destructive to generate the full migration script.",
                    file=err,
                )
                return 1

        # Build the migration SQL from (potentially modified) statements
        from .statements import Statements

        modified_statements = Statements(statements)
        modified_statements.safe = not unsafe_or_force

        # AI explanation support
        explanation = None
        rollback_result = None
        advisory_result = None
        if args.explain:
            from .ai_explain import AIExplainer, resolve_api_key, redact_api_key

            try:
                import anthropic  # noqa: F401
            except ImportError:
                print(
                    "MigraDiff: --explain requires the AI extras.",
                    file=err,
                )
                print("Install with: pip install migradiff[ai]", file=err)
                return 1

            api_key = resolve_api_key(cli_key=args.api_key)
            if not api_key:
                print(
                    "MigraDiff: --explain requires an Anthropic API key.",
                    file=err,
                )
                print(file=err)
                print("Set it up once with:", file=err)
                print("  migra --setup-ai", file=err)
                print(file=err)
                print("Or set the environment variable:", file=err)
                print("  export ANTHROPIC_API_KEY=sk-ant-...", file=err)
                print(file=err)
                print(
                    "Get an API key at: https://console.anthropic.com",
                    file=err,
                )
                return 1

            if statements:
                stmt_info = [classify_sql_statement(s) for s in statements]
                explainer = AIExplainer(api_key)
                try:
                    explanation = explainer.explain(modified_statements.sql, stmt_info)
                except RuntimeError as e:
                    print(str(e), file=err)
                    # Still print SQL, but don't have explanation
                except Exception as e:
                    msg = redact_api_key(str(e))
                    print(
                        "MigraDiff: AI explanation failed: {}".format(msg),
                        file=err,
                    )

        # AI rollback generation
        if args.rollback:
            from .ai_explain import AIRollback, resolve_api_key, redact_api_key

            try:
                import anthropic  # noqa: F401, F811
            except ImportError:
                print(
                    "MigraDiff: --rollback requires the AI extras.",
                    file=err,
                )
                print("Install with: pip install migradiff[ai]", file=err)
                return 1

            api_key = resolve_api_key(cli_key=args.api_key)
            if not api_key:
                print(
                    "MigraDiff: --rollback requires an Anthropic API key.",
                    file=err,
                )
                print(file=err)
                print("Set it up once with:", file=err)
                print("  migra --setup-ai", file=err)
                print(file=err)
                print("Or set the environment variable:", file=err)
                print("  export ANTHROPIC_API_KEY=sk-ant-...", file=err)
                print(file=err)
                print(
                    "Get an API key at: https://console.anthropic.com",
                    file=err,
                )
                return 1

            if statements:
                from .ai_explain import extract_drop_references, extract_schema_context

                rollback_sql = modified_statements.sql
                refs = extract_drop_references(rollback_sql)
                schema_context = ""
                if any(refs.values()) and args.dburl_from:
                    try:
                        schema_context = extract_schema_context(args.dburl_from, refs)
                    except Exception as e:
                        schema_context = (
                            "-- WARNING: Could not extract schema context: {}".format(e)
                        )

                rollbacker = AIRollback(api_key)
                try:
                    rollback_result = rollbacker.generate_rollback(
                        rollback_sql, schema_context
                    )
                except RuntimeError as e:
                    print(str(e), file=err)
                except Exception as e:
                    msg = redact_api_key(str(e))
                    print(
                        "MigraDiff: AI rollback failed: {}".format(msg),
                        file=err,
                    )

        # AI advisory generation
        if args.advise:
            from .ai_explain import AIAdvisor, resolve_api_key, redact_api_key

            try:
                import anthropic  # noqa: F401, F811
            except ImportError:
                print(
                    "MigraDiff: --advise requires the AI extras.",
                    file=err,
                )
                print("Install with: pip install migradiff[ai]", file=err)
                return 1

            api_key = resolve_api_key(cli_key=args.api_key)
            if not api_key:
                print(
                    "MigraDiff: --advise requires an Anthropic API key.",
                    file=err,
                )
                print(file=err)
                print("Set it up once with:", file=err)
                print("  migra --setup-ai", file=err)
                print(file=err)
                print("Or set the environment variable:", file=err)
                print("  export ANTHROPIC_API_KEY=sk-ant-...", file=err)
                print(file=err)
                print(
                    "Get an API key at: https://console.anthropic.com",
                    file=err,
                )
                return 1

            if statements:
                from .ai_explain import extract_table_stats

                advise_sql = modified_statements.sql
                stmt_info = [classify_sql_statement(s) for s in statements]

                # Extract table stats if connection available
                table_stats = ""
                if args.dburl_from:
                    try:
                        referenced_tables = set()
                        for s in statements:
                            upper = s.strip().upper()
                            m = re.match(
                                r"(?:ALTER|DROP|TRUNCATE)\s+TABLE\s+(?:IF\s+EXISTS\s+)?(.+?)(?:\s|;|$)",
                                upper,
                            )
                            if m:
                                referenced_tables.add(m.group(1).strip())
                        if referenced_tables:
                            table_stats = extract_table_stats(
                                args.dburl_from, list(referenced_tables)
                            )
                    except Exception:
                        table_stats = ""
                else:
                    table_stats = (
                        "Table size statistics unavailable (no live connection). "
                    )

                advisor = AIAdvisor(api_key)
                try:
                    advisory_result = advisor.advise(advise_sql, stmt_info, table_stats)
                except RuntimeError as e:
                    print(str(e), file=err)
                except Exception as e:
                    msg = redact_api_key(str(e))
                    print(
                        "MigraDiff: AI advisory failed: {}".format(msg),
                        file=err,
                    )

        try:
            if statements:
                if args.output == "json":
                    json_out = format_json_output(
                        statements,
                        getattr(args, "_original_from", args.dburl_from),
                        getattr(args, "_original_target", args.dburl_target),
                    )
                    if explanation:
                        import json as json_mod

                        data = json_mod.loads(json_out)
                        data["explanation"] = {
                            "text": explanation["text"],
                            "model": explanation["model"],
                            "generated_at": explanation["generated_at"],
                        }
                        json_out = json_mod.dumps(data, indent=2)
                    if rollback_result:
                        import json as json_mod

                        data = json_mod.loads(json_out)
                        data["rollback"] = {
                            "text": rollback_result["text"],
                            "model": rollback_result["model"],
                            "generated_at": rollback_result["generated_at"],
                        }
                        json_out = json_mod.dumps(data, indent=2)
                    if advisory_result:
                        import json as json_mod

                        data = json_mod.loads(json_out)
                        data["advisory"] = {
                            "overall_risk": advisory_result.get("overall_risk", "LOW"),
                            "statements": advisory_result.get("statement_details", []),
                            "model": advisory_result.get("model", ""),
                            "generated_at": advisory_result.get("generated_at", ""),
                        }
                        json_out = json_mod.dumps(data, indent=2)
                    print(json_out, file=out)
                elif args.force_utf8:
                    print(modified_statements.sql.encode("utf8"), file=out)
                else:
                    print(modified_statements.sql, file=out)
                if explanation and args.output != "json":
                    print(file=out)
                    print("--- AI Explanation ---", file=out)
                    print(explanation["text"], file=out)
                if rollback_result and args.output != "json":
                    print(file=out)
                    print(rollback_result["text"], file=out)
                if advisory_result and args.output != "json":
                    print(file=out)
                    print("--- Performance Advisory ---", file=out)
                    print(advisory_result["text"], file=out)
            elif args.output == "json":
                json_out = format_json_output(
                    statements,
                    getattr(args, "_original_from", args.dburl_from),
                    getattr(args, "_original_target", args.dburl_target),
                )
                if explanation:
                    import json as json_mod

                    data = json_mod.loads(json_out)
                    data["explanation"] = {
                        "text": explanation["text"],
                        "model": explanation["model"],
                        "generated_at": explanation["generated_at"],
                    }
                    json_out = json_mod.dumps(data, indent=2)
                if rollback_result:
                    import json as json_mod

                    data = json_mod.loads(json_out)
                    data["rollback"] = {
                        "text": rollback_result["text"],
                        "model": rollback_result["model"],
                        "generated_at": rollback_result["generated_at"],
                    }
                    json_out = json_mod.dumps(data, indent=2)
                if advisory_result:
                    import json as json_mod

                    data = json_mod.loads(json_out)
                    data["advisory"] = {
                        "overall_risk": advisory_result.get("overall_risk", "LOW"),
                        "statements": advisory_result.get("statement_details", []),
                        "model": advisory_result.get("model", ""),
                        "generated_at": advisory_result.get("generated_at", ""),
                    }
                    json_out = json_mod.dumps(data, indent=2)
                print(json_out, file=out)
            elif args.explain or args.rollback or args.advise:
                if args.explain:
                    print("--- AI Explanation ---", file=out)
                if args.rollback:
                    print("--- Rollback ---", file=out)
                if args.advise:
                    print("--- Performance Advisory ---", file=out)
                print(
                    "No schema differences detected. The schemas are identical.",
                    file=out,
                )
        except UnsafeMigrationException:
            print(
                "-- ERROR: destructive statements generated. Use the --unsafe flag to suppress this error.",
                file=err,
            )
            return 3

        if not statements:
            return 0

        else:
            return 2


def do_command():  # pragma: no cover
    args = parse_args(sys.argv[1:])
    status = run(args)
    sys.exit(status)

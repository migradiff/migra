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
    parser.add_argument("dburl_from", help="The database you want to migrate.")
    parser.add_argument(
        "dburl_target", help="The database you want to use as the target."
    )
    return parser.parse_args(args)


def run(args, out=None, err=None):
    if not out:
        out = sys.stdout  # pragma: no cover
    if not err:
        err = sys.stderr  # pragma: no cover

    args._original_from = args.dburl_from
    args._original_target = args.dburl_target

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
        if args.unsafe:
            m.set_safety(False)
        if args.create_extensions_only:
            m.add_extension_changes(drops=False)
        else:
            m.add_all_changes(privileges=args.with_privileges)
        try:
            if m.statements:
                if args.output == "json":
                    json_out = format_json_output(
                        m.statements,
                        getattr(args, "_original_from", args.dburl_from),
                        getattr(args, "_original_target", args.dburl_target),
                    )
                    print(json_out, file=out)
                elif args.force_utf8:
                    print(m.sql.encode("utf8"), file=out)
                else:
                    print(m.sql, file=out)
            elif args.output == "json":
                json_out = format_json_output(
                    m.statements,
                    getattr(args, "_original_from", args.dburl_from),
                    getattr(args, "_original_target", args.dburl_target),
                )
                print(json_out, file=out)
        except UnsafeMigrationException:
            print(
                "-- ERROR: destructive statements generated. Use the --unsafe flag to suppress this error.",
                file=err,
            )
            return 3

        if not m.statements:
            return 0

        else:
            return 2


def do_command():  # pragma: no cover
    args = parse_args(sys.argv[1:])
    status = run(args)
    sys.exit(status)

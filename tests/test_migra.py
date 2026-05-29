from __future__ import unicode_literals

import io
from difflib import ndiff as difflib_diff

import pytest

# import yaml
from pytest import raises
from schemainspect import get_inspector
from sqlbag import S, load_sql_from_file, temporary_database

from migra import Migration, Statements, UnsafeMigrationException
from migra.command import parse_args, run


def textdiff(a, b):
    cd = difflib_diff(a.splitlines(), b.splitlines())
    return "\n" + "\n".join(cd) + "\n"


SQL = """select 1;

select 2;

"""
DROP = "drop table x;"


def test_statements():
    s1 = Statements(["select 1;"])
    s2 = Statements(["select 2;"])
    s3 = s1 + s2
    assert (
        isinstance(s1, Statements)
        and isinstance(s2, Statements)
        and isinstance(s3, Statements)
    )
    s3 = s3 + Statements([DROP])
    with raises(UnsafeMigrationException):
        assert s3.sql == SQL
    s3.safe = False
    SQL_WITH_DROP = SQL + DROP + "\n\n"
    assert s3.sql == SQL_WITH_DROP


def outs():
    return io.StringIO(), io.StringIO()


def test_singleschema():
    for FIXTURE_NAME in ["singleschema"]:
        do_fixture_test(FIXTURE_NAME, schema="goodschema")


def test_excludeschema():
    for FIXTURE_NAME in ["excludeschema"]:
        do_fixture_test(FIXTURE_NAME, exclude_schema="excludedschema")


def test_singleschema_ext():
    for FIXTURE_NAME in ["singleschema_ext"]:
        do_fixture_test(FIXTURE_NAME, create_extensions_only=True)


def test_extversions():
    for FIXTURE_NAME in ["extversions"]:
        do_fixture_test(FIXTURE_NAME, ignore_extension_versions=False)


fixtures = """\
everything
collations
identitycols
partitioning
privileges
enumdefaults
enumdeps
seq
inherit
inherit2
triggers
triggers2
triggers3
dependencies
dependencies2
dependencies3
dependencies4
constraints
generated
""".split()


@pytest.mark.parametrize("fixture_name", fixtures)
def test_fixtures(fixture_name):
    do_fixture_test(fixture_name, with_privileges=True)


schemainspect_test_role = "schemainspect_test_role"


def create_role(s, rolename):
    role = s.execute(
        """
SELECT 1 FROM pg_roles WHERE rolname=:rolename
    """,
        dict(rolename=rolename),
    )

    role_exists = bool(list(role))

    if not role_exists:
        s.execute(f"""
            create role {rolename};
        """)


def test_rls():
    for FIXTURE_NAME in ["rls", "rls2"]:
        do_fixture_test(FIXTURE_NAME, with_privileges=True)


check_expected = True


def do_fixture_test(
    fixture_name,
    schema=None,
    create_extensions_only=False,
    ignore_extension_versions=True,
    with_privileges=False,
    exclude_schema=None,
):
    flags = ["--unsafe"]
    if schema:
        flags += ["--schema", schema]
    if exclude_schema:
        flags += ["--exclude_schema", exclude_schema]
    if create_extensions_only:
        flags += ["--create-extensions-only"]
    if ignore_extension_versions:
        flags += ["--ignore-extension-versions"]
    if with_privileges:
        flags += ["--with-privileges"]
    fixture_path = "tests/FIXTURES/{}/".format(fixture_name)
    EXPECTED = io.open(fixture_path + "expected.sql").read().strip()
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0:
            create_role(s0, schemainspect_test_role)
        with S(d0) as s0, S(d1) as s1:
            load_sql_from_file(s0, fixture_path + "a.sql")
            load_sql_from_file(s1, fixture_path + "b.sql")

        args = parse_args([d0, d1])
        assert not args.unsafe
        assert args.schema is None

        out, err = outs()
        assert run(args, out=out, err=err) == 3
        assert out.getvalue() == ""

        DESTRUCTIVE = "-- ERROR: destructive statements generated. Use the --unsafe flag to suppress this error.\n"

        assert err.getvalue() == DESTRUCTIVE

        args = parse_args(flags + [d0, d1])
        assert args.unsafe
        assert args.schema == schema
        out, err = outs()
        assert run(args, out=out, err=err) == 2
        assert err.getvalue() == ""

        output = out.getvalue().strip()
        if check_expected:
            assert output == EXPECTED

        ADDITIONS = io.open(fixture_path + "additions.sql").read().strip()
        EXPECTED2 = io.open(fixture_path + "expected2.sql").read().strip()

        with S(d0) as s0, S(d1) as s1:
            m = Migration(
                s0,
                s1,
                schema=schema,
                exclude_schema=exclude_schema,
                ignore_extension_versions=ignore_extension_versions,
            )
            m.inspect_from()
            m.inspect_target()
            with raises(AttributeError):
                m.changes.nonexist
            m.set_safety(False)
            if ADDITIONS:
                m.add_sql(ADDITIONS)
            m.apply()

            if create_extensions_only:
                m.add_extension_changes(drops=False)
            else:
                m.add_all_changes(privileges=with_privileges)

            expected = EXPECTED2 if ADDITIONS else EXPECTED

            if check_expected:
                assert m.sql.strip() == expected  # sql generated OK

            m.apply()
            # check for changes again and make sure none are pending
            if create_extensions_only:
                m.add_extension_changes(drops=False)
                assert (
                    m.changes.i_from.extensions.items()
                    >= m.changes.i_target.extensions.items()
                )
            else:
                m.add_all_changes(privileges=with_privileges)

                # y0 = yaml.safe_dump(m.changes.i_from._as_dicts())
                # y1 = yaml.safe_dump(m.changes.i_target._as_dicts())

                # print(textdiff(y0, y1))
                # print(m.statements)

                assert m.changes.i_from == m.changes.i_target
            assert not m.statements  # no further statements to apply
            assert m.sql == ""
            out, err = outs()

        assert run(args, out=out, err=err) == 0
        # test alternative parameters
        with S(d0) as s0, S(d1) as s1:
            m = Migration(
                get_inspector(s0), get_inspector(s1), ignore_extension_versions=True
            )
        # test empty
        m = Migration(None, None)
        m.add_all_changes(privileges=with_privileges)
        with raises(AttributeError):
            m.s_from
        with raises(AttributeError):
            m.s_target
        args = parse_args(flags + ["EMPTY", "EMPTY"])
        out, err = outs()
        assert run(args, out=out, err=err) == 0


def test_from_file_valid():
    import tempfile
    import os

    fixture_path = "tests/FIXTURES/enumdeps/"
    with open(fixture_path + "a.sql") as f:
        a_sql = f.read()
    with open(fixture_path + "b.sql") as f:
        b_sql = f.read()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".sql", delete=False
    ) as fa, tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as fb:
        fa.write(a_sql)
        fb.write(b_sql)
        fa_path = fa.name
        fb_path = fb.name

    try:
        args = parse_args(["--unsafe", "--from-file", fa_path, fb_path])
        out, err = io.StringIO(), io.StringIO()
        status = run(args, out=out, err=err)
        assert status == 2
        output = out.getvalue().strip()
        assert "drop view" in output
        assert "create or replace view" in output
    finally:
        os.unlink(fa_path)
        os.unlink(fb_path)


def test_from_file_nonexistent():
    args = parse_args(["--unsafe", "--from-file", "nonexistent_file.sql", "other.sql"])
    out, err = io.StringIO(), io.StringIO()
    status = run(args, out=out, err=err)
    assert status == 1
    assert "nonexistent_file.sql" in err.getvalue()


def test_from_file_bad_sql():
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
        f.write("this is not valid SQL;")
        bad_path = f.name

    try:
        args = parse_args(["--unsafe", "--from-file", bad_path, bad_path])
        out, err = io.StringIO(), io.StringIO()
        status = run(args, out=out, err=err)
        assert status == 1
        assert "error" in err.getvalue().lower()
    finally:
        os.unlink(bad_path)


def test_from_file_with_url():
    args = parse_args(
        [
            "--unsafe",
            "--from-file",
            "postgresql://localhost/db_from",
            "postgresql://localhost/db_target",
        ]
    )
    out, err = io.StringIO(), io.StringIO()
    status = run(args, out=out, err=err)
    assert status == 1
    assert "URL" in err.getvalue()


# --- JSON output tests ---


def test_json_output_classify_drop_table():
    from migra.command import classify_sql_statement

    info = classify_sql_statement('DROP TABLE IF EXISTS "public"."users";')
    assert info["risk"] == "destructive"
    assert info["type"] == "DROP TABLE"
    assert info["operation"] == "DROP"
    assert info["object"] == '"public"."users"'


def test_json_output_classify_drop_column():
    from migra.command import classify_sql_statement

    info = classify_sql_statement('ALTER TABLE "public"."users" DROP COLUMN "email";')
    assert info["risk"] == "destructive"
    assert info["type"] == "ALTER TABLE"
    assert info["operation"] == "DROP COLUMN"


def test_json_output_classify_truncate():
    from migra.command import classify_sql_statement

    info = classify_sql_statement('TRUNCATE "public"."users";')
    assert info["risk"] == "destructive"
    assert info["type"] == "TRUNCATE"
    assert info["operation"] == "TRUNCATE"


def test_json_output_classify_rename():
    from migra.command import classify_sql_statement

    info = classify_sql_statement('ALTER TABLE "public"."users" RENAME TO "customers";')
    assert info["risk"] == "warning"
    assert info["type"] == "ALTER TABLE"
    assert info["operation"] == "RENAME"


def test_json_output_classify_safe():
    from migra.command import classify_sql_statement

    info = classify_sql_statement('CREATE TABLE "public"."users" ("id" integer);')
    assert info["risk"] == "safe"
    assert info["type"] == "CREATE TABLE"
    assert info["operation"] == "CREATE"


def test_json_output_classify_drop_view_not_destructive():
    from migra.command import classify_sql_statement

    info = classify_sql_statement('DROP VIEW IF EXISTS "public"."v";')
    assert info["risk"] == "safe"
    assert info["type"] == "DROP VIEW"
    assert info["operation"] == "DROP"


def test_json_output_format_empty():
    from migra.command import format_json_output

    result = format_json_output([], "source_url", "target_url")
    import json

    data = json.loads(result)
    assert data["version"] == "1.0"
    assert data["summary"]["total_statements"] == 0
    assert data["summary"]["has_destructive_operations"] is False
    assert data["summary"]["risk_level"] == "low"
    assert data["statements"] == []


def test_json_output_format_mixed():
    from migra.command import format_json_output

    statements = [
        'CREATE TABLE "public"."users" ("id" integer);',
        'DROP TABLE "public"."legacy";',
        'ALTER TABLE "public"."t" RENAME TO "t2";',
    ]
    result = format_json_output(
        statements,
        "postgresql://user:pass@localhost/db_a",
        "postgresql://user:pass@localhost/db_b",
    )
    import json

    data = json.loads(result)
    assert data["version"] == "1.0"
    assert data["summary"]["total_statements"] == 3
    assert data["summary"]["has_destructive_operations"] is True
    assert data["summary"]["risk_level"] == "high"

    # Check credentials redacted
    assert "***:***" in data["source"]
    assert "user:pass" not in data["source"]
    assert "***:***" in data["target"]
    assert "user:pass" not in data["target"]

    # Check statement details
    assert data["statements"][0]["risk"] == "safe"
    assert data["statements"][1]["risk"] == "destructive"
    assert data["statements"][2]["risk"] == "warning"


def test_json_output_format_warning_level():
    from migra.command import format_json_output

    statements = [
        'ALTER TABLE "public"."users" RENAME TO "customers";',
    ]
    result = format_json_output(statements, "s1", "s2")
    import json

    data = json.loads(result)
    assert data["summary"]["has_destructive_operations"] is False
    assert data["summary"]["risk_level"] == "medium"


def test_json_output_integration():
    import json

    fixture_path = "tests/FIXTURES/enumdeps/"
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            load_sql_from_file(s0, fixture_path + "a.sql")
            load_sql_from_file(s1, fixture_path + "b.sql")

        args = parse_args(["--unsafe", "--output", "json", d0, d1])
        out, err = io.StringIO(), io.StringIO()
        status = run(args, out=out, err=err)
        assert status == 2
        data = json.loads(out.getvalue())

        assert data["version"] == "1.0"
        assert data["summary"]["total_statements"] > 0
        for stmt in data["statements"]:
            assert "sql" in stmt
            assert "type" in stmt
            assert "operation" in stmt
            assert "object" in stmt
            assert "risk" in stmt
            assert stmt["risk"] in ("safe", "warning", "destructive")
        assert isinstance(data["summary"]["has_destructive_operations"], bool)
        assert data["summary"]["risk_level"] in ("low", "medium", "high")
        assert "generated_at" in data


def test_json_output_empty_diff():
    import json

    args = parse_args(["--unsafe", "--output", "json", "EMPTY", "EMPTY"])
    out, err = io.StringIO(), io.StringIO()
    status = run(args, out=out, err=err)
    assert status == 0
    data = json.loads(out.getvalue())
    assert data["summary"]["total_statements"] == 0
    assert data["summary"]["risk_level"] == "low"
    assert data["statements"] == []


def test_json_output_from_file():
    import json
    import tempfile
    import os

    fixture_path = "tests/FIXTURES/enumdeps/"
    with open(fixture_path + "a.sql") as f:
        a_sql = f.read()
    with open(fixture_path + "b.sql") as f:
        b_sql = f.read()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".sql", delete=False
    ) as fa, tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as fb:
        fa.write(a_sql)
        fb.write(b_sql)
        fa_path = fa.name
        fb_path = fb.name

    try:
        args = parse_args(
            ["--unsafe", "--from-file", "--output", "json", fa_path, fb_path]
        )
        out, err = io.StringIO(), io.StringIO()
        status = run(args, out=out, err=err)
        assert status == 2
        data = json.loads(out.getvalue())
        # In from-file mode, source/target should be file paths
        assert data["source"] == fa_path
        assert data["target"] == fb_path
        assert data["summary"]["total_statements"] > 0
    finally:
        os.unlink(fa_path)
        os.unlink(fb_path)


def test_json_output_credential_redaction():
    from migra.command import redact_credentials

    assert (
        redact_credentials("postgresql://user:secret@localhost/db")
        == "postgresql://***:***@localhost/db"
    )
    assert (
        redact_credentials("postgresql://localhost/db") == "postgresql://localhost/db"
    )
    assert redact_credentials("schema_a.sql") == "schema_a.sql"


# --- Composite type tests ---


def test_composite_type_field_added():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s0.execute("CREATE TYPE public.address AS (street text, city text);")
            s1.execute(
                "CREATE TYPE public.address AS (street text, city text, postcode text);"
            )

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        assert "drop type" in sql
        assert "create type" in sql
        assert "postcode" in sql


def test_composite_type_field_removed():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s0.execute(
                "CREATE TYPE public.address AS (street text, city text, postcode text);"
            )
            s1.execute("CREATE TYPE public.address AS (street text, city text);")

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        assert "drop type" in sql
        assert "create type" in sql
        assert "postcode" not in sql


def test_composite_type_field_type_changed():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s0.execute("CREATE TYPE public.address AS (street text, city text);")
            s1.execute(
                "CREATE TYPE public.address AS (street varchar(100), city text);"
            )

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        assert "drop type" in sql
        assert "create type" in sql


def test_composite_type_dropped():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s0.execute("CREATE TYPE public.address AS (street text, city text);")

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        assert "drop type" in sql
        assert "address" in sql


def test_composite_type_added():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s1.execute("CREATE TYPE public.address AS (street text, city text);")

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        assert "create type" in sql
        assert "address" in sql


# --- Domain tests ---


def test_domain_constraint_added():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s0.execute(
                "CREATE DOMAIN public.positive_int AS integer CHECK (VALUE > 0);"
            )
            s1.execute(
                "CREATE DOMAIN public.positive_int AS integer CHECK (VALUE > 0) CHECK (VALUE < 1000000);"
            )

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        assert "drop domain" in sql
        assert "create domain" in sql


def test_domain_base_type_changed():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s0.execute(
                "CREATE DOMAIN public.positive_int AS integer CHECK (VALUE > 0);"
            )
            s1.execute("CREATE DOMAIN public.positive_int AS bigint CHECK (VALUE > 0);")

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        assert "drop domain" in sql
        assert "create domain" in sql


def test_domain_dropped():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s0.execute(
                "CREATE DOMAIN public.positive_int AS integer CHECK (VALUE > 0);"
            )

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        assert "drop domain" in sql


def test_domain_added():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s1.execute(
                "CREATE DOMAIN public.positive_int AS integer CHECK (VALUE > 0);"
            )

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        assert "create domain" in sql


# --- Materialized view dependency ordering tests ---


def _mv_create_names(sql):
    import re

    names = []
    for block in sql.strip().split("\n\n"):
        block = block.strip()
        if not block:
            continue
        first_line = block.split("\n")[0]
        m = re.search(
            r'CREATE MATERIALIZED VIEW\s+"([^"]+)"\."([^"]+)"',
            first_line,
            re.IGNORECASE,
        )
        if m:
            names.append(m.group(2))
    return names


def test_mv_dependency_ordering_two_views():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s0.execute("CREATE TABLE public.users (id int, name text);")
            s1.execute("CREATE TABLE public.users (id int, name text);")
            s1.execute(
                "CREATE MATERIALIZED VIEW public.base_view AS SELECT id FROM public.users;"
            )
            s1.execute(
                "CREATE MATERIALIZED VIEW public.derived_view AS SELECT id FROM public.base_view;"
            )

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        names = _mv_create_names(m.sql)
        assert names == ["base_view", "derived_view"]


def test_mv_dependency_ordering_chain():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s0.execute("CREATE TABLE public.users (id int, name text);")
            s1.execute("CREATE TABLE public.users (id int, name text);")
            s1.execute(
                "CREATE MATERIALIZED VIEW public.a AS SELECT id FROM public.users;"
            )
            s1.execute("CREATE MATERIALIZED VIEW public.b AS SELECT id FROM public.a;")
            s1.execute("CREATE MATERIALIZED VIEW public.c AS SELECT id FROM public.b;")

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        names = _mv_create_names(m.sql)
        assert names == ["a", "b", "c"]


# --- Enum evolution tests ---


def test_enum_value_added():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s0.execute(
                "CREATE TYPE public.status AS ENUM ('pending', 'active', 'inactive');"
            )
            s1.execute(
                "CREATE TYPE public.status AS ENUM ('pending', 'active', 'inactive', 'archived');"
            )

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        sql_upper = sql.upper()
        assert "ALTER TYPE" in sql_upper
        assert "ADD VALUE" in sql_upper
        assert "archived" in sql
        assert "drop type" not in sql


def test_enum_value_removed():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s0.execute(
                "CREATE TYPE public.status AS ENUM ('pending', 'active', 'inactive');"
            )
            s1.execute("CREATE TYPE public.status AS ENUM ('pending', 'active');")

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        assert "drop type" in sql
        assert "create type" in sql


def test_enum_value_reordered():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s0.execute(
                "CREATE TYPE public.status AS ENUM ('pending', 'active', 'inactive');"
            )
            s1.execute(
                "CREATE TYPE public.status AS ENUM ('active', 'inactive', 'pending');"
            )

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        assert "drop type" in sql
        assert "create type" in sql


def test_enum_type_dropped():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s0.execute(
                "CREATE TYPE public.status AS ENUM ('pending', 'active', 'inactive');"
            )

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        assert "drop type" in sql


def test_enum_type_added():
    with temporary_database(host="localhost") as d0, temporary_database(
        host="localhost"
    ) as d1:
        with S(d0) as s0, S(d1) as s1:
            s1.execute(
                "CREATE TYPE public.status AS ENUM ('pending', 'active', 'inactive');"
            )

        m = Migration(s0, s1)
        m.set_safety(False)
        m.add_all_changes()
        sql = m.sql.strip()
        assert "create type" in sql
        assert "enum" in sql

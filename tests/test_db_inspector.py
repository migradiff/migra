from __future__ import unicode_literals

from unittest.mock import MagicMock, patch

# ---- compare_schemas unit tests (mocked inspectors) ----


def _make_mock_inspector(config):
    """Build a mock inspector with the given structure.

    config is a dict with keys: schemas, tables, views, enums,
    extensions, functions, sequences, indexes, constraints.
    Each value is a list of (key, mock_obj) tuples that get
    turned into an OrderedDict.
    """
    from collections import OrderedDict

    mock = MagicMock()
    mock.schemas = OrderedDict(config.get("schemas", []))
    mock.tables = OrderedDict(config.get("tables", []))
    mock.views = OrderedDict(config.get("views", []))
    mock.enums = OrderedDict(config.get("enums", []))
    mock.extensions = OrderedDict(config.get("extensions", []))
    mock.functions = OrderedDict(config.get("functions", []))
    mock.sequences = OrderedDict(config.get("sequences", []))
    mock.indexes = OrderedDict(config.get("indexes", []))
    mock.constraints = OrderedDict(config.get("constraints", []))
    return mock


def _col(name, dbtype, not_null=False, default=None):
    c = MagicMock()
    c.name = name
    c.dbtype = dbtype
    c.not_null = not_null
    c.default = default
    return c


def _columns(*cols):
    from collections import OrderedDict

    return OrderedDict((c.name, c) for c in cols)


class TestCompareSchemas:
    def test_identical_schemas(self):
        from migra.db_inspector import compare_schemas

        old_schema = {"inspector": _make_mock_inspector({}), "table_sizes": {}}
        new_schema = {"inspector": _make_mock_inspector({}), "table_sizes": {}}
        diff = compare_schemas(old_schema, new_schema)
        for category in diff.values():
            assert category == []

    def test_table_added(self):
        from migra.db_inspector import compare_schemas

        t = MagicMock()
        t.columns = _columns(_col("id", "integer", not_null=True))
        old = {"inspector": _make_mock_inspector({}), "table_sizes": {}}
        new = {
            "inspector": _make_mock_inspector({"tables": [('"public"."users"', t)]}),
            "table_sizes": {},
        }
        diff = compare_schemas(old, new)
        assert len(diff["tables"]) == 1
        assert diff["tables"][0]["status"] == "added"
        assert diff["tables"][0]["name"] == '"public"."users"'

    def test_table_removed(self):
        from migra.db_inspector import compare_schemas

        t = MagicMock()
        t.columns = _columns(_col("id", "integer"))
        old = {
            "inspector": _make_mock_inspector({"tables": [('"public"."users"', t)]}),
            "table_sizes": {},
        }
        new = {"inspector": _make_mock_inspector({}), "table_sizes": {}}
        diff = compare_schemas(old, new)
        assert len(diff["tables"]) == 1
        assert diff["tables"][0]["status"] == "removed"

    def test_column_added(self):
        from migra.db_inspector import compare_schemas

        old_t = MagicMock()
        old_t.columns = _columns(_col("id", "integer"))
        new_t = MagicMock()
        new_t.columns = _columns(_col("id", "integer"), _col("email", "text"))
        old = {
            "inspector": _make_mock_inspector(
                {"tables": [('"public"."users"', old_t)]}
            ),
            "table_sizes": {},
        }
        new = {
            "inspector": _make_mock_inspector(
                {"tables": [('"public"."users"', new_t)]}
            ),
            "table_sizes": {},
        }
        diff = compare_schemas(old, new)
        assert len(diff["tables"]) == 1
        mods = diff["tables"][0]["modifications"]
        assert any(m["type"] == "column_added" and m["column"] == "email" for m in mods)

    def test_column_removed(self):
        from migra.db_inspector import compare_schemas

        old_t = MagicMock()
        old_t.columns = _columns(_col("id", "integer"), _col("legacy", "text"))
        new_t = MagicMock()
        new_t.columns = _columns(_col("id", "integer"))
        old = {
            "inspector": _make_mock_inspector(
                {"tables": [('"public"."users"', old_t)]}
            ),
            "table_sizes": {},
        }
        new = {
            "inspector": _make_mock_inspector(
                {"tables": [('"public"."users"', new_t)]}
            ),
            "table_sizes": {},
        }
        diff = compare_schemas(old, new)
        mods = diff["tables"][0]["modifications"]
        assert any(
            m["type"] == "column_removed" and m["column"] == "legacy" for m in mods
        )

    def test_column_type_changed(self):
        from migra.db_inspector import compare_schemas

        old_t = MagicMock()
        old_t.columns = _columns(_col("status", "varchar(50)"))
        new_t = MagicMock()
        new_t.columns = _columns(_col("status", "text"))
        old = {
            "inspector": _make_mock_inspector(
                {"tables": [('"public"."users"', old_t)]}
            ),
            "table_sizes": {},
        }
        new = {
            "inspector": _make_mock_inspector(
                {"tables": [('"public"."users"', new_t)]}
            ),
            "table_sizes": {},
        }
        diff = compare_schemas(old, new)
        mods = diff["tables"][0]["modifications"]
        assert any(
            m["type"] == "column_modified"
            and m["column"] == "status"
            and "varchar" in m["old_type"]
            and "text" in m["new_type"]
            for m in mods
        )

    def test_view_added(self):
        from migra.db_inspector import compare_schemas

        v = MagicMock()
        v.definition = "SELECT 1"
        old = {"inspector": _make_mock_inspector({}), "table_sizes": {}}
        new = {
            "inspector": _make_mock_inspector({"views": [('"public"."v"', v)]}),
            "table_sizes": {},
        }
        diff = compare_schemas(old, new)
        assert len(diff["views"]) == 1
        assert diff["views"][0]["status"] == "added"

    def test_enum_added(self):
        from migra.db_inspector import compare_schemas

        e = MagicMock()
        e.elements = ["active", "inactive"]
        old = {"inspector": _make_mock_inspector({}), "table_sizes": {}}
        new = {
            "inspector": _make_mock_inspector({"enums": [('"public"."mood"', e)]}),
            "table_sizes": {},
        }
        diff = compare_schemas(old, new)
        assert len(diff["enums"]) == 1
        assert diff["enums"][0]["status"] == "added"

    def test_extension_added(self):
        from migra.db_inspector import compare_schemas

        old = {"inspector": _make_mock_inspector({}), "table_sizes": {}}
        new = {
            "inspector": _make_mock_inspector(
                {"extensions": [("pgcrypto", MagicMock())]}
            ),
            "table_sizes": {},
        }
        diff = compare_schemas(old, new)
        assert len(diff["extensions"]) == 1

    def test_index_added(self):
        from migra.db_inspector import compare_schemas

        idx = MagicMock()
        idx.quoted_full_table_name = '"public"."users"'
        idx.definition = "CREATE INDEX ..."
        old = {"inspector": _make_mock_inspector({}), "table_sizes": {}}
        new = {
            "inspector": _make_mock_inspector(
                {"indexes": [('"public"."idx_users_email"', idx)]}
            ),
            "table_sizes": {},
        }
        diff = compare_schemas(old, new)
        assert len(diff["indexes"]) == 1
        assert diff["indexes"][0]["status"] == "added"
        assert diff["indexes"][0]["table"] == '"public"."users"'

    def test_constraint_added(self):
        from migra.db_inspector import compare_schemas

        con = MagicMock()
        con.quoted_full_table_name = '"public"."users"'
        con.constraint_type = "UNIQUE"
        old = {"inspector": _make_mock_inspector({}), "table_sizes": {}}
        new = {
            "inspector": _make_mock_inspector(
                {"constraints": [('"public"."users_pkey"', con)]}
            ),
            "table_sizes": {},
        }
        diff = compare_schemas(old, new)
        assert len(diff["constraints"]) == 1

    def test_schema_added(self):
        from migra.db_inspector import compare_schemas

        old = {"inspector": _make_mock_inspector({}), "table_sizes": {}}
        new_s = MagicMock()
        new = {
            "inspector": _make_mock_inspector({"schemas": [("private", new_s)]}),
            "table_sizes": {},
        }
        diff = compare_schemas(old, new)
        assert len(diff["schemas"]) == 1


class TestGetRemoteSchema:
    def test_table_sizes_fetch(self):
        from migra.db_inspector import _fetch_table_sizes

        class MockRow:
            def __getitem__(self, i):
                return [("public", "users", 100), ("public", "orders", 50)][i]

        mock_conn = MagicMock()
        mock_rows = MagicMock()
        mock_rows.fetchall.return_value = [
            MockRow.__getitem__(None, 0),
            MockRow.__getitem__(None, 1),
        ]
        mock_conn.execute.return_value = mock_rows

        with patch("sqlbag.S") as mock_s:
            mock_s.return_value.__enter__.return_value = mock_conn
            sizes = _fetch_table_sizes("postgresql://localhost/test")
            assert "public.users" in sizes
            assert sizes["public.users"] == 100

    def test_get_remote_schema_integration(self):
        mock_inspector = MagicMock()
        with patch("schemainspect.get_inspector", return_value=mock_inspector):
            with patch("migra.db_inspector._fetch_table_sizes", return_value={}):
                from migra.db_inspector import get_remote_schema

                result = get_remote_schema("postgresql://localhost/test")
                assert "inspector" in result
                assert "table_sizes" in result

from __future__ import unicode_literals


def get_remote_schema(connection_string):
    from schemainspect import get_inspector

    inspector = get_inspector(connection_string)
    table_sizes = _fetch_table_sizes(connection_string)
    return {"inspector": inspector, "table_sizes": table_sizes}


def _fetch_table_sizes(conn_url):
    from sqlbag import S

    sizes = {}
    try:
        with S(conn_url) as s:
            rows = s.execute("""
                SELECT schemaname, relname, n_live_tup
                FROM pg_stat_user_tables
            """)
            for row in (rows.fetchall() if hasattr(rows, "fetchall") else rows):
                sizes["{}.{}".format(row[0], row[1])] = int(row[2]) if row[2] else 0
    except Exception:
        pass
    return sizes


def compare_schemas(old, new):
    old_insp = old["inspector"]
    new_insp = new["inspector"]

    diff = {
        "schemas": _compare_schema_list(old_insp, new_insp),
        "tables": _compare_tables(old_insp, new_insp),
        "views": _compare_views(old_insp, new_insp),
        "enums": _compare_enums(old_insp, new_insp),
        "extensions": _compare_extensions(old_insp, new_insp),
        "functions": _compare_functions(old_insp, new_insp),
        "sequences": _compare_sequences(old_insp, new_insp),
        "indexes": _compare_indexes(old_insp, new_insp),
        "constraints": _compare_constraints(old_insp, new_insp),
    }
    return diff


def _compare_schema_list(old_insp, new_insp):
    old_schemas = set(old_insp.schemas.keys())
    new_schemas = set(new_insp.schemas.keys())
    added = sorted(new_schemas - old_schemas)
    removed = sorted(old_schemas - new_schemas)
    changes = []
    for s in added:
        changes.append({"name": s, "status": "added"})
    for s in removed:
        changes.append({"name": s, "status": "removed"})
    return changes


def _column_info(col):
    parts = [col.dbtype]
    if col.not_null:
        parts.append("NOT NULL")
    if col.default:
        parts.append("DEFAULT {}".format(col.default))
    return " ".join(parts)


def _compare_tables(old_insp, new_insp):
    old_tables = set(old_insp.tables.keys())
    new_tables = set(new_insp.tables.keys())
    added = sorted(new_tables - old_tables)
    removed = sorted(old_tables - new_tables)
    common = sorted(old_tables & new_tables)

    changes = []
    for t in removed:
        table_obj = old_insp.tables[t]
        changes.append(
            {
                "name": t,
                "status": "removed",
                "columns": [
                    {"name": c.name, "type": _column_info(c)}
                    for c in table_obj.columns.values()
                ],
            }
        )
    for t in added:
        table_obj = new_insp.tables[t]
        changes.append(
            {
                "name": t,
                "status": "added",
                "columns": [
                    {"name": c.name, "type": _column_info(c)}
                    for c in table_obj.columns.values()
                ],
            }
        )
    for t in common:
        old_t = old_insp.tables[t]
        new_t = new_insp.tables[t]
        modifications = []

        old_cols = {c.name: c for c in old_t.columns.values()}
        new_cols = {c.name: c for c in new_t.columns.values()}

        added_cols = sorted(set(new_cols.keys()) - set(old_cols.keys()))
        removed_cols = sorted(set(old_cols.keys()) - set(new_cols.keys()))
        common_cols = sorted(set(old_cols.keys()) & set(new_cols.keys()))

        for cn in removed_cols:
            modifications.append(
                {
                    "type": "column_removed",
                    "column": cn,
                    "old_type": _column_info(old_cols[cn]),
                }
            )
        for cn in added_cols:
            modifications.append(
                {
                    "type": "column_added",
                    "column": cn,
                    "new_type": _column_info(new_cols[cn]),
                }
            )
        for cn in common_cols:
            old_col = old_cols[cn]
            new_col = new_cols[cn]
            if old_col.dbtype != new_col.dbtype or old_col.not_null != new_col.not_null:
                modifications.append(
                    {
                        "type": "column_modified",
                        "column": cn,
                        "old_type": _column_info(old_col),
                        "new_type": _column_info(new_col),
                    }
                )

        if modifications:
            changes.append(
                {"name": t, "status": "modified", "modifications": modifications}
            )

    return changes


def _compare_views(old_insp, new_insp):
    old_views = set(old_insp.views.keys())
    new_views = set(new_insp.views.keys())
    added = sorted(new_views - old_views)
    removed = sorted(old_views - new_views)
    common = sorted(old_views & new_views)

    changes = []
    for v in removed:
        view_obj = old_insp.views[v]
        changes.append(
            {
                "name": v,
                "status": "removed",
                "definition": view_obj.definition,
            }
        )
    for v in added:
        view_obj = new_insp.views[v]
        changes.append(
            {
                "name": v,
                "status": "added",
                "definition": view_obj.definition,
            }
        )
    for v in common:
        old_v = old_insp.views[v]
        new_v = new_insp.views[v]
        if old_v.definition != new_v.definition:
            changes.append(
                {
                    "name": v,
                    "status": "modified",
                    "old_definition": old_v.definition,
                    "new_definition": new_v.definition,
                }
            )
    return changes


def _compare_enums(old_insp, new_insp):
    old_enums = set(old_insp.enums.keys())
    new_enums = set(new_insp.enums.keys())
    added = sorted(new_enums - old_enums)
    removed = sorted(old_enums - new_enums)
    common = sorted(old_enums & new_enums)

    changes = []
    for e in removed:
        changes.append(
            {
                "name": e,
                "status": "removed",
                "elements": list(old_insp.enums[e].elements),
            }
        )
    for e in added:
        changes.append(
            {"name": e, "status": "added", "elements": list(new_insp.enums[e].elements)}
        )
    for e in common:
        old_elements = list(old_insp.enums[e].elements)
        new_elements = list(new_insp.enums[e].elements)
        if old_elements != new_elements:
            changes.append(
                {
                    "name": e,
                    "status": "modified",
                    "old_elements": old_elements,
                    "new_elements": new_elements,
                }
            )
    return changes


def _compare_extensions(old_insp, new_insp):
    old_exts = set(old_insp.extensions.keys())
    new_exts = set(new_insp.extensions.keys())
    added = sorted(new_exts - old_exts)
    removed = sorted(old_exts - new_exts)
    changes = []
    for e in removed:
        changes.append({"name": e, "status": "removed"})
    for e in added:
        changes.append({"name": e, "status": "added"})
    return changes


def _compare_functions(old_insp, new_insp):
    old_funcs = set(old_insp.functions.keys())
    new_funcs = set(new_insp.functions.keys())
    added = sorted(new_funcs - old_funcs)
    removed = sorted(old_funcs - new_funcs)
    changes = []
    for f in removed:
        changes.append({"name": f, "status": "removed"})
    for f in added:
        changes.append({"name": f, "status": "added"})
    return changes


def _compare_sequences(old_insp, new_insp):
    old_seqs = set(old_insp.sequences.keys())
    new_seqs = set(new_insp.sequences.keys())
    added = sorted(new_seqs - old_seqs)
    removed = sorted(old_seqs - new_seqs)
    changes = []
    for s in removed:
        changes.append({"name": s, "status": "removed"})
    for s in added:
        changes.append({"name": s, "status": "added"})
    return changes


def _compare_indexes(old_insp, new_insp):
    old_set = set(old_insp.indexes.keys())
    new_set = set(new_insp.indexes.keys())
    added = sorted(new_set - old_set)
    removed = sorted(old_set - new_set)
    changes = []
    for i in removed:
        idx = old_insp.indexes[i]
        changes.append(
            {
                "name": i,
                "status": "removed",
                "table": idx.quoted_full_table_name,
                "definition": idx.definition,
            }
        )
    for i in added:
        idx = new_insp.indexes[i]
        changes.append(
            {
                "name": i,
                "status": "added",
                "table": idx.quoted_full_table_name,
                "definition": idx.definition,
            }
        )
    return changes


def _compare_constraints(old_insp, new_insp):
    old_set = set(old_insp.constraints.keys())
    new_set = set(new_insp.constraints.keys())
    added = sorted(new_set - old_set)
    removed = sorted(old_set - new_set)
    changes = []
    for c in removed:
        con = old_insp.constraints[c]
        changes.append(
            {
                "name": c,
                "status": "removed",
                "table": con.quoted_full_table_name,
                "type": con.constraint_type,
            }
        )
    for c in added:
        con = new_insp.constraints[c]
        changes.append(
            {
                "name": c,
                "status": "added",
                "table": con.quoted_full_table_name,
                "type": con.constraint_type,
            }
        )
    return changes

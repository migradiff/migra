from __future__ import unicode_literals

from datetime import datetime, timezone

from .ai_explain import DEFAULT_MODEL, MAX_TOKENS, TEMPERATURE, redact_api_key

DRIFT_SYSTEM_PROMPT = (
    "You are a PostgreSQL schema drift analysis expert. You will be given"
    " differences between two database schemas along with table size"
    " information from the production database. Explain what changed in"
    " plain English, highlight breaking changes, and note any data"
    " migration risks.\n"
    "\n"
    "Format your response as:\n"
    "\n"
    "Schema Drift Analysis: <source> \u2192 <target>\n"
    "\n"
    "Changes Detected:\n"
    "\n"
    "1. <table/view/schema> \u2014 <DROPPED/MODIFIED/NEW>\n"
    "   - <specific changes>\n"
    "\n"
    "Risk Analysis:\n"
    "- BREAKING: <reason>\n"
    "- WARNING: <reason>\n"
    "- INFO: <reason>\n"
    "\n"
    "Be concise and practical. Only note meaningful changes."
)


def _build_diff_summary(diff, from_label, to_label, table_sizes):
    lines = []
    lines.append("Schema Drift Analysis: {} \u2192 {}".format(from_label, to_label))
    lines.append("")
    lines.append("--- Changes by Category ---")
    lines.append("")

    for category, label in [
        ("schemas", "Schemas"),
        ("tables", "Tables"),
        ("views", "Views"),
        ("enums", "Enums"),
        ("extensions", "Extensions"),
        ("functions", "Functions"),
        ("sequences", "Sequences"),
        ("indexes", "Indexes"),
        ("constraints", "Constraints"),
    ]:
        items = diff.get(category, [])
        if not items:
            continue
        lines.append("{} ({}):".format(label, len(items)))
        for item in items:
            if item["status"] == "added":
                lines.append("  + {}: NEW".format(item["name"]))
            elif item["status"] == "removed":
                lines.append("  - {}: DROPPED".format(item["name"]))
            elif item["status"] == "modified":
                lines.append("  ~ {}: MODIFIED".format(item["name"]))
                modifications = item.get("modifications", [])
                for mod in modifications:
                    if mod["type"] == "column_removed":
                        lines.append(
                            "    - Column '{}' ({}) removed".format(
                                mod["column"], mod["old_type"]
                            )
                        )
                    elif mod["type"] == "column_added":
                        lines.append(
                            "    + Column '{}' ({}) added".format(
                                mod["column"], mod["new_type"]
                            )
                        )
                    elif mod["type"] == "column_modified":
                        lines.append(
                            "    ~ Column '{}': {} \u2192 {}".format(
                                mod["column"], mod["old_type"], mod["new_type"]
                            )
                        )
                if "old_definition" in item:
                    lines.append("    Definition changed")
        lines.append("")

    lines.append("--- Live Table Sizes ---")
    if table_sizes:
        for name, count in sorted(table_sizes.items()):
            lines.append("  {}: ~{} rows".format(name, count))
    else:
        lines.append("  (no size data available)")
    lines.append("")

    return "\n".join(lines)


class DriftExplainer:
    def __init__(self, api_key):
        self.api_key = api_key

    def explain_drift(self, diff, from_label, to_label, table_sizes):
        import anthropic

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        diff_summary = _build_diff_summary(diff, from_label, to_label, table_sizes)

        client = anthropic.Anthropic(api_key=self.api_key)
        try:
            response = client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=DRIFT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": diff_summary}],
            )
            text = response.content[0].text
            return {
                "text": text,
                "model": DEFAULT_MODEL,
                "generated_at": timestamp,
            }
        except Exception as e:
            msg = redact_api_key(str(e))
            raise RuntimeError("MigraDiff: AI drift analysis failed: {}".format(msg))

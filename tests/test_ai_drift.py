from __future__ import unicode_literals

from unittest.mock import MagicMock, patch

import pytest


def mock_anthropic():
    """Patch anthropic.Anthropic so lazy imports see the mock."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock()]
    mock_message.content[0].text = (
        "Schema Drift Analysis: old_db \u2192 new_db\n\n"
        "Changes Detected:\n\n"
        '1. "users" \u2014 MODIFIED\n'
        '   - Column "email" type changed: VARCHAR \u2192 TEXT\n\n'
        "Risk Analysis:\n"
        "- WARNING: Column type change may require data migration"
    )
    mock_response.content = mock_message.content
    mock_client.messages.create.return_value = mock_response

    patcher = patch("anthropic.Anthropic", return_value=mock_client)
    mock_anthropic_class = patcher.start()
    return patcher, mock_anthropic_class, mock_client


class TestDriftExplainer:
    def test_explain_drift_basic(self):
        from migra.ai_drift import DriftExplainer

        patcher, mock_anthropic_mod, mock_client = mock_anthropic()
        try:
            explainer = DriftExplainer(api_key="sk-ant-test-key")
            diff = {
                "tables": [
                    {
                        "name": '"public"."users"',
                        "status": "modified",
                        "modifications": [
                            {
                                "type": "column_modified",
                                "column": "email",
                                "old_type": "varchar(255)",
                                "new_type": "text",
                            }
                        ],
                    }
                ],
                "schemas": [],
                "views": [],
                "enums": [],
                "extensions": [],
                "functions": [],
                "sequences": [],
                "indexes": [],
                "constraints": [],
            }
            result = explainer.explain_drift(
                diff, "old_db", "new_db", {"public.users": 1000}
            )

            assert "text" in result
            assert "model" in result
            assert "generated_at" in result
            assert "Drift Analysis" in result["text"]

            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
            assert call_kwargs["temperature"] == 0
            assert "system" in call_kwargs
        finally:
            patcher.stop()

    def test_explain_drift_empty_diff(self):
        from migra.ai_drift import DriftExplainer

        patcher, mock_anthropic_mod, mock_client = mock_anthropic()
        try:
            explainer = DriftExplainer(api_key="sk-ant-test-key")
            diff = {
                "tables": [],
                "schemas": [],
                "views": [],
                "enums": [],
                "extensions": [],
                "functions": [],
                "sequences": [],
                "indexes": [],
                "constraints": [],
            }
            result = explainer.explain_drift(diff, "a", "b", {})
            assert "text" in result
            mock_client.messages.create.assert_called_once()
        finally:
            patcher.stop()

    def test_explain_drift_error_redacts_key(self):
        from migra.ai_drift import DriftExplainer

        patcher = patch("anthropic.Anthropic")
        mock_anthropic_class = patcher.start()
        mock_client = MagicMock()
        error_msg = "API error: sk-ant-invalid-key-12345 is invalid"
        mock_client.messages.create.side_effect = RuntimeError(error_msg)
        mock_anthropic_class.return_value = mock_client

        try:
            explainer = DriftExplainer(api_key="sk-ant-invalid-key-12345")
            diff = {
                "tables": [],
                "schemas": [],
                "views": [],
                "enums": [],
                "extensions": [],
                "functions": [],
                "sequences": [],
                "indexes": [],
                "constraints": [],
            }
            with pytest.raises(RuntimeError) as exc_info:
                explainer.explain_drift(diff, "a", "b", {})
            error_text = str(exc_info.value)
            assert "sk-ant-***" in error_text
            assert "sk-ant-invalid-key-12345" not in error_text
        finally:
            patcher.stop()


class TestBuildDiffSummary:
    def test_summary_includes_table_sizes(self):
        from migra.ai_drift import _build_diff_summary

        diff = {
            "tables": [
                {
                    "name": '"public"."users"',
                    "status": "added",
                    "columns": [{"name": "id", "type": "integer"}],
                }
            ],
            "schemas": [],
            "views": [],
            "enums": [],
            "extensions": [],
            "functions": [],
            "sequences": [],
            "indexes": [],
            "constraints": [],
        }
        summary = _build_diff_summary(diff, "old", "new", {"public.users": 500})
        assert "public.users" in summary
        assert "500 rows" in summary
        assert "NEW" in summary

    def test_summary_no_table_sizes(self):
        from migra.ai_drift import _build_diff_summary

        diff = {
            "tables": [],
            "schemas": [],
            "views": [],
            "enums": [],
            "extensions": [],
            "functions": [],
            "sequences": [],
            "indexes": [],
            "constraints": [],
        }
        summary = _build_diff_summary(diff, "old", "new", {})
        assert "no size data" in summary

    def test_summary_shows_column_changes(self):
        from migra.ai_drift import _build_diff_summary

        diff = {
            "tables": [
                {
                    "name": '"public"."users"',
                    "status": "modified",
                    "modifications": [
                        {
                            "type": "column_modified",
                            "column": "email",
                            "old_type": "varchar(100)",
                            "new_type": "text",
                        },
                        {
                            "type": "column_added",
                            "column": "score",
                            "new_type": "integer",
                        },
                        {
                            "type": "column_removed",
                            "column": "legacy",
                            "old_type": "text",
                        },
                    ],
                }
            ],
            "schemas": [],
            "views": [],
            "enums": [],
            "extensions": [],
            "functions": [],
            "sequences": [],
            "indexes": [],
            "constraints": [],
        }
        summary = _build_diff_summary(diff, "old", "new", {})
        assert "MODIFIED" in summary
        assert "email" in summary
        assert "score" in summary
        assert "legacy" in summary

    def test_summary_shows_dropped_table_columns(self):
        from migra.ai_drift import _build_diff_summary

        diff = {
            "tables": [
                {
                    "name": '"public"."old_table"',
                    "status": "removed",
                    "columns": [
                        {"name": "id", "type": "integer"},
                        {"name": "data", "type": "text"},
                    ],
                }
            ],
            "schemas": [],
            "views": [],
            "enums": [],
            "extensions": [],
            "functions": [],
            "sequences": [],
            "indexes": [],
            "constraints": [],
        }
        summary = _build_diff_summary(diff, "old", "new", {})
        assert "DROPPED" in summary
        assert "old_table" in summary

    def test_summary_handles_enum_changes(self):
        from migra.ai_drift import _build_diff_summary

        diff = {
            "tables": [],
            "schemas": [],
            "views": [],
            "enums": [
                {
                    "name": '"public"."mood"',
                    "status": "added",
                    "elements": ["happy", "sad"],
                }
            ],
            "extensions": [],
            "functions": [],
            "sequences": [],
            "indexes": [],
            "constraints": [],
        }
        summary = _build_diff_summary(diff, "old", "new", {})
        assert "Enums" in summary
        assert "mood" in summary

    def test_summary_handles_view_changes(self):
        from migra.ai_drift import _build_diff_summary

        diff = {
            "tables": [],
            "schemas": [],
            "views": [
                {
                    "name": '"public"."v"',
                    "status": "modified",
                    "old_definition": "SELECT 1",
                    "new_definition": "SELECT 2",
                }
            ],
            "enums": [],
            "extensions": [],
            "functions": [],
            "sequences": [],
            "indexes": [],
            "constraints": [],
        }
        summary = _build_diff_summary(diff, "old", "new", {})
        assert "Views" in summary
        assert "Definition changed" in summary

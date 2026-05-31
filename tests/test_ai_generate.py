from __future__ import unicode_literals

import io
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from migra.command import parse_args, run

# ---- Helpers ----


def mock_anthropic():
    """Patch anthropic.Anthropic so lazy imports see the mock."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock()]
    mock_message.content[0].text = (
        "ALTER TABLE public.users ADD COLUMN email_verified boolean;\n"
        "ALTER TABLE public.users ADD COLUMN email_verified_at timestamptz;"
    )
    mock_response.content = mock_message.content
    mock_client.messages.create.return_value = mock_response

    patcher = patch("anthropic.Anthropic", return_value=mock_client)
    mock_anthropic_class = patcher.start()
    return patcher, mock_anthropic_class, mock_client


# ---- Safety rules tests ----


class TestCheckSafetyRules:
    def test_hard_refuse_drop_all(self):
        from migra.ai_explain import check_safety_rules

        result = check_safety_rules("drop all tables")
        assert result["action"] == "refuse"

    def test_hard_refuse_delete_all(self):
        from migra.ai_explain import check_safety_rules

        result = check_safety_rules("delete all users")
        assert result["action"] == "refuse"

    def test_hard_refuse_truncate_all(self):
        from migra.ai_explain import check_safety_rules

        result = check_safety_rules("truncate all tables")
        assert result["action"] == "refuse"

    def test_hard_refuse_drop_everything(self):
        from migra.ai_explain import check_safety_rules

        result = check_safety_rules("drop everything in the database")
        assert result["action"] == "refuse"

    def test_hard_refuse_wipe(self):
        from migra.ai_explain import check_safety_rules

        result = check_safety_rules("wipe the users table")
        assert result["action"] == "refuse"

    def test_soft_warn_drop(self):
        from migra.ai_explain import check_safety_rules

        result = check_safety_rules("drop the email column from users")
        assert result["action"] == "warn"

    def test_soft_warn_delete(self):
        from migra.ai_explain import check_safety_rules

        result = check_safety_rules("delete expired sessions")
        assert result["action"] == "warn"

    def test_soft_warn_truncate(self):
        from migra.ai_explain import check_safety_rules

        result = check_safety_rules("truncate the audit_log table")
        assert result["action"] == "warn"

    def test_clean_allow(self):
        from migra.ai_explain import check_safety_rules

        result = check_safety_rules("add email column to users table")
        assert result["action"] == "allow"

    def test_add_index_allow(self):
        from migra.ai_explain import check_safety_rules

        result = check_safety_rules("add index on orders.user_id")
        assert result["action"] == "allow"


# ---- Prompt building tests ----


class TestBuildGeneratePrompt:
    def test_basic_prompt_structure(self):
        from migra.ai_explain import build_generate_prompt

        prompt = build_generate_prompt(
            "add email column to users",
            "CREATE TABLE public.users (id integer);",
        )
        assert "Generate a PostgreSQL migration" in prompt
        assert "add email column to users" in prompt
        assert "CREATE TABLE public.users" in prompt

    def test_no_schema_context(self):
        from migra.ai_explain import build_generate_prompt

        prompt = build_generate_prompt("add index on orders.user_id", "")
        assert "No schema context available" in prompt


# ---- AIGenerator class tests ----


class TestAIGenerator:
    def test_generate_basic(self):
        from migra.ai_explain import AIGenerator

        patcher, mock_anthropic_mod, mock_client = mock_anthropic()
        try:
            generator = AIGenerator(api_key="sk-ant-test-key")
            result = generator.generate(
                "add email verification to users table, nullable initially",
                schema_context="CREATE TABLE public.users (id integer, email text);",
            )

            assert "text" in result
            assert "model" in result
            assert "generated_at" in result
            assert result["model"] == "claude-haiku-4-5-20251001"
            assert "Generated Migration" in result["text"]
            assert "ALTER TABLE" in result["text"]
            assert "schema_context_used" in result
            assert result["is_destructive"] is False

            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
            assert call_kwargs["max_tokens"] == 2048
            assert call_kwargs["temperature"] == 0
        finally:
            patcher.stop()

    def test_generate_no_schema(self):
        from migra.ai_explain import AIGenerator

        patcher, mock_anthropic_mod, mock_client = mock_anthropic()
        try:
            generator = AIGenerator(api_key="sk-ant-test-key")
            result = generator.generate(
                "add email column to users",
                schema_context="",
            )

            assert "No schema context available" in result["text"]
            assert "Warning" in result["text"]
        finally:
            patcher.stop()

    def test_refuse_bulk_destructive(self):
        from migra.ai_explain import AIGenerator

        generator = AIGenerator(api_key="sk-ant-test-key")
        result = generator.generate("drop all tables", schema_context="")
        assert "Refusing" in result["text"]
        assert result["model"] == ""

    def test_soft_warn_destructive(self):
        from migra.ai_explain import AIGenerator

        patcher, mock_anthropic_mod, mock_client = mock_anthropic()
        try:
            generator = AIGenerator(api_key="sk-ant-test-key")
            result = generator.generate(
                "drop the email column from users",
                schema_context="CREATE TABLE public.users (id integer, email text);",
            )

            assert result["is_destructive"] is True
            assert "WARNING" in result["text"]
            assert "destructive" in result["text"]
            assert "ALTER TABLE" in result["text"] or "DROP" in result["text"]
        finally:
            patcher.stop()

    def test_generate_error_redacts_key(self):
        from migra.ai_explain import AIGenerator

        patcher = patch("anthropic.Anthropic")
        mock_anthropic_class = patcher.start()
        mock_client = MagicMock()
        error_msg = "API error: sk-ant-invalid-key-12345 is invalid"
        mock_client.messages.create.side_effect = RuntimeError(error_msg)
        mock_anthropic_class.return_value = mock_client

        try:
            generator = AIGenerator(api_key="sk-ant-invalid-key-12345")
            with pytest.raises(RuntimeError) as exc_info:
                generator.generate(
                    "add column to users",
                    schema_context="CREATE TABLE public.users (id int);",
                )
            error_text = str(exc_info.value)
            assert "sk-ant-***" in error_text
            assert "sk-ant-invalid-key-12345" not in error_text
        finally:
            patcher.stop()

    def test_empty_description(self):
        from migra.ai_explain import AIGenerator

        generator = AIGenerator(api_key="sk-ant-test-key")
        result = generator.generate("", schema_context="")
        assert "No description provided" in result["text"]
        assert result["model"] == ""


# ---- parse_schema_file_for_tables tests ----


class TestParseSchemaFileForTables:
    def test_parse_create_table(self):
        from migra.ai_explain import parse_schema_file_for_tables

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(
                "CREATE TABLE public.users (\n"
                "    id integer NOT NULL,\n"
                "    email text\n"
                ");\n"
            )
            f.flush()
            fname = f.name

        try:
            result = parse_schema_file_for_tables(fname)
            assert "CREATE TABLE public.users" in result
        finally:
            os.unlink(fname)

    def test_file_not_found(self):
        from migra.ai_explain import parse_schema_file_for_tables

        result = parse_schema_file_for_tables("/nonexistent/file.sql")
        assert result == ""

    def test_no_create_tables(self):
        from migra.ai_explain import parse_schema_file_for_tables

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("-- empty file\n")
            f.flush()
            fname = f.name

        try:
            result = parse_schema_file_for_tables(fname)
            assert result == ""
        finally:
            os.unlink(fname)


# ---- --generate flag integration tests (mocked) ----


class TestGenerateIntegration:
    def test_generate_no_api_key(self):
        """--generate without API key should print error."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("migra.ai_explain.load_config", return_value=None):
                args = parse_args(["--generate", "add column"])
                out, err = io.StringIO(), io.StringIO()
                status = run(args, out=out, err=err)
                assert status == 1
                assert "API key" in err.getvalue()

    def test_generate_missing_package(self):
        """--generate without anthropic package should print error."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("No module named 'anthropic'")
            return original_import(name, *args, **kwargs)

        with patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"}, clear=True
        ):
            with patch("builtins.__import__", side_effect=mock_import):
                args = parse_args(["--generate", "add column"])
                out, err = io.StringIO(), io.StringIO()
                status = run(args, out=out, err=err)
                assert status == 1
                assert "AI extras" in err.getvalue()

    def test_generate_no_description(self):
        """--generate without description should print error."""
        with patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"}, clear=True
        ):
            args = parse_args(["--generate"])
            out, err = io.StringIO(), io.StringIO()
            status = run(args, out=out, err=err)
            assert status == 1
            assert "requires a description" in err.getvalue()

    def test_generate_refuse_bulk_destructive(self):
        """--generate with bulk destructive description prints error."""
        with patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"}, clear=True
        ):
            args = parse_args(["--generate", "drop all tables"])
            out, err = io.StringIO(), io.StringIO()
            status = run(args, out=out, err=err)
            assert status == 1
            assert "Refusing" in err.getvalue()

    def test_generate_basic_with_api_key(self):
        """--generate with API key and description."""
        patcher, mock_anthropic_mod, mock_client = mock_anthropic()
        try:
            with patch.dict(
                os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True
            ):
                args = parse_args(["--generate", "add email column to users"])
                out, err = io.StringIO(), io.StringIO()
                status = run(args, out=out, err=err)
                assert status == 0
                output = out.getvalue()
                assert "Generated Migration" in output
                assert "ALTER TABLE" in output
        finally:
            patcher.stop()

    def test_generate_json_output(self):
        """--generate --output json produces JSON."""
        patcher, mock_anthropic_mod, mock_client = mock_anthropic()
        try:
            with patch.dict(
                os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True
            ):
                args = parse_args(
                    ["--generate", "add email column", "--output", "json"]
                )
                out, err = io.StringIO(), io.StringIO()
                status = run(args, out=out, err=err)
                assert status == 0
                data = json.loads(out.getvalue())
                assert "version" in data
                assert "generated" in data
                assert "sql" in data["generated"]
                assert "description" in data["generated"]
        finally:
            patcher.stop()

    def test_generate_with_advise(self):
        """--generate --advise shows both generation and advisory."""
        patcher, mock_anthropic_mod, mock_client = mock_anthropic()
        try:
            with patch.dict(
                os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True
            ):
                args = parse_args(["--generate", "add email column", "--advise"])
                out, err = io.StringIO(), io.StringIO()
                status = run(args, out=out, err=err)
                assert status == 0
                output = out.getvalue()
                assert "Generated Migration" in output
                assert "Performance Advisory" in output
        finally:
            patcher.stop()

    def test_generate_with_from_file(self):
        """--generate --from-file with schema file."""
        patcher, mock_anthropic_mod, mock_client = mock_anthropic()
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".sql", delete=False
            ) as f:
                f.write("CREATE TABLE public.users (id integer);\n")
                f.flush()
                fname = f.name

            try:
                with patch.dict(
                    os.environ,
                    {"ANTHROPIC_API_KEY": "sk-ant-test"},
                    clear=True,
                ):
                    args = parse_args(
                        ["--generate", "add column to users", "--from-file", fname]
                    )
                    out, err = io.StringIO(), io.StringIO()
                    status = run(args, out=out, err=err)
                    assert status == 0
                    output = out.getvalue()
                    assert "Generated Migration" in output
            finally:
                os.unlink(fname)
        finally:
            patcher.stop()


# ---- Security tests ----


class TestGenerateSecurity:
    def test_api_key_not_in_output(self):
        """API key should never appear in stdout or stderr."""
        patcher, mock_anthropic_mod, mock_client = mock_anthropic()
        try:
            with patch.dict(
                os.environ,
                {"ANTHROPIC_API_KEY": "sk-ant-test-secret-key-12345"},
                clear=True,
            ):
                args = parse_args(["--generate", "add email column"])
                out, err = io.StringIO(), io.StringIO()
                run(args, out=out, err=err)
                output = out.getvalue() + err.getvalue()
                assert "sk-ant-test-secret-key-12345" not in output
        finally:
            patcher.stop()


# ---- extract_relevant_schema tests (mocked DB) ----


class TestExtractRelevantSchema:
    def test_extract_known_table(self):
        from migra.ai_explain import extract_relevant_schema

        # Without a real DB, this should return empty string
        result = extract_relevant_schema("postgres://localhost/test", "users table")
        assert result == ""

    def test_no_description(self):
        from migra.ai_explain import extract_relevant_schema

        result = extract_relevant_schema("postgres://localhost/test", "")
        assert result == ""

    def test_no_connection(self):
        from migra.ai_explain import extract_relevant_schema

        result = extract_relevant_schema("", "users")
        assert result == ""

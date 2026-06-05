from __future__ import unicode_literals
import io
from unittest.mock import MagicMock, patch


def outs():
    return io.StringIO(), io.StringIO()


class TestParseArgsDrift:
    def test_parse_args_minimal(self):
        from migra.command import parse_args

        args = parse_args(
            [
                "--explain-drift",
                "--from-db",
                "postgresql://user:pass@old/db",
                "--to-db",
                "postgresql://user:pass@new/db",
            ]
        )
        assert args.explain_drift
        assert args.from_db == "postgresql://user:pass@old/db"
        assert args.to_db == "postgresql://user:pass@new/db"

    def test_parse_args_missing_from_db(self):
        from migra.command import parse_args

        args = parse_args(["--explain-drift", "--to-db", "postgresql://localhost/db"])
        assert args.explain_drift
        assert args.from_db is None
        assert args.to_db == "postgresql://localhost/db"

    def test_parse_args_missing_to_db(self):
        from migra.command import parse_args

        args = parse_args(["--explain-drift", "--from-db", "postgresql://localhost/db"])
        assert args.explain_drift
        assert args.from_db == "postgresql://localhost/db"
        assert args.to_db is None


class TestExplainDriftErrors:
    def test_missing_args_prints_error(self):
        from migra.command import parse_args, run

        args = parse_args(["--explain-drift"])
        out, err = outs()
        status = run(args, out=out, err=err)
        assert status == 1
        assert "requires both --from-db and --to-db" in err.getvalue()

    def test_missing_from_db_prints_error(self):
        from migra.command import parse_args, run

        args = parse_args(["--explain-drift", "--to-db", "postgresql://localhost/new"])
        out, err = outs()
        status = run(args, out=out, err=err)
        assert status == 1
        assert "requires both --from-db and --to-db" in err.getvalue()

    def test_missing_anthropic_package(self):
        from migra.command import parse_args, run

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("No module named 'anthropic'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            args = parse_args(
                [
                    "--explain-drift",
                    "--from-db",
                    "postgresql://localhost/old",
                    "--to-db",
                    "postgresql://localhost/new",
                ]
            )
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 1
            assert "AI extras" in err.getvalue()

    def test_missing_api_key(self):
        from migra.command import parse_args, run

        with patch.dict("os.environ", {}, clear=True):
            with patch("migra.ai_explain.load_config", return_value=None):
                args = parse_args(
                    [
                        "--explain-drift",
                        "--from-db",
                        "postgresql://localhost/old",
                        "--to-db",
                        "postgresql://localhost/new",
                    ]
                )
                out, err = outs()
                status = run(args, out=out, err=err)
                assert status == 1
                assert "API key" in err.getvalue()

    def test_api_key_flag_used(self):
        from migra.command import parse_args, run

        with patch("schemainspect.get_inspector", return_value=MagicMock()):
            with patch("migra.db_inspector._fetch_table_sizes", return_value={}):
                with patch("anthropic.Anthropic") as mock_anthropic:
                    mock_client = MagicMock()
                    mock_message = MagicMock()
                    mock_message.content = [MagicMock()]
                    mock_message.content[0].text = "Drift analysis result"
                    mock_client.messages.create.return_value = mock_message
                    mock_anthropic.return_value = mock_client

                    args = parse_args(
                        [
                            "--explain-drift",
                            "--from-db",
                            "postgresql://localhost/old",
                            "--to-db",
                            "postgresql://localhost/new",
                            "--api-key",
                            "sk-ant-cli-key",
                        ]
                    )
                    out, err = outs()
                    status = run(args, out=out, err=err)
                    assert status == 0
                    assert "Drift analysis result" in out.getvalue()


class TestExplainDriftSuccess:
    def test_drift_run_with_env_key(self):
        from migra.command import parse_args, run

        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "sk-ant-env-key"},
            clear=True,
        ):
            with patch("schemainspect.get_inspector", return_value=MagicMock()):
                with patch("migra.db_inspector._fetch_table_sizes", return_value={}):
                    with patch("anthropic.Anthropic") as mock_anthropic:
                        mock_client = MagicMock()
                        mock_message = MagicMock()
                        mock_message.content = [MagicMock()]
                        mock_message.content[0].text = (
                            "Schema Drift Analysis: old \u2192 new\n"
                            "No changes detected."
                        )
                        mock_client.messages.create.return_value = mock_message
                        mock_anthropic.return_value = mock_client

                        args = parse_args(
                            [
                                "--explain-drift",
                                "--from-db",
                                "postgresql://localhost/old",
                                "--to-db",
                                "postgresql://localhost/new",
                            ]
                        )
                        out, err = outs()
                        status = run(args, out=out, err=err)
                        assert status == 0
                        output = out.getvalue()
                        assert "Drift Analysis" in output


class TestExplainDriftRuntimeError:
    def test_runtime_error_handled(self):
        from migra.command import parse_args, run

        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "sk-ant-key"},
            clear=True,
        ):
            with patch("schemainspect.get_inspector", return_value=MagicMock()):
                with patch("migra.db_inspector._fetch_table_sizes", return_value={}):
                    with patch("anthropic.Anthropic") as mock_anthropic:
                        mock_client = MagicMock()
                        mock_client.messages.create.side_effect = RuntimeError(
                            "AI failure"
                        )
                        mock_anthropic.return_value = mock_client

                        args = parse_args(
                            [
                                "--explain-drift",
                                "--from-db",
                                "postgresql://localhost/old",
                                "--to-db",
                                "postgresql://localhost/new",
                            ]
                        )
                        out, err = outs()
                        status = run(args, out=out, err=err)
                        assert status == 1
                        assert "AI" in err.getvalue()

from __future__ import unicode_literals

from unittest.mock import MagicMock, patch


class TestCredentialSafety:
    def test_credentials_not_in_error_messages(self):
        """Verify connection errors don't leak credentials."""
        from migra.command import parse_args, run

        import io

        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "sk-ant-test-key"},
            clear=True,
        ):
            with patch("schemainspect.get_inspector") as mock_get:
                mock_get.side_effect = RuntimeError(
                    "could not connect to server: "
                    'FATAL: password authentication failed for user "admin"'
                )

                args = parse_args(
                    [
                        "--explain-drift",
                        "--from-db",
                        "postgresql://admin:supersecret@old.example.com:5432/db",
                        "--to-db",
                        "postgresql://admin:supersecret@new.example.com:5432/db",
                    ]
                )
                out = io.StringIO()
                err = io.StringIO()
                status = run(args, out=out, err=err)
                assert status == 1
                error_output = err.getvalue()
                assert "supersecret" not in error_output

    def test_api_key_not_in_output(self):
        """Verify API key never appears in stdout or stderr on failure."""
        from migra.command import parse_args, run

        import io

        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "sk-ant-test-secret-key-12345"},
            clear=True,
        ):
            with patch("schemainspect.get_inspector") as mock_get:
                mock_get.return_value = MagicMock()

                with patch("migra.db_inspector._fetch_table_sizes", return_value={}):
                    with patch("anthropic.Anthropic") as mock_anthropic:
                        mock_client = MagicMock()
                        mock_client.messages.create.side_effect = RuntimeError(
                            "API error: sk-ant-test-secret-key-12345"
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
                        out = io.StringIO()
                        err = io.StringIO()
                        run(args, out=out, err=err)
                        output = out.getvalue() + err.getvalue()
                        assert "sk-ant-test-secret-key-12345" not in output

    def test_redact_api_key_regex(self):
        from migra.ai_explain import redact_api_key

        keys = [
            "sk-ant-something",
            "sk-ant-a1b2c3d4e5",
            "sk-ant-abc-def-ghi",
        ]
        for key in keys:
            result = redact_api_key("Error: {} is invalid".format(key))
            assert "sk-ant-***" in result
            assert key not in result


class TestConnectionHandling:
    def test_invalid_connection_string(self):
        from migra.command import parse_args, run

        import io

        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "sk-ant-test-key"},
            clear=True,
        ):
            with patch("schemainspect.get_inspector") as mock_get:
                mock_get.side_effect = Exception(
                    'could not translate host name "nonexistent.example.com" '
                    "to address: Name or service not known"
                )

                args = parse_args(
                    [
                        "--explain-drift",
                        "--from-db",
                        "postgresql://localhost/old",
                        "--to-db",
                        "postgresql://nonexistent.example.com/new",
                    ]
                )
                out = io.StringIO()
                err = io.StringIO()
                status = run(args, out=out, err=err)
                assert status == 1
                assert "drift analysis failed" in err.getvalue()

    def test_diff_connection_strings_validated(self):
        """Both --from-db and --to-db must be valid connection strings."""
        from migra.command import parse_args, run

        import io

        args = parse_args(
            [
                "--explain-drift",
                "--from-db",
                "not-a-url",
                "--to-db",
                "also-not-a-url",
            ]
        )
        out = io.StringIO()
        err = io.StringIO()

        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "sk-ant-test-key"},
            clear=True,
        ):
            with patch("schemainspect.get_inspector") as mock_get:
                mock_get.side_effect = Exception("invalid connection")

                status = run(args, out=out, err=err)
                assert status == 1

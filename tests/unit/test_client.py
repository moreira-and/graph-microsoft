from pathlib import Path

import httpx
import pytest
from azure.core.exceptions import ClientAuthenticationError
from fakes import api_error

from sharepoint_files.client import (
    DEFAULT_SCOPE,
    ErrorCategory,
    GraphToolError,
    graph_errors,
    load_config,
    read_env_file,
    translate_error,
)

SECRET = "super-secret-value"
VALID_ENV = {
    "AZURE_TENANT_ID": "tenant",
    "AZURE_CLIENT_ID": "client",
    "AZURE_CLIENT_SECRET": SECRET,
    "SHAREPOINT_SITE_ID": "site-1",
}


def test_load_config_with_required_variables_uses_defaults() -> None:
    config = load_config(VALID_ENV)

    assert config.tenant_id == "tenant"
    assert config.scope == DEFAULT_SCOPE
    assert config.site_id == "site-1"
    assert config.download_dir is None


def test_load_config_reads_optional_variables() -> None:
    env = {
        **VALID_ENV,
        "GRAPH_SCOPE": "custom/.default",
        "SHAREPOINT_HOSTNAME": "contoso.sharepoint.com",
        "SHAREPOINT_SITE_PATH": "/sites/team",
        "DOWNLOAD_DIR": "/tmp/out",
    }

    config = load_config(env)

    assert config.scope == "custom/.default"
    assert config.hostname == "contoso.sharepoint.com"
    assert config.site_path == "/sites/team"
    assert str(config.download_dir) == "/tmp/out"


@pytest.mark.parametrize(
    "site_variables",
    [
        {},
        {"SHAREPOINT_HOSTNAME": "contoso.sharepoint.com"},
        {"SHAREPOINT_SITE_PATH": "/sites/team"},
    ],
)
def test_load_config_requires_site_id_or_hostname_and_path(
    site_variables: dict[str, str],
) -> None:
    env = {
        key: value for key, value in VALID_ENV.items() if key != "SHAREPOINT_SITE_ID"
    }
    env.update(site_variables)

    with pytest.raises(GraphToolError) as error:
        load_config(env)

    assert error.value.category is ErrorCategory.CONFIGURATION
    assert "SHAREPOINT_SITE_ID" in str(error.value)


@pytest.mark.parametrize("name", list(VALID_ENV))
@pytest.mark.parametrize("blank", [False, True])
def test_load_config_reports_only_the_missing_variable_name(
    name: str, blank: bool
) -> None:
    env = dict(VALID_ENV)
    if blank:
        env[name] = "  "
    else:
        del env[name]

    with pytest.raises(GraphToolError) as error:
        load_config(env)

    assert error.value.category is ErrorCategory.CONFIGURATION
    assert name in str(error.value)
    assert SECRET not in str(error.value)


def test_config_repr_hides_secret() -> None:
    assert SECRET not in repr(load_config(VALID_ENV))


def test_read_env_file_parses_pairs_and_ignores_comments(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('# nota\nA=1\nB="dois"\n\nINVALIDA\n', encoding="utf-8")

    assert read_env_file(env_file) == {"A": "1", "B": "dois"}
    assert read_env_file(tmp_path / "ausente.env") == {}


@pytest.mark.parametrize(
    ("status", "category"),
    [
        (401, ErrorCategory.AUTHENTICATION),
        (403, ErrorCategory.PERMISSION),
        (404, ErrorCategory.NOT_FOUND),
        (429, ErrorCategory.THROTTLED),
        (400, ErrorCategory.REQUEST),
        (500, ErrorCategory.SERVER),
        (503, ErrorCategory.SERVER),
    ],
)
def test_translate_error_maps_http_status(status: int, category: ErrorCategory) -> None:
    error = translate_error(api_error(status))

    assert error.category is category
    assert "secret.example" not in str(error)
    assert "token=abc" not in str(error)


def test_translate_error_reports_retry_after_for_throttling() -> None:
    error = translate_error(api_error(429, {"retry-after": "7"}))

    assert "Retry-After: 7s" in str(error)


def test_translate_error_maps_timeout_and_authentication_failures() -> None:
    timeout = translate_error(httpx.ReadTimeout("https://secret.example/?token=abc"))
    auth = translate_error(ClientAuthenticationError("segredo " + SECRET))

    assert timeout.category is ErrorCategory.TIMEOUT
    assert auth.category is ErrorCategory.AUTHENTICATION
    assert SECRET not in str(auth)
    assert "secret.example" not in str(timeout)


def test_graph_errors_translates_and_hides_original_error() -> None:
    with pytest.raises(GraphToolError) as error, graph_errors():
        raise api_error(404)

    assert error.value.category is ErrorCategory.NOT_FOUND
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__


def test_graph_errors_keeps_tool_errors() -> None:
    original = GraphToolError(ErrorCategory.INVALID_PATH, "x")

    with pytest.raises(GraphToolError) as error, graph_errors():
        raise original

    assert error.value is original

"""Configuração, cliente Graph app-only e tradução de erros."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import httpx
from azure.core.exceptions import ClientAuthenticationError
from azure.identity.aio import ClientSecretCredential
from kiota_abstractions.api_error import APIError
from kiota_authentication_azure.azure_identity_authentication_provider import (
    AzureIdentityAuthenticationProvider,
)
from msgraph.graph_request_adapter import GraphRequestAdapter
from msgraph.graph_service_client import GraphServiceClient
from msgraph_core import GraphClientFactory  # type: ignore[import-untyped]

DEFAULT_SCOPE = "https://graph.microsoft.com/.default"
LIST_TIMEOUT = 30.0
DOWNLOAD_TIMEOUT = 120.0
_GRAPH_HOST = "graph.microsoft.com"
REQUIRED_VARIABLES = ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")


class ErrorCategory(StrEnum):
    CONFIGURATION = "configuração"
    AUTHENTICATION = "autenticação"
    PERMISSION = "permissão"
    NOT_FOUND = "não encontrado"
    THROTTLED = "limitação"
    REQUEST = "requisição"
    SERVER = "servidor"
    TIMEOUT = "timeout"
    INVALID_PATH = "caminho inválido"


class GraphToolError(Exception):
    """Erro esperado da ferramenta; a mensagem nunca contém dados sensíveis."""

    def __init__(self, category: ErrorCategory, message: str) -> None:
        super().__init__(message)
        self.category = category


@dataclass(frozen=True)
class Config:
    tenant_id: str
    client_id: str
    client_secret: str = field(repr=False)
    scope: str = DEFAULT_SCOPE
    site_id: str | None = None
    hostname: str | None = None
    site_path: str | None = None
    download_dir: Path | None = None


def load_config(env: Mapping[str, str]) -> Config:
    missing = [name for name in REQUIRED_VARIABLES if not env.get(name, "").strip()]
    if missing:
        raise GraphToolError(
            ErrorCategory.CONFIGURATION,
            f"Variáveis obrigatórias ausentes: {', '.join(missing)}",
        )
    site_id = env.get("SHAREPOINT_SITE_ID", "").strip() or None
    hostname = env.get("SHAREPOINT_HOSTNAME", "").strip() or None
    site_path = env.get("SHAREPOINT_SITE_PATH", "").strip() or None
    if not site_id and not (hostname and site_path):
        raise GraphToolError(
            ErrorCategory.CONFIGURATION,
            "Defina SHAREPOINT_SITE_ID ou SHAREPOINT_HOSTNAME e SHAREPOINT_SITE_PATH",
        )
    download_dir = env.get("DOWNLOAD_DIR", "").strip()
    return Config(
        tenant_id=env["AZURE_TENANT_ID"].strip(),
        client_id=env["AZURE_CLIENT_ID"].strip(),
        client_secret=env["AZURE_CLIENT_SECRET"].strip(),
        scope=env.get("GRAPH_SCOPE", "").strip() or DEFAULT_SCOPE,
        site_id=site_id,
        hostname=hostname,
        site_path=site_path,
        download_dir=Path(download_dir) if download_dir else None,
    )


def read_env_file(path: Path) -> dict[str, str]:
    """Lê pares CHAVE=VALOR de um .env; arquivo ausente resulta em dicionário vazio."""
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, _, value = text.partition("=")
        values[key.strip()] = value.strip().strip("\"'")
    return values


def create_client(config: Config, timeout: float) -> GraphServiceClient:
    credential = ClientSecretCredential(
        config.tenant_id, config.client_id, config.client_secret
    )
    auth_provider = AzureIdentityAuthenticationProvider(
        credential, scopes=[config.scope], allowed_hosts=[_GRAPH_HOST]
    )
    # O middleware padrão do SDK já repete 429 respeitando Retry-After.
    http_client = GraphClientFactory.create_with_default_middleware(
        client=httpx.AsyncClient(timeout=timeout)
    )
    return GraphServiceClient(
        request_adapter=GraphRequestAdapter(auth_provider, http_client)
    )


def _retry_after(headers: Mapping[str, str] | None) -> str | None:
    for key, value in (headers or {}).items():
        if key.lower() == "retry-after":
            return value
    return None


def _translate_status(error: APIError) -> GraphToolError:
    status = error.response_status_code
    if status == 401:
        return GraphToolError(
            ErrorCategory.AUTHENTICATION, "Credenciais recusadas (HTTP 401)"
        )
    if status == 403:
        return GraphToolError(
            ErrorCategory.PERMISSION,
            "Acesso negado (HTTP 403); verifique a concessão Sites.Selected do site",
        )
    if status == 404:
        return GraphToolError(
            ErrorCategory.NOT_FOUND, "Recurso não encontrado (HTTP 404)"
        )
    if status == 429:
        retry_after = _retry_after(error.response_headers)
        suffix = f"; Retry-After: {retry_after}s" if retry_after else ""
        return GraphToolError(
            ErrorCategory.THROTTLED,
            f"Limite de requisições excedido (HTTP 429){suffix}",
        )
    if status is not None and status >= 500:
        return GraphToolError(ErrorCategory.SERVER, f"Erro do servidor (HTTP {status})")
    return GraphToolError(ErrorCategory.REQUEST, f"Requisição recusada (HTTP {status})")


def translate_error(exc: Exception) -> GraphToolError:
    """Converte erros do SDK, do HTTP e da autenticação, sem repassar suas mensagens."""
    if isinstance(exc, APIError):
        return _translate_status(exc)
    if isinstance(exc, ClientAuthenticationError):
        return GraphToolError(
            ErrorCategory.AUTHENTICATION, "Falha de autenticação no Entra ID"
        )
    if isinstance(exc, httpx.TimeoutException):
        return GraphToolError(
            ErrorCategory.TIMEOUT, "Tempo limite da requisição excedido"
        )
    return GraphToolError(
        ErrorCategory.SERVER, "Falha de rede ao acessar o Microsoft Graph"
    )


@contextmanager
def graph_errors() -> Iterator[None]:
    """Traduz erros de chamadas ao Graph; omite o erro original, que pode ter URLs."""
    try:
        yield
    except GraphToolError:
        raise
    except (APIError, ClientAuthenticationError, httpx.HTTPError) as exc:
        raise translate_error(exc) from None

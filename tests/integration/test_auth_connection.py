"""Valida a autenticação app-only sem exigir um site SharePoint."""

import asyncio
import os
import time
from pathlib import Path

import pytest
from azure.identity.aio import ClientSecretCredential

from sharepoint_files.client import DEFAULT_SCOPE, REQUIRED_VARIABLES, read_env_file

pytestmark = pytest.mark.integration

ENV = {**read_env_file(Path(".env")), **os.environ}


def test_app_credentials_can_obtain_graph_token() -> None:
    missing = [name for name in REQUIRED_VARIABLES if not ENV.get(name, "").strip()]
    if missing:
        pytest.skip("Credenciais app-only ausentes no .env local")

    credential = ClientSecretCredential(
        ENV["AZURE_TENANT_ID"], ENV["AZURE_CLIENT_ID"], ENV["AZURE_CLIENT_SECRET"]
    )

    async def request_token() -> None:
        try:
            token = await credential.get_token(
                ENV.get("GRAPH_SCOPE", "").strip() or DEFAULT_SCOPE
            )
            assert token.token
            assert token.expires_on > time.time()
        except Exception as exc:
            pytest.fail(
                f"Falha ao obter token do Microsoft Graph ({type(exc).__name__})",
                pytrace=False,
            )
        finally:
            await credential.close()

    asyncio.run(request_token())

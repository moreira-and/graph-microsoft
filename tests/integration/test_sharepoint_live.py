"""Testes opt-in contra o SharePoint real: `uv run pytest -m integration`."""

import asyncio
import os
from pathlib import Path

import pytest

from sharepoint_files.client import (
    REQUIRED_VARIABLES,
    Config,
    create_client,
    load_config,
    read_env_file,
)
from sharepoint_files.downloads import Status, download_paths
from sharepoint_files.sharepoint import list_items, list_libraries, resolve_site

pytestmark = pytest.mark.integration

ENV = {**read_env_file(Path(".env")), **os.environ}


@pytest.fixture
def config() -> Config:
    missing = [name for name in REQUIRED_VARIABLES if not ENV.get(name)]
    has_site = ENV.get("SHAREPOINT_SITE_ID") or (
        ENV.get("SHAREPOINT_HOSTNAME") and ENV.get("SHAREPOINT_SITE_PATH")
    )
    if missing or not has_site:
        pytest.skip("Credenciais e site de teste ausentes no .env local")
    return load_config(ENV)


def test_resolve_list_and_download_one_file(config: Config, tmp_path: Path) -> None:
    async def scenario() -> None:
        client = create_client(config, timeout=30.0)
        site = await resolve_site(
            client,
            site_id=config.site_id,
            hostname=config.hostname,
            site_path=config.site_path,
        )
        libraries = await list_libraries(client, site.id)
        assert libraries
        items = await list_items(client, libraries[0].id)
        files = [item for item in items if not item.is_folder]
        if not files:
            pytest.skip("A biblioteca de teste não tem arquivos na raiz")
        report = await download_paths(
            client, libraries[0].id, [files[0].path], tmp_path
        )
        assert report.results[0].status is Status.DOWNLOADED

    asyncio.run(scenario())

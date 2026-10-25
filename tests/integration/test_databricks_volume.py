"""Testes opt-in de gravação em volume Unity Catalog no compute Databricks."""

import asyncio
import os
from pathlib import Path, PurePosixPath

import pytest

from sharepoint_files.client import (
    DOWNLOAD_TIMEOUT,
    REQUIRED_VARIABLES,
    create_client,
    load_config,
    read_env_file,
)
from sharepoint_files.downloads import Status, download_volume_paths, volume_root

pytestmark = pytest.mark.integration

ENV = {**read_env_file(Path(".env")), **os.environ}


def test_download_and_overwrite_in_databricks_volume() -> None:
    required = (
        *REQUIRED_VARIABLES,
        "DATABRICKS_TEST_VOLUME",
        "DATABRICKS_TEST_SHAREPOINT_LIBRARY_ID",
        "DATABRICKS_TEST_SHAREPOINT_FILE_PATH",
    )
    missing = [name for name in required if not ENV.get(name, "").strip()]
    if missing:
        pytest.skip("Configuração opt-in do teste Databricks ausente")
    has_site = ENV.get("SHAREPOINT_SITE_ID") or (
        ENV.get("SHAREPOINT_HOSTNAME") and ENV.get("SHAREPOINT_SITE_PATH")
    )
    if not has_site:
        pytest.skip("Site SharePoint de teste ausente no .env local")

    config = load_config(ENV)
    root = volume_root(ENV["DATABRICKS_TEST_VOLUME"])
    source_path = ENV["DATABRICKS_TEST_SHAREPOINT_FILE_PATH"].strip()
    if not source_path or source_path.endswith("/"):
        pytest.skip("O caminho de teste deve identificar um arquivo")
    target = root / PurePosixPath(source_path).name
    if target.exists():
        pytest.skip("O arquivo dedicado do teste já existe no volume")

    created_by_test = False

    async def scenario() -> None:
        nonlocal created_by_test
        client = create_client(config, DOWNLOAD_TIMEOUT)
        try:
            for _ in range(2):
                created_by_test = True
                report = await download_volume_paths(
                    client,
                    ENV["DATABRICKS_TEST_SHAREPOINT_LIBRARY_ID"].strip(),
                    [source_path],
                    root,
                )
                result = report.results[0]
                assert result.status is Status.DOWNLOADED, result.reason
                assert target.is_file()
        finally:
            if created_by_test:
                target.unlink(missing_ok=True)

    asyncio.run(scenario())

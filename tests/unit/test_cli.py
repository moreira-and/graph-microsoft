from pathlib import Path
from typing import Any

import pytest
from azure.core.exceptions import ClientAuthenticationError
from fakes import FakeClient, drive_page, file_item, folder_item, page
from msgraph.generated.models.drive import Drive
from msgraph.generated.models.site import Site as GraphSite

from sharepoint_files.cli import main
from sharepoint_files.client import Config
from sharepoint_files.downloads import DownloadReport

ENV = {
    "AZURE_TENANT_ID": "t",
    "AZURE_CLIENT_ID": "c",
    "AZURE_CLIENT_SECRET": "s",
    "SHAREPOINT_SITE_ID": "site-1",
}


def factory_for(client: FakeClient) -> Any:
    def factory(config: Config, timeout: float) -> Any:
        return client

    return factory


def test_missing_configuration_fails_before_any_call(
    capsys: pytest.CaptureFixture[str],
) -> None:
    client = FakeClient()

    code = main(["site"], env={}, client_factory=factory_for(client))

    assert code == 1
    assert "AZURE_TENANT_ID" in capsys.readouterr().err
    assert client.calls == []


def test_site_uses_configured_site(capsys: pytest.CaptureFixture[str]) -> None:
    client = FakeClient()
    client.site_responses.append(
        GraphSite(id="site-1", display_name="Equipe", web_url="u")
    )

    code = main(["site"], env=ENV, client_factory=factory_for(client))

    assert code == 0
    assert capsys.readouterr().out.strip() == "site-1\tEquipe\tu"


def test_libraries_lists_ids_and_names(capsys: pytest.CaptureFixture[str]) -> None:
    client = FakeClient()
    client.site_responses.append(GraphSite(id="site-1"))
    client.site_drives.append(drive_page([Drive(id="d1", name="Documentos")]))

    code = main(["libraries"], env=ENV, client_factory=factory_for(client))

    assert code == 0
    assert "d1\tDocumentos" in capsys.readouterr().out


def test_ls_prints_kind_size_and_path(capsys: pytest.CaptureFixture[str]) -> None:
    client = FakeClient()
    client.children[""].append(
        page([file_item("1", "a.txt", 7), folder_item("2", "docs")])
    )

    code = main(["ls", "--library", "d1"], env=ENV, client_factory=factory_for(client))

    assert code == 0
    assert capsys.readouterr().out.splitlines() == [
        "arquivo\t7\ta.txt",
        "pasta\t-\tdocs",
    ]


def test_find_reports_when_nothing_matches(capsys: pytest.CaptureFixture[str]) -> None:
    client = FakeClient()
    client.children[""].append(page([file_item("1", "a.txt")]))

    code = main(
        ["find", "--library", "d1", "--name", "zzz"],
        env=ENV,
        client_factory=factory_for(client),
    )

    assert code == 0
    assert capsys.readouterr().out.strip() == "nenhum arquivo encontrado"


def test_find_by_name_prints_matches(capsys: pytest.CaptureFixture[str]) -> None:
    client = FakeClient()
    client.children[""].append(page([file_item("1", "relatorio.pdf", 2)]))

    code = main(
        ["find", "--library", "d1", "--name", "rela"],
        env=ENV,
        client_factory=factory_for(client),
    )

    assert code == 0
    assert "relatorio.pdf" in capsys.readouterr().out


def test_find_requires_name_or_path() -> None:
    with pytest.raises(SystemExit) as error:
        main(
            ["find", "--library", "d1"],
            env=ENV,
            client_factory=factory_for(FakeClient()),
        )

    assert error.value.code == 2


def test_download_volume_uses_configured_volume_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import sharepoint_files.cli as cli

    captured: dict[str, Any] = {}

    async def download_to_volume(
        client: Any, drive_id: str, paths: list[str], dest: Path
    ) -> DownloadReport:
        captured.update(client=client, drive_id=drive_id, paths=paths, dest=dest)
        return DownloadReport(())

    monkeypatch.setattr(cli, "download_volume_paths", download_to_volume)
    client = FakeClient()

    code = main(
        [
            "download",
            "--library",
            "d1",
            "--volume",
            "main.analytics.files",
            "reports/a.csv",
        ],
        env=ENV,
        client_factory=factory_for(client),
    )

    assert code == 0
    assert captured["drive_id"] == "d1"
    assert captured["paths"] == ["reports/a.csv"]
    assert captured["dest"] == Path("/Volumes/main/analytics/files")
    assert "Total: 0 baixado, 0 falha" in capsys.readouterr().out
    assert client.calls == []


def test_download_rejects_invalid_volume_name(
    capsys: pytest.CaptureFixture[str],
) -> None:
    client = FakeClient()

    code = main(
        [
            "download",
            "--library",
            "d1",
            "--volume",
            "main..files",
            "a.csv",
        ],
        env=ENV,
        client_factory=factory_for(client),
    )

    assert code == 1
    assert "catalog.schema.volume" in capsys.readouterr().err
    assert client.calls == []


def test_download_volume_auth_failure_does_not_leak_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import sharepoint_files.cli as cli

    secret = "sentinel-client-secret-value"
    monkeypatch.setattr(cli, "volume_root", lambda _: tmp_path)
    client = FakeClient()
    client.by_path["reports/a.csv"] = ClientAuthenticationError(
        f"invalid_client: {secret}"
    )

    code = main(
        [
            "download",
            "--library",
            "d1",
            "--volume",
            "main.analytics.files",
            "reports/a.csv",
        ],
        env={**ENV, "AZURE_CLIENT_SECRET": secret},
        client_factory=factory_for(client),
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "autenticação" in captured.out
    assert secret not in captured.out + captured.err
    assert list(tmp_path.iterdir()) == []

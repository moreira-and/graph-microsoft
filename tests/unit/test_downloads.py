import asyncio
import os
from pathlib import Path
from typing import Any, cast

import pytest
from fakes import FakeClient, api_error, file_item, folder_item
from msgraph.graph_service_client import GraphServiceClient

from sharepoint_files.client import ErrorCategory, GraphToolError
from sharepoint_files.downloads import (
    MAX_BATCH,
    MAX_FILE_BYTES,
    DownloadRequest,
    Status,
    destination_for,
    download_files,
    download_paths,
    download_volume_paths,
    volume_root,
)

SECRET_URL = "https://secret.example/download?token=abc"


def graph(client: FakeClient) -> GraphServiceClient:
    return cast(GraphServiceClient, client)


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def request(
    item_id: str,
    name: str,
    size: int | None = 3,
    source_path: str | None = None,
) -> DownloadRequest:
    return DownloadRequest("d1", item_id, name, size, source_path)


@pytest.mark.parametrize(
    "name", ["", ".", "..", "../fora.txt", "/etc/passwd", "a/b.txt", "a\\b.txt", "x\0y"]
)
def test_destination_rejects_unsafe_names(tmp_path: Path, name: str) -> None:
    with pytest.raises(GraphToolError) as error:
        destination_for(name, tmp_path)

    assert error.value.category is ErrorCategory.INVALID_PATH


def test_destination_accepts_spaces_and_accents(tmp_path: Path) -> None:
    target = destination_for("relatório final (1).docx", tmp_path)

    assert target.parent == tmp_path.resolve()


@pytest.mark.parametrize(
    "name",
    ["", "catalog.schema", "catalog.schema.volume.extra", "a..c", "a/./c", "../b.c"],
)
def test_volume_root_rejects_invalid_qualified_names(name: str) -> None:
    with pytest.raises(GraphToolError) as error:
        volume_root(name)

    assert error.value.category is ErrorCategory.CONFIGURATION


def test_volume_root_maps_qualified_name_to_databricks_path() -> None:
    assert volume_root("main.analytics.files") == Path("/Volumes/main/analytics/files")


@pytest.mark.parametrize("name", ["a:b.txt", "a*b.txt", "a?b.txt"])
def test_destination_validates_platform_specific_characters(
    tmp_path: Path, name: str
) -> None:
    if os.name == "nt":
        with pytest.raises(GraphToolError) as error:
            destination_for(name, tmp_path)
        assert error.value.category is ErrorCategory.INVALID_PATH
    else:
        assert destination_for(name, tmp_path).name == name


def test_destination_rejects_symlink_pointing_outside(tmp_path: Path) -> None:
    outside = tmp_path / "fora"
    outside.mkdir()
    base = tmp_path / "base"
    base.mkdir()
    (base / "link.txt").symlink_to(outside / "alvo.txt")

    with pytest.raises(GraphToolError):
        destination_for("link.txt", base)


def test_unsafe_name_in_batch_is_a_failure_and_writes_nothing_outside(
    tmp_path: Path,
) -> None:
    base = tmp_path / "base"
    client = FakeClient()
    client.contents["1"] = [b"abc"]

    report = run(download_files(graph(client), [request("1", "../fora.txt")], base))

    assert report.results[0].status is Status.FAILED
    assert not (tmp_path / "fora.txt").exists()
    assert list(base.iterdir()) == []


def test_download_writes_files_sequentially_in_order(tmp_path: Path) -> None:
    client = FakeClient()
    client.contents.update({"1": [b"um"], "2": [b"dois"]})

    report = run(
        download_files(
            graph(client), [request("1", "a.txt"), request("2", "b.txt")], tmp_path
        )
    )

    assert [r.status for r in report.results] == [Status.DOWNLOADED] * 2
    assert (tmp_path / "a.txt").read_bytes() == b"um"
    assert (tmp_path / "b.txt").read_bytes() == b"dois"
    assert [c[2] for c in client.calls if c[0] == "item"] == ["1", "2"]


def test_existing_file_is_skipped_without_overwrite(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"original")
    client = FakeClient()
    client.contents["1"] = [b"novo"]

    report = run(download_files(graph(client), [request("1", "a.txt")], tmp_path))

    assert report.results[0].status is Status.SKIPPED
    assert (tmp_path / "a.txt").read_bytes() == b"original"
    assert [c for c in client.calls if c[0] == "item"] == []


def test_existing_file_is_replaced_with_overwrite(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"original")
    client = FakeClient()
    client.contents["1"] = [b"novo"]

    report = run(
        download_files(graph(client), [request("1", "a.txt")], tmp_path, overwrite=True)
    )

    assert report.results[0].status is Status.DOWNLOADED
    assert (tmp_path / "a.txt").read_bytes() == b"novo"


def test_duplicate_destination_in_batch_follows_the_overwrite_rule(
    tmp_path: Path,
) -> None:
    client = FakeClient()
    client.contents.update({"1": [b"primeiro"], "2": [b"segundo"]})
    batch = [request("1", "a.txt"), request("2", "a.txt")]

    skipped = run(download_files(graph(client), batch, tmp_path))
    assert [r.status for r in skipped.results] == [Status.DOWNLOADED, Status.SKIPPED]
    assert skipped.results[1].reason == "Destino já usado neste lote"
    assert (tmp_path / "a.txt").read_bytes() == b"primeiro"

    client.contents.update({"1": [b"primeiro"], "2": [b"segundo"]})
    replaced = run(download_files(graph(client), batch, tmp_path, overwrite=True))
    assert [r.status for r in replaced.results] == [Status.DOWNLOADED] * 2
    assert (tmp_path / "a.txt").read_bytes() == b"segundo"


def test_partial_failures_keep_completed_files_and_report_each_item(
    tmp_path: Path,
) -> None:
    client = FakeClient()
    client.contents.update({"1": [b"ok"], "2": [api_error(500)], "4": [b"fim"]})
    batch = [
        request("1", "ok.txt"),
        request("2", "erro.txt"),
        request("3", "grande.bin", MAX_FILE_BYTES + 1),
        request("4", "fim.txt"),
        request("5", "sem-tamanho.txt", None),
    ]

    report = run(download_files(graph(client), batch, tmp_path))

    assert [r.status for r in report.results] == [
        Status.DOWNLOADED,
        Status.FAILED,
        Status.FAILED,
        Status.DOWNLOADED,
        Status.FAILED,
    ]
    assert (tmp_path / "ok.txt").read_bytes() == b"ok"
    assert (tmp_path / "fim.txt").read_bytes() == b"fim"
    assert not (tmp_path / "erro.txt").exists()
    assert report.count(Status.FAILED) == 3
    assert "100 MB" in (report.results[2].reason or "")
    assert "informado" in (report.results[4].reason or "")


def test_batch_above_limit_is_refused_before_downloading(tmp_path: Path) -> None:
    client = FakeClient()
    batch = [request(str(i), f"{i}.txt") for i in range(MAX_BATCH + 1)]

    with pytest.raises(GraphToolError):
        run(download_files(graph(client), batch, tmp_path))

    assert client.calls == []


def test_failure_while_writing_leaves_no_final_or_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = FakeClient()
    client.contents["1"] = [b"conteudo"]

    def broken_replace(src: str, dst: Path) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "replace", broken_replace)

    report = run(download_files(graph(client), [request("1", "a.txt")], tmp_path))

    assert report.results[0].status is Status.FAILED
    assert "gravação" in (report.results[0].reason or "")
    assert list(tmp_path.iterdir()) == []


def test_report_and_reasons_never_expose_urls_or_tokens(tmp_path: Path) -> None:
    client = FakeClient()
    client.contents["1"] = [api_error(403)]
    client.contents["2"] = [api_error(500)]

    report = run(
        download_files(
            graph(client), [request("1", "a.txt"), request("2", "b.txt")], tmp_path
        )
    )

    text = " ".join(str(r) for r in report.results)
    assert SECRET_URL not in text
    assert "token" not in text
    assert "secret.example" not in text


def test_download_paths_resolves_and_reports_individual_failures(
    tmp_path: Path,
) -> None:
    client = FakeClient()
    client.by_path["docs/a.txt"] = file_item("1", "a.txt")
    client.by_path["docs"] = folder_item("2", "docs")
    client.contents["1"] = [b"abc"]

    report = run(
        download_paths(
            graph(client), "d1", ["docs/a.txt", "docs", "nao/existe.txt"], tmp_path
        )
    )

    assert [r.status for r in report.results] == [
        Status.DOWNLOADED,
        Status.FAILED,
        Status.FAILED,
    ]
    assert report.results[1].reason == "O item é uma pasta"
    assert report.results[2].reason == "Arquivo não encontrado"
    assert (tmp_path / "a.txt").read_bytes() == b"abc"


def test_download_paths_refuses_large_batches(tmp_path: Path) -> None:
    client = FakeClient()

    with pytest.raises(GraphToolError):
        run(download_paths(graph(client), "d1", ["a"] * (MAX_BATCH + 1), tmp_path))


def test_volume_download_writes_and_overwrites_sequentially(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"old")
    client = FakeClient()
    client.by_path.update(
        {
            "docs/a.txt": file_item("1", "a.txt"),
            "docs/b.txt": file_item("2", "b.txt"),
        }
    )
    client.contents.update({"1": [b"new-a"], "2": [b"new-b"]})

    report = run(
        download_volume_paths(
            graph(client), "d1", ["docs/a.txt", "docs/b.txt"], tmp_path
        )
    )

    assert [result.status for result in report.results] == [
        Status.DOWNLOADED,
        Status.DOWNLOADED,
    ]
    assert (tmp_path / "a.txt").read_bytes() == b"new-a"
    assert (tmp_path / "b.txt").read_bytes() == b"new-b"
    assert client.contents["1"] == []
    assert client.contents["2"] == []


def test_volume_download_keeps_existing_file_when_fetch_fails(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.txt").write_bytes(b"original")
    client = FakeClient()
    client.by_path["docs/a.txt"] = file_item("1", "a.txt")
    client.contents["1"] = [api_error(500)]

    report = run(download_volume_paths(graph(client), "d1", ["docs/a.txt"], tmp_path))

    assert report.results[0].status is Status.FAILED
    assert (tmp_path / "a.txt").read_bytes() == b"original"


def test_volume_download_reports_write_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = FakeClient()
    client.by_path["docs/a.txt"] = file_item("1", "a.txt")
    client.contents["1"] = [b"content"]

    def fail_write(_: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if mode == "wb":
            raise OSError(13, "permission denied")
        return original_open(_, mode, *args, **kwargs)

    original_open = Path.open
    monkeypatch.setattr(Path, "open", fail_write)

    report = run(download_volume_paths(graph(client), "d1", ["docs/a.txt"], tmp_path))

    assert report.results[0].status is Status.FAILED
    assert "gravação" in (report.results[0].reason or "")


@pytest.mark.parametrize("size", [None, MAX_FILE_BYTES + 1])
def test_volume_download_retains_file_size_limit(
    tmp_path: Path, size: int | None
) -> None:
    client = FakeClient()
    client.by_path["docs/a.txt"] = file_item("1", "a.txt", size)
    client.contents["1"] = [b"content"]

    report = run(download_volume_paths(graph(client), "d1", ["docs/a.txt"], tmp_path))

    assert report.results[0].status is Status.FAILED
    assert client.contents["1"] == [b"content"]
    assert not (tmp_path / "a.txt").exists()


def test_volume_download_rejects_duplicate_names_before_writing_non_conflicts_continue(
    tmp_path: Path,
) -> None:
    client = FakeClient()
    client.by_path.update(
        {
            "folder-one/report.csv": file_item("1", "report.csv"),
            "folder-two/report.csv": file_item("2", "report.csv"),
            "other/notes.txt": file_item("3", "notes.txt"),
        }
    )
    client.contents.update({"1": [b"one"], "2": [b"two"], "3": [b"notes"]})

    report = run(
        download_volume_paths(
            graph(client),
            "d1",
            [
                "folder-one/report.csv",
                "folder-two/report.csv",
                "other/notes.txt",
            ],
            tmp_path,
        )
    )

    assert [result.status for result in report.results] == [
        Status.FAILED,
        Status.FAILED,
        Status.DOWNLOADED,
    ]
    assert "folder-one/report.csv" in (report.results[0].reason or "")
    assert "folder-two/report.csv" in (report.results[1].reason or "")
    assert not (tmp_path / "report.csv").exists()
    assert (tmp_path / "notes.txt").read_bytes() == b"notes"
    assert client.contents["1"] == [b"one"]
    assert client.contents["2"] == [b"two"]
    assert client.contents["3"] == []


def test_volume_download_rejects_invalid_destination_and_large_batch(
    tmp_path: Path,
) -> None:
    client = FakeClient()

    with pytest.raises(GraphToolError) as invalid:
        run(download_volume_paths(graph(client), "d1", [], tmp_path / "missing"))
    assert invalid.value.category is ErrorCategory.CONFIGURATION
    assert client.calls == []

    with pytest.raises(GraphToolError):
        run(
            download_volume_paths(
                graph(client),
                "d1",
                [f"{i}.txt" for i in range(MAX_BATCH + 1)],
                tmp_path,
            )
        )
    assert client.calls == []

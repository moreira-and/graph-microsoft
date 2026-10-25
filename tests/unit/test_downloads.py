import asyncio
import os
from pathlib import Path
from typing import Any, cast

import pytest
from fakes import FakeClient, api_error, file_item
from msgraph.graph_service_client import GraphServiceClient

from sharepoint_files.client import ErrorCategory, GraphToolError
from sharepoint_files.downloads import (
    MAX_BATCH,
    MAX_FILE_BYTES,
    DownloadRequest,
    Status,
    destination_for,
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

    def fail_replace(*_: Any, **__: Any) -> None:
        raise OSError(13, "permission denied")

    monkeypatch.setattr(os, "replace", fail_replace)

    report = run(download_volume_paths(graph(client), "d1", ["docs/a.txt"], tmp_path))

    assert report.results[0].status is Status.FAILED
    assert "gravação" in (report.results[0].reason or "")


def test_volume_download_failed_overwrite_keeps_previous_content_without_part(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a.txt").write_bytes(b"original")
    client = FakeClient()
    client.by_path["docs/a.txt"] = file_item("1", "a.txt")
    client.contents["1"] = [b"new-content"]

    def fail_replace(*_: Any, **__: Any) -> None:
        raise OSError(5, "input/output error")

    monkeypatch.setattr(os, "replace", fail_replace)

    report = run(download_volume_paths(graph(client), "d1", ["docs/a.txt"], tmp_path))

    assert report.results[0].status is Status.FAILED
    assert (tmp_path / "a.txt").read_bytes() == b"original"
    assert [path.name for path in tmp_path.iterdir()] == ["a.txt"]


def test_volume_download_writes_only_requested_paths(tmp_path: Path) -> None:
    client = FakeClient()
    client.by_path.update(
        {
            "docs/a.txt": file_item("1", "a.txt"),
            "docs/b.txt": file_item("2", "b.txt"),
        }
    )
    client.contents.update({"1": [b"only-a"], "2": [b"not-requested"]})

    report = run(download_volume_paths(graph(client), "d1", ["docs/a.txt"], tmp_path))

    assert [result.status for result in report.results] == [Status.DOWNLOADED]
    assert [path.name for path in tmp_path.iterdir()] == ["a.txt"]
    assert (tmp_path / "a.txt").read_bytes() == b"only-a"
    assert client.contents["2"] == [b"not-requested"]


def test_volume_download_missing_source_reports_path_and_writes_nothing(
    tmp_path: Path,
) -> None:
    client = FakeClient()

    report = run(download_volume_paths(graph(client), "d1", ["docs/x.txt"], tmp_path))

    assert report.results[0].status is Status.FAILED
    assert "x.txt" in report.results[0].name
    assert list(tmp_path.iterdir()) == []


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


def test_volume_download_partial_failures_keep_completed_files(
    tmp_path: Path,
) -> None:
    client = FakeClient()
    client.by_path.update(
        {
            "docs/ok.txt": file_item("1", "ok.txt"),
            "docs/erro.txt": file_item("2", "erro.txt"),
            "docs/fim.txt": file_item("3", "fim.txt"),
        }
    )
    client.contents.update({"1": [b"ok"], "2": [api_error(500)], "3": [b"fim"]})

    report = run(
        download_volume_paths(
            graph(client),
            "d1",
            ["docs/ok.txt", "docs/erro.txt", "docs/fim.txt"],
            tmp_path,
        )
    )

    assert [r.status for r in report.results] == [
        Status.DOWNLOADED,
        Status.FAILED,
        Status.DOWNLOADED,
    ]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["fim.txt", "ok.txt"]


def test_volume_report_never_exposes_urls_or_tokens(tmp_path: Path) -> None:
    client = FakeClient()
    client.by_path.update(
        {
            "docs/a.txt": file_item("1", "a.txt"),
            "docs/b.txt": file_item("2", "b.txt"),
        }
    )
    client.contents.update({"1": [api_error(403)], "2": [api_error(500)]})

    report = run(
        download_volume_paths(
            graph(client), "d1", ["docs/a.txt", "docs/b.txt"], tmp_path
        )
    )

    text = " ".join(str(r) for r in report.results)
    assert SECRET_URL not in text
    assert "token" not in text
    assert "secret.example" not in text

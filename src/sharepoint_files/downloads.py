"""Download sequencial e seguro de arquivos do SharePoint para um diretório local."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from msgraph.graph_service_client import GraphServiceClient

from sharepoint_files.client import ErrorCategory, GraphToolError, graph_errors
from sharepoint_files.sharepoint import find_items

MAX_BATCH = 20
MAX_FILE_BYTES = 100 * 1024 * 1024
_WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
}


class Status(StrEnum):
    DOWNLOADED = "baixado"
    SKIPPED = "ignorado"
    FAILED = "falha"


@dataclass(frozen=True)
class DownloadRequest:
    drive_id: str
    item_id: str
    name: str
    size: int | None


@dataclass(frozen=True)
class DownloadResult:
    name: str
    status: Status
    path: Path | None = None
    reason: str | None = None


@dataclass(frozen=True)
class DownloadReport:
    results: tuple[DownloadResult, ...]

    def count(self, status: Status) -> int:
        return sum(1 for result in self.results if result.status is status)


def destination_for(name: str, base: Path) -> Path:
    """Resolve o destino de um arquivo e garante que fica dentro de `base`."""
    if not name or name in {".", ".."} or any(c in name for c in "/\\\0"):
        raise GraphToolError(
            ErrorCategory.INVALID_PATH, f"Nome de arquivo inválido: {name!r}"
        )
    if os.name == "nt" and (
        any(ord(char) < 32 or char in '<>:"|?*' for char in name)
        or name.endswith((" ", "."))
        or name.split(".", maxsplit=1)[0].upper() in _WINDOWS_RESERVED_NAMES
    ):
        raise GraphToolError(
            ErrorCategory.INVALID_PATH, f"Nome de arquivo inválido: {name!r}"
        )
    base_resolved = base.resolve()
    target = (base_resolved / name).resolve()
    if target.parent != base_resolved:
        raise GraphToolError(
            ErrorCategory.INVALID_PATH,
            f"Destino fora do diretório configurado: {name!r}",
        )
    return target


def _write_atomic(target: Path, content: bytes) -> None:
    temp = tempfile.NamedTemporaryFile(
        dir=target.parent, prefix=f".{target.name}.", suffix=".part", delete=False
    )
    try:
        with temp:
            temp.write(content)
        os.replace(temp.name, target)
    except BaseException:
        Path(temp.name).unlink(missing_ok=True)
        raise


def _failed(name: str, reason: str) -> DownloadResult:
    return DownloadResult(name, Status.FAILED, reason=reason)


async def _fetch(client: GraphServiceClient, request: DownloadRequest) -> bytes:
    item = client.drives.by_drive_id(request.drive_id).items.by_drive_item_id(
        request.item_id
    )
    with graph_errors():
        content = await item.content.get()
    return content or b""


async def _download_one(
    client: GraphServiceClient,
    request: DownloadRequest,
    dest: Path,
    overwrite: bool,
    seen_targets: set[Path],
) -> DownloadResult:
    try:
        target = destination_for(request.name, dest)
        duplicate = target in seen_targets
        seen_targets.add(target)
        if request.size is None:
            return _failed(request.name, "Tamanho do arquivo não informado")
        if request.size > MAX_FILE_BYTES:
            return _failed(request.name, "Arquivo acima do limite de 100 MB")
        if target.exists() and not overwrite:
            return DownloadResult(
                request.name,
                Status.SKIPPED,
                target,
                "Destino já usado neste lote" if duplicate else "Arquivo já existe",
            )
        _write_atomic(target, await _fetch(client, request))
    except GraphToolError as exc:
        return _failed(request.name, str(exc))
    except OSError as exc:
        return _failed(request.name, f"Erro de gravação: {exc.strerror}")
    return DownloadResult(request.name, Status.DOWNLOADED, target)


def _check_batch_size(size: int) -> None:
    if size > MAX_BATCH:
        raise GraphToolError(
            ErrorCategory.REQUEST, f"O lote excede o limite de {MAX_BATCH} arquivos"
        )


async def download_files(
    client: GraphServiceClient,
    requests: Sequence[DownloadRequest],
    dest: Path,
    overwrite: bool = False,
) -> DownloadReport:
    _check_batch_size(len(requests))
    dest.mkdir(parents=True, exist_ok=True)
    seen_targets: set[Path] = set()
    results = [
        await _download_one(client, request, dest, overwrite, seen_targets)
        for request in requests
    ]
    return DownloadReport(tuple(results))


async def resolve_request(
    client: GraphServiceClient, drive_id: str, path: str
) -> DownloadRequest | DownloadResult:
    """Resolve um caminho da biblioteca; falhas viram resultado individual."""
    try:
        matches = await find_items(client, drive_id, path=path)
    except GraphToolError as exc:
        return _failed(path, str(exc))
    if not matches:
        return _failed(path, "Arquivo não encontrado")
    item = matches[0]
    if item.is_folder:
        return _failed(path, "O item é uma pasta")
    return DownloadRequest(drive_id, item.id, item.name, item.size)


async def resolve_requests(
    client: GraphServiceClient, drive_id: str, paths: Sequence[str]
) -> list[DownloadRequest | DownloadResult]:
    return [await resolve_request(client, drive_id, path) for path in paths]


async def download_paths(
    client: GraphServiceClient,
    drive_id: str,
    paths: Sequence[str],
    dest: Path,
    overwrite: bool = False,
) -> DownloadReport:
    """Resolve e baixa cada caminho em ordem, sem perder os resultados anteriores."""
    _check_batch_size(len(paths))
    dest.mkdir(parents=True, exist_ok=True)
    results: list[DownloadResult] = []
    seen_targets: set[Path] = set()
    for resolved in await resolve_requests(client, drive_id, paths):
        if isinstance(resolved, DownloadResult):
            results.append(resolved)
        else:
            results.append(
                await _download_one(client, resolved, dest, overwrite, seen_targets)
            )
    return DownloadReport(tuple(results))

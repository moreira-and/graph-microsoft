"""Operações somente leitura de SharePoint: site, bibliotecas, itens e localização."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from msgraph.graph_service_client import GraphServiceClient

from sharepoint_files.client import ErrorCategory, GraphToolError, graph_errors


@dataclass(frozen=True)
class Site:
    id: str
    name: str
    web_url: str


@dataclass(frozen=True)
class Library:
    id: str
    name: str


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    path: str
    is_folder: bool
    size: int | None


def _base_url(client: GraphServiceClient) -> str:
    return client.request_adapter.base_url.rstrip("/")


def _site_key(site_id: str | None, hostname: str | None, site_path: str | None) -> str:
    if site_id:
        return site_id
    if hostname and site_path:
        return f"{hostname}:/{site_path.strip('/')}"
    raise GraphToolError(
        ErrorCategory.CONFIGURATION,
        "Informe o ID do site ou hostname e caminho do site",
    )


async def _collect(builder: Any) -> list[Any]:
    """Lê todas as páginas de uma coleção seguindo @odata.nextLink."""
    entries: list[Any] = []
    with graph_errors():
        page = await builder.get()
        while page is not None:
            entries.extend(page.value or [])
            if not page.odata_next_link:
                break
            page = await builder.with_url(page.odata_next_link).get()
    return entries


async def resolve_site(
    client: GraphServiceClient,
    *,
    site_id: str | None = None,
    hostname: str | None = None,
    site_path: str | None = None,
) -> Site:
    key = _site_key(site_id, hostname, site_path)
    builder = client.sites.by_site_id(key)
    if not site_id:
        # O SDK codifica ":" e "/" no segmento; a URL de caminho vai sem codificação.
        builder = builder.with_url(f"{_base_url(client)}/sites/{key}")
    with graph_errors():
        site = await builder.get()
    if site is None or not site.id:
        raise GraphToolError(ErrorCategory.NOT_FOUND, "Site não encontrado")
    return Site(site.id, site.display_name or site.name or "", site.web_url or "")


async def list_libraries(client: GraphServiceClient, site_id: str) -> list[Library]:
    drives = await _collect(client.sites.by_site_id(site_id).drives)
    return [Library(drive.id or "", drive.name or "") for drive in drives]


def _children_builder(client: GraphServiceClient, drive_id: str, folder: str) -> Any:
    root = client.drives.by_drive_id(drive_id).items.by_drive_item_id("root")
    if not folder:
        return root.children
    url = f"{_base_url(client)}/drives/{drive_id}/root:/{quote(folder)}:/children"
    return root.children.with_url(url)


def _to_item(entry: Any, folder: str) -> Item:
    is_folder = entry.folder is not None
    name = entry.name or ""
    return Item(
        id=entry.id or "",
        name=name,
        path=f"{folder}/{name}".strip("/"),
        is_folder=is_folder,
        size=None if is_folder else entry.size,
    )


async def list_items(
    client: GraphServiceClient, drive_id: str, folder: str = ""
) -> list[Item]:
    folder = folder.strip("/")
    entries = await _collect(_children_builder(client, drive_id, folder))
    return [_to_item(entry, folder) for entry in entries]


async def _find_by_path(
    client: GraphServiceClient, drive_id: str, path: str
) -> list[Item]:
    url = f"{_base_url(client)}/drives/{drive_id}/root:/{quote(path)}"
    builder = (
        client.drives.by_drive_id(drive_id).items.by_drive_item_id("root").with_url(url)
    )
    try:
        with graph_errors():
            entry = await builder.get()
    except GraphToolError as exc:
        if exc.category is ErrorCategory.NOT_FOUND:
            return []
        raise
    if entry is None:
        return []
    parent, _, _ = path.rpartition("/")
    return [_to_item(entry, parent)]


async def _find_by_name(
    client: GraphServiceClient, drive_id: str, folder: str, name: str
) -> list[Item]:
    needle = name.lower()
    matches: list[Item] = []
    pending = [folder]
    while pending:
        for item in await list_items(client, drive_id, pending.pop(0)):
            if item.is_folder:
                pending.append(item.path)
            elif needle in item.name.lower():
                matches.append(item)
    return matches


async def find_items(
    client: GraphServiceClient,
    drive_id: str,
    folder: str = "",
    *,
    name: str | None = None,
    path: str | None = None,
) -> list[Item]:
    """Localiza por nome (arquivos, recursivo) ou por caminho relativo à pasta.

    Percorre só a pasta informada; não usa os endpoints de busca do Graph.
    """
    if (name is None) == (path is None):
        raise ValueError("Informe exatamente um entre name e path")
    folder = folder.strip("/")
    if name is not None:
        return await _find_by_name(client, drive_id, folder, name)
    assert path is not None
    return await _find_by_path(
        client, drive_id, f"{folder}/{path.strip('/')}".strip("/")
    )

"""Cliente Graph falso para testes: sem rede, usa os modelos reais do SDK."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from urllib.parse import unquote

from kiota_abstractions.api_error import APIError
from msgraph.generated.models.drive import Drive
from msgraph.generated.models.drive_collection_response import DriveCollectionResponse
from msgraph.generated.models.drive_item import DriveItem
from msgraph.generated.models.drive_item_collection_response import (
    DriveItemCollectionResponse,
)
from msgraph.generated.models.file import File
from msgraph.generated.models.folder import Folder


def api_error(status: int, headers: dict[str, str] | None = None) -> APIError:
    return APIError(
        "erro com https://secret.example/download?token=abc", status, headers
    )


def file_item(item_id: str, name: str, size: int | None = 3) -> DriveItem:
    return DriveItem(id=item_id, name=name, size=size, file=File())


def folder_item(item_id: str, name: str) -> DriveItem:
    return DriveItem(id=item_id, name=name, folder=Folder())


def page(
    items: list[DriveItem], next_link: str | None = None
) -> DriveItemCollectionResponse:
    return DriveItemCollectionResponse(value=items, odata_next_link=next_link)


def drive_page(
    drives: list[Drive], next_link: str | None = None
) -> DriveCollectionResponse:
    return DriveCollectionResponse(value=drives, odata_next_link=next_link)


class Endpoint:
    """Fila de respostas; `with_url` devolve o mesmo endpoint (próxima página)."""

    def __init__(self, client: FakeClient, responses: list[Any]) -> None:
        self.client = client
        self.responses = responses

    async def get(self) -> Any:
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def with_url(self, url: str) -> Endpoint:
        self.client.calls.append(("with_url", url))
        return self


class FolderChildren(Endpoint):
    def with_url(self, url: str) -> Endpoint:
        self.client.calls.append(("with_url", url))
        if "root:/" not in url:
            return self
        folder = unquote(url.split("root:/", 1)[1].removesuffix(":/children"))
        return Endpoint(self.client, self.client.children[folder])


class ItemBuilder:
    def __init__(self, client: FakeClient, drive_id: str, item_id: str) -> None:
        self.client = client
        self.children = FolderChildren(client, client.children[""])
        self.content = Endpoint(client, client.contents.setdefault(item_id, []))
        self.item_id = item_id
        client.calls.append(("item", drive_id, item_id))

    def with_url(self, url: str) -> Endpoint:
        self.client.calls.append(("with_url", url))
        key = unquote(url.split("root:/", 1)[1])
        return Endpoint(self.client, [self.client.by_path.get(key, api_error(404))])


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.site_responses: list[Any] = []
        self.site_drives: list[Any] = []
        self.children: dict[str, list[Any]] = {"": []}
        self.by_path: dict[str, Any] = {}
        self.contents: dict[str, list[Any]] = {}
        self.request_adapter = SimpleNamespace(
            base_url="https://graph.microsoft.com/v1.0/"
        )
        self.sites = SimpleNamespace(by_site_id=self._by_site_id)
        self.drives = SimpleNamespace(by_drive_id=self._by_drive_id)

    def _by_site_id(self, key: str) -> Any:
        self.calls.append(("site", key))
        return SimpleNamespace(
            get=Endpoint(self, self.site_responses).get,
            with_url=Endpoint(self, self.site_responses).with_url,
            drives=Endpoint(self, self.site_drives),
        )

    def _by_drive_id(self, drive_id: str) -> Any:
        return SimpleNamespace(
            items=SimpleNamespace(
                by_drive_item_id=lambda item_id: ItemBuilder(self, drive_id, item_id)
            )
        )

import asyncio
from typing import Any, cast

import pytest
from fakes import FakeClient, api_error, drive_page, file_item, folder_item, page
from msgraph.generated.models.drive import Drive
from msgraph.generated.models.site import Site as GraphSite
from msgraph.graph_service_client import GraphServiceClient

from sharepoint_files.client import ErrorCategory, GraphToolError
from sharepoint_files.sharepoint import (
    find_items,
    list_items,
    list_libraries,
    resolve_site,
)

NEXT = "https://graph.microsoft.com/v1.0/next"


def graph(client: FakeClient) -> GraphServiceClient:
    return cast(GraphServiceClient, client)


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def test_resolve_site_by_id() -> None:
    client = FakeClient()
    client.site_responses.append(GraphSite(id="s1", display_name="Equipe", web_url="u"))

    site = run(resolve_site(graph(client), site_id="s1"))

    assert (site.id, site.name, site.web_url) == ("s1", "Equipe", "u")
    assert ("site", "s1") in client.calls


def test_resolve_site_by_hostname_and_path_uses_unencoded_url() -> None:
    client = FakeClient()
    client.site_responses.append(GraphSite(id="s1", display_name="Equipe"))

    site = run(
        resolve_site(
            graph(client), hostname="contoso.sharepoint.com", site_path="/sites/team/"
        )
    )

    assert site.id == "s1"
    assert (
        "with_url",
        "https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com:/sites/team",
    ) in client.calls


def test_resolve_site_requires_an_identifier_before_any_call() -> None:
    client = FakeClient()

    with pytest.raises(GraphToolError) as error:
        run(resolve_site(graph(client), hostname="contoso.sharepoint.com"))

    assert error.value.category is ErrorCategory.CONFIGURATION
    assert client.calls == []


def test_resolve_site_translates_not_found() -> None:
    client = FakeClient()
    client.site_responses.append(api_error(404))

    with pytest.raises(GraphToolError) as error:
        run(resolve_site(graph(client), site_id="s1"))

    assert error.value.category is ErrorCategory.NOT_FOUND


def test_list_libraries_follows_all_pages() -> None:
    client = FakeClient()
    client.site_drives.extend(
        [
            drive_page([Drive(id="d1", name="A")], NEXT + "1"),
            drive_page([Drive(id="d2", name="B")], NEXT + "2"),
            drive_page([Drive(id="d3", name="C")]),
        ]
    )

    libraries = run(list_libraries(graph(client), "s1"))

    assert [(lib.id, lib.name) for lib in libraries] == [
        ("d1", "A"),
        ("d2", "B"),
        ("d3", "C"),
    ]
    assert [c[1] for c in client.calls if c[0] == "with_url"] == [
        NEXT + "1",
        NEXT + "2",
    ]


def test_list_items_follows_pages_and_maps_files_and_folders() -> None:
    client = FakeClient()
    client.children[""].extend(
        [
            page([file_item("1", "a.txt", 10)], NEXT + "1"),
            page([folder_item("2", "docs")], NEXT + "2"),
            page([file_item("3", "b.txt", 5)]),
        ]
    )

    items = run(list_items(graph(client), "d1"))

    assert [(i.name, i.path, i.is_folder, i.size) for i in items] == [
        ("a.txt", "a.txt", False, 10),
        ("docs", "docs", True, None),
        ("b.txt", "b.txt", False, 5),
    ]


def test_list_items_in_subfolder_builds_relative_paths() -> None:
    client = FakeClient()
    client.children["docs/2024"] = [page([file_item("1", "r.pdf")])]

    items = run(list_items(graph(client), "d1", "/docs/2024/"))

    assert [i.path for i in items] == ["docs/2024/r.pdf"]
    assert any("root:/docs/2024:/children" in c[1] for c in client.calls)


def test_list_items_empty_folder_returns_empty_list() -> None:
    client = FakeClient()
    client.children[""].append(page([]))

    assert run(list_items(graph(client), "d1")) == []


def test_list_items_propagates_translated_errors() -> None:
    client = FakeClient()
    client.children[""].append(api_error(403))

    with pytest.raises(GraphToolError) as error:
        run(list_items(graph(client), "d1"))

    assert error.value.category is ErrorCategory.PERMISSION


def test_find_by_name_is_case_insensitive_and_recursive_over_files() -> None:
    client = FakeClient()
    client.children[""].append(
        page(
            [
                file_item("1", "Relatorio.docx"),
                folder_item("2", "sub"),
                file_item("3", "x.txt"),
            ]
        )
    )
    client.children["sub"] = [page([file_item("4", "relatorio-final.pdf")])]

    items = run(find_items(graph(client), "d1", name="RELATORIO"))

    assert [i.path for i in items] == ["Relatorio.docx", "sub/relatorio-final.pdf"]


def test_find_by_name_without_matches_returns_empty() -> None:
    client = FakeClient()
    client.children[""].append(page([file_item("1", "a.txt")]))

    assert run(find_items(graph(client), "d1", name="zzz")) == []


def test_find_by_path_returns_the_item_relative_to_the_folder() -> None:
    client = FakeClient()
    client.by_path["docs/a/b.pdf"] = file_item("9", "b.pdf")

    items = run(find_items(graph(client), "d1", "docs", path="a/b.pdf"))

    assert [(i.id, i.path) for i in items] == [("9", "docs/a/b.pdf")]


def test_find_by_path_missing_returns_empty() -> None:
    client = FakeClient()

    assert run(find_items(graph(client), "d1", path="nao/existe.txt")) == []


def test_find_by_path_other_errors_are_raised() -> None:
    client = FakeClient()
    client.by_path["x.txt"] = api_error(500)

    with pytest.raises(GraphToolError) as error:
        run(find_items(graph(client), "d1", path="x.txt"))

    assert error.value.category is ErrorCategory.SERVER


def test_find_requires_exactly_one_criterion() -> None:
    client = FakeClient()

    with pytest.raises(ValueError):
        run(find_items(graph(client), "d1"))
    with pytest.raises(ValueError):
        run(find_items(graph(client), "d1", name="a", path="b"))


def test_operations_never_use_graph_search_endpoints() -> None:
    client = FakeClient()
    client.site_responses.append(GraphSite(id="s1"))
    client.children[""].append(page([file_item("1", "a.txt")]))

    run(resolve_site(graph(client), site_id="s1"))
    run(find_items(graph(client), "d1", name="a"))

    urls = " ".join(c[1] for c in client.calls if len(c) > 1)
    assert "search" not in urls

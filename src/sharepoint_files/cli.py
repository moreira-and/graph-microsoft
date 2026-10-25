"""Interface de linha de comando mínima."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Callable, Coroutine, Mapping, Sequence
from pathlib import Path
from typing import Any

from msgraph.graph_service_client import GraphServiceClient

from sharepoint_files.client import (
    DOWNLOAD_TIMEOUT,
    LIST_TIMEOUT,
    Config,
    ErrorCategory,
    GraphToolError,
    create_client,
    load_config,
    read_env_file,
)
from sharepoint_files.downloads import Status, download_paths
from sharepoint_files.sharepoint import (
    Item,
    find_items,
    list_items,
    list_libraries,
    resolve_site,
)

ClientFactory = Callable[[Config, float], GraphServiceClient]
Handler = Callable[
    [argparse.Namespace, Config, GraphServiceClient], Coroutine[Any, Any, int]
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sharepoint_files")
    parser.add_argument("--env-file", default=".env", help="arquivo .env local")
    commands = parser.add_subparsers(dest="command", required=True)

    for name in ("site", "libraries"):
        command = commands.add_parser(name)
        command.add_argument("--site-id")
        command.add_argument("--hostname")
        command.add_argument("--site-path")

    for name in ("ls", "find", "download"):
        command = commands.add_parser(name)
        command.add_argument("--library", required=True, help="ID da biblioteca")
        if name != "download":
            command.add_argument("--folder", default="")
    find = commands.choices["find"]
    target = find.add_mutually_exclusive_group(required=True)
    target.add_argument("--name")
    target.add_argument("--path")

    download = commands.choices["download"]
    download.add_argument("--dest", type=Path)
    download.add_argument("--overwrite", action="store_true")
    download.add_argument("paths", nargs="+", metavar="CAMINHO")
    return parser


def _site_arguments(args: argparse.Namespace, config: Config) -> dict[str, str | None]:
    if args.site_id or args.hostname or args.site_path:
        return {
            "site_id": args.site_id,
            "hostname": args.hostname,
            "site_path": args.site_path,
        }
    return {
        "site_id": config.site_id,
        "hostname": config.hostname,
        "site_path": config.site_path,
    }


def _format_item(item: Item) -> str:
    kind = "pasta" if item.is_folder else "arquivo"
    size = "-" if item.size is None else str(item.size)
    return f"{kind}\t{size}\t{item.path}"


async def _site(
    args: argparse.Namespace, config: Config, client: GraphServiceClient
) -> int:
    site = await resolve_site(client, **_site_arguments(args, config))
    print(f"{site.id}\t{site.name}\t{site.web_url}")
    return 0


async def _libraries(
    args: argparse.Namespace, config: Config, client: GraphServiceClient
) -> int:
    site = await resolve_site(client, **_site_arguments(args, config))
    for library in await list_libraries(client, site.id):
        print(f"{library.id}\t{library.name}")
    return 0


async def _ls(
    args: argparse.Namespace, config: Config, client: GraphServiceClient
) -> int:
    for item in await list_items(client, args.library, args.folder):
        print(_format_item(item))
    return 0


async def _find(
    args: argparse.Namespace, config: Config, client: GraphServiceClient
) -> int:
    items = await find_items(
        client, args.library, args.folder, name=args.name, path=args.path
    )
    if not items:
        print("nenhum arquivo encontrado")
    for item in items:
        print(_format_item(item))
    return 0


async def _download(
    args: argparse.Namespace, config: Config, client: GraphServiceClient
) -> int:
    dest = args.dest or config.download_dir
    if dest is None:
        raise GraphToolError(
            ErrorCategory.CONFIGURATION, "Informe --dest ou defina DOWNLOAD_DIR"
        )
    report = await download_paths(
        client, args.library, args.paths, dest, args.overwrite
    )
    for result in report.results:
        print(f"{result.status}\t{result.name}\t{result.reason or result.path or ''}")
    counts = ", ".join(f"{report.count(s)} {s}" for s in Status)
    print(f"Total: {counts}")
    return 1 if report.count(Status.FAILED) else 0


_HANDLERS: dict[str, Handler] = {
    "site": _site,
    "libraries": _libraries,
    "ls": _ls,
    "find": _find,
    "download": _download,
}


def main(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    client_factory: ClientFactory = create_client,
) -> int:
    args = _build_parser().parse_args(argv)
    timeout = DOWNLOAD_TIMEOUT if args.command == "download" else LIST_TIMEOUT
    try:
        if env is None:
            env = {**read_env_file(Path(args.env_file)), **os.environ}
        config = load_config(env)
        client = client_factory(config, timeout)
        return asyncio.run(_HANDLERS[args.command](args, config, client))
    except GraphToolError as exc:
        print(f"Erro ({exc.category}): {exc}", file=sys.stderr)
        return 1

import tomllib
from pathlib import Path


def test_sharepoint_console_entry_point_targets_cli_main() -> None:
    project_file = Path(__file__).parents[2] / "pyproject.toml"
    pyproject = tomllib.loads(project_file.read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["sharepoint-files"] == (
        "sharepoint_files.cli:main"
    )


def test_existing_module_entry_point_remains_available() -> None:
    project_file = Path(__file__).parents[2] / "src/sharepoint_files/__main__.py"

    assert "sharepoint_files.cli import main" in project_file.read_text(
        encoding="utf-8"
    )

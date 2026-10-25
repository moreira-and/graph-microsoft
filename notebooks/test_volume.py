# Databricks notebook source
from datetime import UTC, datetime
from pathlib import Path

databricks_utils = globals()["dbutils"]
databricks_utils.widgets.text(
    "volume", "", "Unity Catalog volume (catalog.schema.volume)"
)
volume_name = databricks_utils.widgets.get("volume").strip()
volume_parts = volume_name.split(".")

if len(volume_parts) != 3 or any(
    not part or part in {".", ".."} or "/" in part or "\\" in part
    for part in volume_parts
):
    raise ValueError("Informe o volume no formato catalog.schema.volume")

volume_path = Path("/Volumes", *volume_parts)
test_file = volume_path / "test.txt"
expected_content = f"current_time={datetime.now(UTC).isoformat(timespec='seconds')}\n"

test_file.write_text(expected_content, encoding="utf-8")
actual_content = test_file.read_text(encoding="utf-8")

if actual_content != expected_content:
    raise RuntimeError(f"Falha ao validar a leitura de {test_file}")

print(f"Escrita e leitura confirmadas: {test_file}")

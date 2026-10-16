from pathlib import Path
import json

from .constants import DATA_DIR_NAME, METADATA_FILE

DATA_DIR = Path(DATA_DIR_NAME)
DATA_DIR.mkdir(exist_ok=True)

def load_metadata(filepath: str = METADATA_FILE) -> dict:
    path = Path(filepath)
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_metadata(filepath: str, data: dict) -> None:
    path = Path(filepath)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_data(table_name: str) -> list:
    file_path = DATA_DIR / f"{table_name}.json"
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_data(table_name: str, rows: list) -> None:
    file_path = DATA_DIR / f"{table_name}.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

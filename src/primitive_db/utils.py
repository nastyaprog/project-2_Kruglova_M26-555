import json
from pathlib import Path


METADATA_FILE = "db_meta.json"

def load_metadata(filepath: str = METADATA_FILE) -> dict:
    """Загружает метаданные из JSON. 
    Если файла нет — возвращает пустой словарь."""
    path = Path(filepath)
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        # Если файл есть, но битый — считаем, что метаданных нет
        return {}

def save_metadata(filepath: str, data: dict) -> None:
    """Сохраняет метаданные в JSON-файл."""
    path = Path(filepath)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
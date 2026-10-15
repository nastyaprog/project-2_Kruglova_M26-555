import json
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

METADATA_FILE = "db_meta.json"

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

def load_data(filename: str) -> list:
    path = DATA_DIR / f"{filename}.json"
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (IOError, json.JSONDecodeError):
        print(f"❗️ Ошибка загрузки {path}.")
        return []

    # Восстанавливаем типы только если файл был сохранён со строковыми значениями.
    # Но делаем это аккуратно: только если тип в метаданных известен и значение — строка.
    metadata = load_metadata(METADATA_FILE)
    if filename in metadata and isinstance(data, list):
        columns = metadata[filename]
        for row in data:
            for col_def in columns[1:]:  # пропускаем ID
                col_name = col_def["name"]
                col_type = col_def["type"].lower()
                raw_value = row.get(col_name)

                if not isinstance(raw_value, str):
                    continue

                # Убираем внешние кавычки, если они есть (на случай, если мы сохраняли как строки)
                while raw_value.startswith(('"', "'")) and raw_value.endswith(('"', "'")):
                    raw_value = raw_value[1:-1].strip()

                try:
                    if col_type == "int":
                        row[col_name] = int(raw_value)
                    elif col_type == "bool":
                        row[col_name] = raw_value.lower().startswith("t")
                    else:
                        row[col_name] = raw_value
                except ValueError:
                    # Если не удалось преобразовать — оставляем как есть
                    pass

    return data

def save_data(filename: str, data: list) -> None:
    path = DATA_DIR / f"{filename}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

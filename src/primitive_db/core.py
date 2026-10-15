from typing import Any, Dict, List, Optional
from pathlib import Path


SUPPORTED_TYPES = {"int", "str", "bool"}

def parse_columns(columns_raw: List[str]) -> List[Dict[str, str]]:
    """
    Преобразует сырые аргументы командной строки в список определений столбцов.
    """
    parsed = []
    # Цикл по каждому сырому определению столбца 'name:type'
    for col in columns_raw:
        if ":" not in col:
            raise ValueError(f"Некорректный формат столбца: {col}")
        name, typ = col.split(":", 1)
        name = name.strip()
        typ = typ.strip().lower()
        if not name:
            raise ValueError("Имя столбца не может быть пустым.")
        if typ not in SUPPORTED_TYPES:
            raise ValueError(f"Неподдерживаемый тип: {typ}")
        parsed.append({"name": name, "type": typ})
    return parsed

def create_table(metadata: Dict[str, Any], table_name: str, columns_raw: List[str]) -> Dict[str, Any]:
    """Создает новую таблицу в метаданных, добавляя ID:int."""
    if table_name in metadata:
        raise ValueError(f'Ошибка: Таблица "{table_name}" уже существует.')
    columns = parse_columns(columns_raw)
    columns.insert(0, {"name": "ID", "type": "int"})
    metadata[table_name] = columns
    return metadata

DATA_DIR = Path("data")

def drop_table(metadata, table_name):
    if table_name not in metadata:
        raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')
    
    # Удаляем файл данных, если он есть
    data_file = DATA_DIR / f"{table_name}.json"
    if data_file.exists():
        data_file.unlink()  # это удаляет файл
    
    # Удаляем описание таблицы из метаданных
    del metadata[table_name]
    return metadata

def list_tables(metadata: Dict[str, Any]) -> List[str]:
    """Возвращает список имен всех существующих таблиц."""
    return list(metadata.keys())

# --- CRUD операции ---

def get_all(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Возвращает все записи таблицы."""
    return records

def create(records: List[Dict[str, Any]], new_record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Добавляет новую запись, генерируя автоинкремент ID."""
    next_id = (max((r["ID"] for r in records), default=0)) + 1
    new_record["ID"] = next_id
    records.append(new_record)
    return records

def update(records: List[Dict[str, Any]], record_id: int, updates: Dict[str, Any]) -> bool:
    """Обновляет запись по ID. Возвращает успех операции."""
    # Цикл по записям для поиска нужного ID
    for r in records:
        if r.get("ID") == record_id:
            r.update(updates)
            return True
    return False

def delete(records: List[Dict[str, Any]], record_id: int) -> bool:
    """Удаляет запись по ID. Возвращает успех операции."""
    initial_len = len(records)
    # Пересоздаем список, исключая запись с заданным ID (фильтрация)
    records[:] = [r for r in records if r.get("ID") != record_id]
    return len(records) < initial_len

def filter_records(records: List[Dict[str, Any]], condition: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Фильтрует записи по словарю условий (аналог WHERE)."""
    if not condition:
        return records
    # Цикл-генератор списка: оставляет только те строки, где все условия совпадают
    return [r for r in records if all(r.get(k) == v for k, v in condition.items())]
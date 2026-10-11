from typing import Any, Dict, List


SUPPORTED_TYPES = {"int", "str", "bool"}

def parse_columns(columns_raw: List[str]) -> List[Dict[str, str]]:
    """
    Преобразует список строк 'name:type' в список словарей [{name, type}].
    Проверяет, что тип поддерживается.
    """
    parsed = []
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
    """Создаёт таблицу: добавляет ID:int в начало, проверяет существование и типы."""
    if table_name in metadata:
        raise ValueError(f'Ошибка: Таблица "{table_name}" уже существует.')

    columns = parse_columns(columns_raw)

    # Добавляем ID:int в самое начало
    columns.insert(0, {"name": "ID", "type": "int"})

    metadata[table_name] = columns
    return metadata

def drop_table(metadata: Dict[str, Any], table_name: str) -> Dict[str, Any]:
    """Удаляет таблицу, если она существует."""
    if table_name not in metadata:
        raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')
    del metadata[table_name]
    return metadata

def list_tables(metadata: Dict[str, Any]) -> List[str]:
    """Возвращает список имён таблиц."""
    return list(metadata.keys())

import re
from typing import Any, Dict, List, Optional

from .constants import METADATA_FILE
from .decorators import confirm_action, handle_db_errors, log_time
from .parser import (  # <-- важно добавить parse_set_clause
    parse_columns,
    parse_set_clause,
)
from .utils import DATA_DIR, load_data, load_metadata, save_data, save_metadata

# --- Вспомогательные функции для типов ---

def convert_value_to_type(value: str, target_type: str) -> Any:
    """Преобразует строковое значение в нужный тип данных."""
    target_type = target_type.lower()
    
    # Если это уже не строка (например, передали число при тестировании),
    # возвращаем как есть
    if not isinstance(value, str):
        return value

    # Убираем кавычки, если они есть вокруг значения
    while value.startswith(('"', "'")) and value.endswith(('"', "'")):
        value = value[1:-1].strip()

    if target_type == "int":
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Не удалось преобразовать '{value}' к типу int")
    elif target_type == "bool":
        lower = value.lower()
        if lower in ("true", "1", "yes"):
            return True
        elif lower in ("false", "0", "no"):
            return False
        else:
            raise ValueError(f"Не удалось преобразовать '{value}' к типу bool")
    elif target_type == "float":
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"Не удалось преобразовать '{value}' к типу float")
    else:
        # Для str и остальных просто возвращаем строку
        return value


# --- Логика управления таблицами (Core Logic) ---

@handle_db_errors
@log_time
def execute_update(
    table_name: str, 
    set_part: str, 
    where_part: str | None = None,
) -> int:
    """
    Обновляет записи в таблице по условию WHERE.
    Если where_part пуст — обновляет все строки.
    Возвращает число обновлённых строк.
    """
    data = load_data(table_name) or []
    if not data:
        return 0

    # Парсим часть SET: col=value, col2=value2
    updates = parse_set_clause(set_part)

    # Если WHERE нет — обновляем все строки
    if not where_part or not where_part.strip():
        updated_count = 0
        for row in data:
            changed = False
            for col, new_val in updates.items():
                if col in row and row[col] != new_val:
                    row[col] = new_val
                    changed = True
            if changed:
                updated_count += 1
        save_data(table_name, data)
        return updated_count

    # Иначе парсим WHERE через тот же механизм, что и в execute_delete/execute_select
    where_part = where_part.strip()
    pattern = r'^\s*([A-Za-z_][\w]*)\s*(>=|<=|<>|!=|=|>|<)\s*(.*)\s*$'
    match = re.match(pattern, where_part)
    if not match:
        raise ValueError(f"Некорректный формат условия WHERE: {where_part}")

    col_name = match.group(1).strip()
    operator = match.group(2).strip()
    raw_val_str = match.group(3).strip()

    value = raw_val_str
    if len(value) >= 2 and (
        (value.startswith('"') and value.endswith('"')) or
        (value.startswith("'") and value.endswith("'"))
    ):
        value = value[1:-1]

    lower_val = value.lower()
    if lower_val in ("true", "1", "yes"):
        target_value = True
    elif lower_val in ("false", "0", "no"):
        target_value = False
    elif re.fullmatch(r"-?\d+", value):
        target_value = int(value)
    elif re.fullmatch(r"-?\d+\.\d+", value):
        target_value = float(value)
    else:
        target_value = value

    updated_count = 0
    for row in data:
        cell = row.get(col_name)
        if cell is None:
            continue

        match_row = False
        if operator == "=":
            match_row = (cell == target_value)
        elif operator == ">":
            match_row = (cell > target_value)
        elif operator == "<":
            match_row = (cell < target_value)
        elif operator == ">=":
            match_row = (cell >= target_value)
        elif operator == "<=":
            match_row = (cell <= target_value)
        elif operator in ("!=", "<>"):
            match_row = (cell != target_value)

        if not match_row:
            continue

        changed = False
        for col, new_val in updates.items():
            if col in row and row[col] != new_val:
                row[col] = new_val
                changed = True
        if changed:
            updated_count += 1

    save_data(table_name, data)
    return updated_count

@handle_db_errors
def execute_create_table(
    metadata: dict, 
    table_name: str, 
    columns_raw: List[str],
) -> dict:
    """
    Создает таблицу. 
    ВАЖНО: Парсинг колонок (columns_raw -> список словарей) происходит в parser.py.
    Здесь остается только бизнес-логика.
    """
    if not isinstance(table_name, str):
        raise ValueError(
            f"Имя таблицы должно быть строкой, а не {type(table_name).__name__}"
            )

    if table_name in metadata:
        raise ValueError(f'Ошибка: таблица "{table_name}" уже существует.')

    # 1. Парсим колонки через внешнюю функцию (из parser.py)
    # Это превращает ["name:str", "age:int"] в [{"name": "name", "type": "str"}, ...]
    try:
        parsed_columns = parse_columns(columns_raw)
    except ValueError as e:
        raise e

    # 2. Добавляем ID:int в начало списка колонок (автоматически)
    final_columns = [{"name": "ID", "type": "int"}] + parsed_columns

    # 3. Сохраняем структуру в метаданные
    metadata[table_name] = final_columns
    
    return metadata


@confirm_action("удаление таблицы")
@handle_db_errors
@log_time
def execute_drop_table(table_name: str) -> bool:
    metadata = load_metadata(METADATA_FILE)
    
    if table_name not in metadata:
        raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')
    
    data_file = DATA_DIR / f"{table_name}.json"
    if data_file.exists():
        data_file.unlink()
    
    del metadata[table_name]
    save_metadata(METADATA_FILE, metadata)
    return True


def list_tables(metadata: Dict[str, Any]) -> List[str]:
    return list(metadata.keys())


def get_info(metadata: Dict[str, Any], table_name: str) -> Optional[Dict[str, Any]]:
    if table_name not in metadata:
        return None
    
    cols = metadata[table_name]
    data = load_data(table_name) or []
    
    return {
        "name": table_name,
        "columns": cols,
        "count": len(data)
    }


# --- CRUD операции (базовые функции работы со списком) ---

def create_record(
        records: List[Dict[str, Any]], 
        new_record: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
    next_id = (max((r["ID"] for r in records), default=0)) + 1
    new_record["ID"] = next_id
    records.append(new_record)
    return records


@handle_db_errors
@log_time
def execute_insert(
    table_name: str, 
    values_raw: List[Any], 
    columns: List[Dict[str, str]],
) -> int:
    """Вставляет одну запись. values_raw - это список значений без ID."""
    # Ожидаем количество значений равное количеству колонок минус ID
    expected_count = len(columns) - 1
    
    if len(values_raw) != expected_count:
        raise ValueError(
            f"Ожидается {expected_count} значений, передано {len(values_raw)}."
            )

    converted_values = []
    # Проходим по колонкам начиная со второй (пропуская ID)
    for i, val_raw in enumerate(values_raw):
        col_def = columns[i + 1]
        converted = convert_value_to_type(val_raw, col_def["type"])
        converted_values.append(converted)

    data = load_data(table_name) or []
    record = {"ID": None} # ID присвоится внутри create_record
    
    for (col_def, val) in zip(columns[1:], converted_values):
        record[col_def["name"]] = val

    data = create_record(data, record)
    save_data(table_name, data)
    
    # Возвращаем ID последней добавленной записи
    return data[-1]["ID"]


def filter_records(
    records: List[Dict[str, Any]], 
    condition: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Фильтрует список записей по условию WHERE."""
    if not condition:
        return records
    
    col = condition["column"]
    op = condition["operator"]
    val = condition["value"]
    
    result = []
    for r in records:
        cell = r.get(col)
        if cell is None:
            continue
            
        match = False
        if op == "=":
            match = (cell == val)
        elif op == ">":
            match = (cell > val)
        elif op == "<":
            match = (cell < val)
        elif op == ">=":
            match = (cell >= val)
        elif op == "<=":
            match = (cell <= val)
        elif op in ("!=", "<>"):
            match = (cell != val)
            
        if match:
            result.append(r)
            
    return result


@handle_db_errors
@log_time
def execute_select(table_name: str, where_part: Optional[str]) -> List[Dict[str, Any]]:
    data = load_data(table_name) or []

    if not where_part:
        return data

    # Парсинг условия WHERE (можно вынести в parser.py в будущем, 
    #но пока оставляю здесь для SELECT)
    pattern = r'^\s*([A-Za-z_][\w]*)\s*(>=|<=|<>|!=|=|>|<)\s*(.*)\s*$'
    match = re.match(pattern, where_part.strip())
    if not match:
        raise ValueError(f"Некорректный формат условия WHERE: {where_part}")

    col_name = match.group(1).strip()
    operator = match.group(2).strip()
    raw_val_str = match.group(3).strip()

    value = raw_val_str
    # Удаляем кавычки
    if len(value) >= 2 and ((value.startswith('"') and value.endswith('"')) or
                            (value.startswith("'") and value.endswith("'"))):
        value = value[1:-1]

    lower_val = value.lower()
    if lower_val in ("true", "1", "yes"):
        target_value = True
    elif lower_val in ("false", "0", "no"):
        target_value = False
    elif re.fullmatch(r"-?\d+", value):
        target_value = int(value)
    elif re.fullmatch(r"-?\d+\.\d+", value):
        target_value = float(value)
    else:
        target_value = value

    condition = {
        "column": col_name,
        "operator": operator,
        "value": target_value
    }

    return filter_records(data, condition)


@handle_db_errors
@log_time
def execute_info(table_name: str) -> dict:
    """
    Возвращает информацию о структуре таблицы: имя, колонки, типы, число строк.
    """
    metadata = load_metadata()
    if metadata is None:
        raise ValueError("Метаданные не загружены.")

    if table_name not in metadata:
        raise ValueError(f"Таблица '{table_name}' не найдена.")
    # список колонок: [{"name": "...", "type": "..."}, ...]
    table_meta = metadata[table_name]
    total_rows = len(load_data(table_name) or [])

    return {
        "name": table_name,
        "columns": table_meta,
        "total_rows": total_rows,
    }

@handle_db_errors
@log_time
def execute_delete(table_name: str, where_part: str) -> int:
    """
    Удаляет записи по условию.
    Если where_part пуст или None — удаляет все записи в таблице.
    Возвращает количество удалённых записей.
    """
    data = load_data(table_name) or []
    if not data:
        return 0

    # Если условие пустое — удаляем всё
    if not where_part or not where_part.strip():
        initial_len = len(data)
        save_data(table_name, [])
        return initial_len

    where_part = where_part.strip()
    pattern = r'^\s*([A-Za-z_][\w]*)\s*(>=|<=|<>|!=|=|>|<)\s*(.*)\s*$'
    match = re.match(pattern, where_part)
    if not match:
        raise ValueError(f"Некорректный формат условия WHERE: {where_part}")

    col_name = match.group(1).strip()
    operator = match.group(2).strip()
    raw_val_str = match.group(3).strip()

    value = raw_val_str
    if len(value) >= 2 and ((value.startswith('"') and value.endswith('"')) or
                            (value.startswith("'") and value.endswith("'"))):
        value = value[1:-1]

    lower_val = value.lower()
    if lower_val in ("true", "1", "yes"):
        target_value = True
    elif lower_val in ("false", "0", "no"):
        target_value = False
    elif re.fullmatch(r"-?\d+", value):
        target_value = int(value)
    elif re.fullmatch(r"-?\d+\.\d+", value):
        target_value = float(value)
    else:
        target_value = value

    ids_to_remove = set()
    for row in data:
        cell = row.get(col_name)
        if cell is None:
            continue

        match_row = False
        if operator == "=":
            match_row = (cell == target_value)
        elif operator == ">":
            match_row = (cell > target_value)
        elif operator == "<":
            match_row = (cell < target_value)
        elif operator == ">=":
            match_row = (cell >= target_value)
        elif operator == "<=":
            match_row = (cell <= target_value)
        elif operator in ("!=", "<>"):
            match_row = (cell != target_value)

        if match_row:
            ids_to_remove.add(row["ID"])

    if not ids_to_remove:
        return 0

    new_data = [row for row in data if row["ID"] not in ids_to_remove]
    save_data(table_name, new_data)
    return len(ids_to_remove)

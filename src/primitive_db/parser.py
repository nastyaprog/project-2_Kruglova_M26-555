from typing import List, Dict, Any 
from .constants import SUPPORTED_TYPES


def parse_where_clause(where_str: str) -> Dict[str, Any]:
    """
    Парсит простое условие WHERE и возвращает словарь {column: value}.
    
    Поддерживаемые операторы: =, >, <, >=, <=, !=, <>
    НО: оператор НЕ включается в возвращаемый dict. Он нужен только для execute_*,
    поэтому здесь мы возвращаем только {column: value}, а оператор можно вернуть отдельно,
    если ты решишь усложнить логику позже.

    Примеры:
      "name = 'Alice'"   -> {"name": "Alice"}
      "age > 25"         -> {"age": 25}
      "is_active != true"-> {"is_active": False}

    Для условий с операторами, отличными от '=', логика фильтрации должна быть
    реализована в execute_select / execute_delete.
    """
    where_str = where_str.strip()

    # Паттерн: колонка, оператор, значение
    pattern = r'^\s*([A-Za-z_][\w]*)\s*(>=|<=|<>|!=|=|>|<)\s*(.*)\s*$'
    match = re.match(pattern, where_str)

    if not match:
        raise ValueError(f"Некорректный формат условия WHERE: {where_str}")

    col_name = match.group(1).strip()
    operator = match.group(2).strip()  # Сохраняем оператор, если понадобится
    raw_val_str = match.group(3).strip()

    value = raw_val_str

    # Удаляем внешние кавычки, если они есть (одинарные или двойные)
    if len(value) >= 2 and ((value.startswith('"') and value.endswith('"')) or
                            (value.startswith("'") and value.endswith("'"))):
        value = value[1:-1]

    lower_val = value.lower()

    # Булевы значения
    if lower_val in ("true", "1", "yes"):
        return {col_name: True}
    elif lower_val in ("false", "0", "no"):
        return {col_name: False}

    # Числа
    if re.fullmatch(r"-?\d+", value):
        return {col_name: int(value)}
    elif re.fullmatch(r"-?\d+\.\d+", value):
        return {col_name: float(value)}

    # Иначе — строка
    return {col_name: value}


def parse_set_clause(set_str: str) -> Dict[str, Any]:
    set_parts = [p.strip() for p in set_str.split(",") if p.strip()]
    result = {}
    for part in set_parts:
        if "=" not in part:
            raise ValueError(f"Некорректное выражение в SET: {part}")
        key, val_str = part.split("=", 1)
        key = key.strip()
        val_str = val_str.strip()

        if (val_str.startswith('"') and val_str.endswith('"')) or (val_str.startswith("'") and val_str.endswith("'")):
            val = val_str[1:-1]
        else:
            val = val_str

        if val.lower() == "true":
            val = True
        elif val.lower() == "false":
            val = False
        elif re.fullmatch(r"-?\d+", val):
            val = int(val)
        result[key] = val
    return result

def parse_columns(columns_raw: List[str]) -> List[Dict[str, str]]:
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
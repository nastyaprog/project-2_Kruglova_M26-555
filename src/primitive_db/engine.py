import shlex
import re
from typing import Any, Dict, List
from prettytable import PrettyTable

from .utils import load_metadata, save_metadata
from .core import (
    execute_create_table,  # <--- ВАЖНО: заменили create_table на execute_create_table
    execute_insert,
    execute_select,
    execute_drop_table,
    execute_delete,
    list_tables,
)

METADATA_FILE = "db_meta.json"

def parse_values(values_str: str) -> List[Any]:
    """Парсит строку значений внутри скобок, учитывая кавычки."""
    values_str = values_str.strip()
    if values_str.startswith("(") and values_str.endswith(")"):
        values_str = values_str[1:-1].strip()

    result = [] 
    in_quote = False
    current = ""
    quote_char = None
    i = 0

    while i < len(values_str):
        ch = values_str[i]
        if ch in ('"', "'") and not in_quote:
            in_quote = True
            quote_char = ch
            i += 1
            continue
        elif ch == quote_char and in_quote:
            in_quote = False
            result.append(current)
            current = ""
            i += 1
            while i < len(values_str) and values_str[i].isspace():
                i += 1
            continue

        if not in_quote and ch == ",":
            if current.strip():
                result.append(current.strip())
            current = ""
            i += 1
            continue

        current += ch
        i += 1

    if current.strip():
        result.append(current.strip())

    return result

def format_table(rows: List[Dict[str, Any]], columns: List[Dict[str, str]]) -> str:
    """Форматирует список словарей в красивую таблицу PrettyTable."""
    if not rows:
        return "Нет записей."
    
    t = PrettyTable()
    field_names = [c["name"] for c in columns]
    t.field_names = field_names
    
    for row in rows:
        row_values = []
        for col in columns:
            val = row.get(col["name"])
            # Для булевых значений делаем красивый вывод
            if isinstance(val, bool):
                row_values.append("true" if val else "false")
            else:
                row_values.append(val)
        t.add_row(row_values)
    
    return str(t)

def run():
    print("Примитивная база данных. Введите 'help' для списка команд.")

    while True:
        try:
            command_line = input(">>> Введите команду: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход из программы.")
            break

        if not command_line:
            continue

        lower_cmd = command_line.lower()

        # --- ГЛАВНЫЙ IF: create_table ---
        if lower_cmd.startswith("create_table"):
            parts = shlex.split(command_line)
            if len(parts) < 3:
                print("Ошибка: недостаточно аргументов. Формат: create_table <name> <col:type> ...")
                continue
            
            table_name = parts[1]
            columns_raw = parts[2:]  # ["name:str", "age:int"]
            
            try:
                metadata = load_metadata(METADATA_FILE)
                # <--- ЗДЕСЬ ГЛАВНОЕ ИЗМЕНЕНИЕ: вызываем execute_create_table из core
                # Она сама вызовет parse_columns из parser.py
                metadata = execute_create_table(metadata, table_name, columns_raw)
                save_metadata(METADATA_FILE, metadata)
                
                cols_str = ", ".join(f"{c['name']}:{c['type']}" for c in metadata[table_name])
                print(f'Таблица "{table_name}" успешно создана со столбцами: {cols_str}')
            except ValueError as e:
                print(f"Ошибка: {e}")
            except Exception as e:
                print(f"Неожиданная ошибка: {e}")

        # --- drop_table ---
        elif lower_cmd.startswith("drop_table"):
            parts = shlex.split(command_line)
            if len(parts) < 2:
                print("Ошибка: укажите имя таблицы. Формат: drop_table <name>")
                continue
            table_name = parts[1]
            try:
                execute_drop_table(table_name)
                print(f'Таблица "{table_name}" успешно удалена.')
            except ValueError as e:
                print(f"Ошибка: {e}")

        # --- list_tables ---
        elif lower_cmd == "list_tables":
            metadata = load_metadata(METADATA_FILE)
            tables = list_tables(metadata)
            if not tables:
                print("- (таблиц нет)")
            else:
                for t in tables:
                    print(f"- {t}")

        # --- insert into ---
        elif lower_cmd.startswith("insert into"):
            match = re.match(r'insert\s+into\s+(\w+)\s+values\s*(.*)', command_line, re.IGNORECASE)
            if not match:
                print("Ошибка синтаксиса INSERT. Пример: insert into users values ('Alice', 25)")
                continue
            
            table_name, values_part = match.groups()
            try:
                metadata = load_metadata(METADATA_FILE)
                if table_name not in metadata:
                    raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')
                columns = metadata[table_name]
                values_raw = parse_values(values_part)
                new_id = execute_insert(table_name, values_raw, columns)
                print(f'Запись с ID={new_id} успешно добавлена в таблицу "{table_name}".')
            except ValueError as e:
                print(f"Ошибка: {e}")

        # --- select from ---
        elif lower_cmd.startswith("select from"):
            match = re.match(r'^\s*select\s+from\s+(\w+)(?:\s+where\s+(.+))?\s*$', command_line, re.IGNORECASE)
            if not match:
                print("Ошибка синтаксиса SELECT. Пример: select from users [where name = Alice]")
                continue

            table_name = match.group(1)
            where_part = match.group(2)

            try:
                metadata = load_metadata(METADATA_FILE)
                if table_name not in metadata:
                    raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')
                columns = metadata[table_name]
                rows = execute_select(table_name, where_part)
                print(format_table(rows, columns))
            except ValueError as e:
                print(f"Ошибка: {e}")

        # --- delete from ---
        elif lower_cmd.startswith("delete from"):
            match = re.match(r'^\s*delete\s+from\s+(\w+)\s+where\s+(.+)\s*$', command_line, re.IGNORECASE)
            if not match:
                print("Ошибка синтаксиса DELETE. Пример: delete from users where name = Alice")
                continue

            table_name, where_part = match.groups()

            try:
                deleted_count = execute_delete(table_name, where_part)
                if deleted_count > 0:
                    print(f"Удалено записей: {deleted_count}")
                else:
                    print("Записей, удовлетворяющих условию WHERE, не найдено.")
            except ValueError as e:
                print(f"Ошибка: {e}")

        # --- help ---
        elif lower_cmd == "help":
            print("Доступные команды:")
            print("  create_table <name> <col:type>...  - создать таблицу")
            print("  drop_table <name>                    - удалить таблицу")
            print("  list_tables                          - список таблиц")
            print("  insert into <name> values (...)     - вставить запись")
            print("  select from <name> [where ...]      - выбрать записи")
            print("  delete from <name> where ...        - удалить записи")
            print("  exit                                - выход")

        elif lower_cmd == "exit":
            print("Выход из программы.")
            break

        else:
            print("Неизвестная команда. Введите 'help' для справки.")

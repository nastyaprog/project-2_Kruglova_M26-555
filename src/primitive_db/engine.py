import re
import shlex
from typing import Any, List, Dict
from prettytable import PrettyTable

from .utils import load_metadata, save_metadata, DATA_DIR
from .core import (
    execute_create_table,
    execute_insert,
    execute_select,
    execute_drop_table,
    execute_delete,
    list_tables,
)
from .constants import METADATA_FILE


def parse_values(values_str: str) -> List[Any]:
    """
    Парсит строку значений в скобках: ('Alice', 25, true)
    Возвращает список строк/значений, сохраняя кавычки для дальнейшей конвертации.
    """
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
            # Конец строки
            in_quote = False
            result.append(current)
            current = ""
            i += 1
            # Пропускаем пробелы и запятую после закрывающей кавычки
            while i < len(values_str) and values_str[i].isspace():
                i += 1
            if i < len(values_str) and values_str[i] == ",":
                i += 1
                while i < len(values_str) and values_str[i].isspace():
                    i += 1
            continue

        if not in_quote and ch == ",":
            if current.strip():
                result.append(current.strip())
            current = ""
            i += 1
            while i < len(values_str) and values_str[i].isspace():
                i += 1
            continue

        current += ch
        i += 1

    if current.strip():
        result.append(current.strip())

    return result


def format_table(rows: List[Dict[str, Any]], columns: List[Dict[str, str]]) -> str:
    if not rows:
        return "Нет записей."

    t = PrettyTable()
    field_names = [c["name"] for c in columns]
    t.field_names = field_names

    for row in rows:
        row_values = []
        for col in columns:
            val = row.get(col["name"])
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

        parts = command_line.split(maxsplit=1)
        cmd = parts[0].lower()
        args_raw = parts[1] if len(parts) > 1 else ""

        # help
        if cmd == "help":
            print(
                "Доступные команды:\n"
                "  create_table <name> <col:type> ...\n"
                "  drop_table <name>\n"
                "  list_tables\n"
                "  insert into <name> values (...)\n"
                "  select from <name> [where ...]\n"
                "  delete from <name> where ...\n"
                "  help\n"
                "  exit"
            )
            continue

        # exit
        if cmd == "exit":
            print("Выход из программы.")
            break

        metadata = load_metadata(METADATA_FILE)
        if metadata is None:
            metadata = {}

        # create_table
        if cmd == "create_table":
            args = args_raw.split()
            if len(args) < 2:
                print("Ошибка: недостаточно аргументов. Пример: create_table users name:str age:int")
                continue
            table_name = args[0]
            columns_raw = args[1:]
            try:
                new_metadata = execute_create_table(metadata, table_name, columns_raw)
                save_metadata(METADATA_FILE, new_metadata)
                cols = new_metadata[table_name]
                col_names_types = ", ".join(f"{c['name']}:{c['type']}" for c in cols)
                print(f'Таблица "{table_name}" успешно создана со столбцами: {col_names_types}')
            except Exception as e:
                print(f"Ошибка: {e}")
            continue

        # drop_table
        if cmd == "drop_table":
            args = args_raw.split()
            if not args:
                print("Ошибка: укажите имя таблицы. Пример: drop_table users")
                continue
            table_name = args[0]
            try:
                success = execute_drop_table(table_name)
                if success:
                    print(f'Таблица "{table_name}" успешно удалена.')
            except Exception as e:
                print(f"Ошибка: {e}")
            continue

        # list_tables
        if cmd == "list_tables":
            tables = list_tables(metadata)
            if not tables:
                print("Таблиц нет.")
            else:
                for t in tables:
                    print("-", t)
            continue

        # insert
        if cmd == "insert":
            # Формат: insert into users values ('Alice', 25, true)
            match = re.match(r"^into\s+(\S+)\s+values\s+(.*)$", args_raw, re.IGNORECASE)
            if not match:
                print('Ошибка: неверный формат INSERT. Пример: insert into users values (\'Alice\', 25, true)')
                continue
            table_name, values_str = match.groups()

            if table_name not in metadata:
                print(f'Ошибка: таблица "{table_name}" не найдена.')
                continue

            values_raw = parse_values(values_str)
            cols = metadata[table_name]

            try:
                record_id = execute_insert(table_name, values_raw, cols)
                print(f"Запись с ID={record_id} успешно добавлена в таблицу \"{table_name}\".")
            except Exception as e:
                print(f"Ошибка: {e}")
            continue

        # select
        if cmd == "select":
            match = re.match(r"^from\s+(\S+)(?:\s+where\s+(.+))?$", args_raw, re.IGNORECASE)
            if not match:
                print('Ошибка: неверный формат SELECT. Пример: select from users [where age > 20]')
                continue
            table_name, where_part = match.groups()

            if table_name not in metadata:
                print(f'Ошибка: таблица "{table_name}" не найдена.')
                continue

            try:
                rows = execute_select(table_name, where_part)
                cols = metadata[table_name]
                print(format_table(rows, cols))
            except Exception as e:
                print(f"Ошибка: {e}")
            continue

        # delete
        if cmd == "delete":
            match = re.match(r"^from\s+(\S+)\s+where\s+(.+)$", args_raw, re.IGNORECASE)
            if not match:
                print('Ошибка: неверный формат DELETE. Пример: delete from users where name = \'Alice\'')
                continue
            table_name, where_part = match.groups()

            if table_name not in metadata:
                print(f'Ошибка: таблица "{table_name}" не найдена.')
                continue

            try:
                deleted_count = execute_delete(table_name, where_part)
                print(f"Удалено записей: {deleted_count}")
            except Exception as e:
                print(f"Ошибка: {e}")
            continue

        print("Неизвестная команда. Введите 'help' для справки.")

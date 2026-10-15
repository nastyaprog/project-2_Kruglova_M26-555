import shlex
import re
from typing import Any, Dict, List, Optional
from prettytable import PrettyTable

from .utils import load_metadata, save_metadata, load_data, save_data
from .core import (
    create_table, drop_table, list_tables,
    get_all, create, update, delete, filter_records
)

METADATA_FILE = "db_meta.json"

def parse_values(values_str: str) -> List[Any]:
    """
    Парсит строку значений внутри VALUES(...). Поддерживает только явные типы.
    Строки должны быть всегда в кавычках ("..."), чтобы избежать конфликтов.
    Числа и bool распознаются автоматически через json.dump.
    """
    values_str = values_str.strip()
    if values_str.startswith("(") and values_str.endswith(")"):
        values_str = values_str[1:-1].strip()  # Убираем внешние скобки

    result = []
    in_quote = False
    current = ""
    quote_char = None
    i = 0

    while i < len(values_str):  # Цикл посимвольного разбора
        ch = values_str[i]

        # Обработка строковых литералов
        if ch in ('"', "'") and not in_quote:
            in_quote = True
            quote_char = ch
            i += 1  # Пропускаем открывающую кавычку
            continue
        elif ch == quote_char and in_quote:
            in_quote = False
            val = current  # Не делаем здесь никаких преобразований типа! Оставляем raw-string.
            result.append(val)
            current = ""
            i += 1  # Переходим за закрывающую кавычку
            # Пропускаем все пробелы/запятые до следующего символа
            while i < len(values_str) and values_str[i].isspace():
                i += 1
            continue

        # Если мы вне кавычек и встретили запятую,
        # значит, закончилась числовая константа или true/false/null.
        if not in_quote and ch == ",":
            val = current.strip()
            if val:
                result.append(val)  # Опять же, оставляем как есть.
            current = ""
            i += 1
            continue

        current += ch
        i += 1

    # Добавляем последнее значение
    val = current.strip()
    if val:
        result.append(val)

    return result

def parse_single_value(val: str) -> Any:
    """Преобразует одно строковое значение к типу int, bool или str."""
    # СРЕЗАЕМ КАВЫЧКИ ПЕРЕД ВСЕМИ ДРУГИМИ ОПЕРАЦИЯМИ

    while val.startswith(('"', "'")) and val.endswith(('"', "'")):
        val = val[1:-1].strip()

    # Теперь у нас гарантированно нет внешних кавычек.
    if not val:
        return None  # Или пустую строку "", если нужно

    val_lower = val.lower()
    if val_lower == "true":
        return True
    elif val_lower == "false":
        return False

    try:
        # Пробуем привести к целому числу
        return int(val)
    except ValueError:
        pass  # Если не число, идём дальше по логике string/bool.
    
    # Здесь можно добавить float(), но у вас в схеме только int
    # try:
    #     return float(val)
    # except ValueError:
    #     pass

    return val  # Возвращаем очищенную от кавычек строку

def parse_where_clause(where_str: str) -> Dict[str, Any]:
    """
    Парсит условие WHERE вида: age = 28 или name = "Sergei".
    """
    where_str = where_str.strip()
    match = re.match(r'^\s*(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|(\S+))\s*$', where_str)
    if not match:
        raise ValueError(f"Некорректный формат условия WHERE: {where_str}")
    col = match.group(1)
    value = match.group(2) or match.group(3) or match.group(4)

    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif re.fullmatch(r"-?\d+", value):
        value = int(value)
    return {col: value}

def parse_set_clause(set_str: str) -> Dict[str, Any]:
    """
    Парсит SET часть команды UPDATE: age = 29, name = "Alex".
    """
    set_parts = [p.strip() for p in set_str.split(",") if p.strip()]
    result = {}
    # Цикл по каждой паре 'ключ=значение' в SET
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

def format_table(rows: List[Dict[str, Any]], columns: List[Dict[str, str]]) -> str:
    """
    Форматирует список записей в красивую ASCII-таблицу.
    """
    if not rows:
        return "Нет записей."
    t = PrettyTable()
    field_names = [c["name"] for c in columns]
    t.field_names = field_names
    # Цикл по записям для добавления строк в таблицу
    for row in rows:
        t.add_row([row.get(col["name"]) for col in columns])
    return str(t)

def convert_value_to_type(value: str, target_type: str) -> Any:
    """Преобразует строковое значение к целевому типу (int, bool, str)."""
    target_type = target_type.lower()

    # Если это уже не строка — возвращаем как есть (на всякий случай)
    if not isinstance(value, str):
        return value

    # Убираем внешние кавычки
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

    else:  # str
        return value


def run():
    """Основной цикл командной строки (REPL)."""
    print("Примитивная база данных. Введите 'help' для списка команд.")

    while True:
        try:
            command_line = input(">>> Введите команду: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход из программы.")
            break

        if not command_line:
            continue

        parts = shlex.split(command_line)
        cmd = parts[0].lower()

        # --- create_table ---
        if cmd == "create_table":
            if len(parts) < 3:
                print("Ошибка: недостаточно аргументов. Формат: create_table <name> <col:type> ...")
                continue
            table_name = parts[1]
            columns_raw = parts[2:]
            try:
                metadata = load_metadata(METADATA_FILE)
                metadata = create_table(metadata, table_name, columns_raw)
                save_metadata(METADATA_FILE, metadata)
                cols_str = ", ".join(f"{c['name']}:{c['type']}" for c in metadata[table_name])
                print(f'Таблица "{table_name}" успешно создана со столбцами: {cols_str}')
            except ValueError as e:
                print(f"Ошибка: {e}")

        # --- drop_table ---
        elif command_line.lower().startswith("drop_table "):
            _, table_name = command_line.split(maxsplit=1)
            try:
                metadata = load_metadata(METADATA_FILE)
                metadata = drop_table(metadata, table_name)
                save_metadata(METADATA_FILE, metadata)  # <-- обязательно!
                print(f'Таблица "{table_name}" успешно удалена.')
            except ValueError as e:
                print(f"Ошибка: {e}")

        # --- list_tables ---
        elif cmd == "list_tables":
            metadata = load_metadata(METADATA_FILE)
            tables = list_tables(metadata)
            if not tables:
                print("- (таблиц нет)")
            else:
                # Цикл для вывода списка таблиц
                for t in tables:
                    print(f"- {t}")

        # --- insert into ---
        elif command_line.lower().startswith("insert into "):
            match = re.match(r'insert\s+into\s+(\w+)\s+values\s*(.*)', command_line, re.IGNORECASE)
            if not match:
                print("Ошибка синтаксиса INSERT.")
                continue
            table_name, values_part = match.groups()
            try:
                metadata = load_metadata(METADATA_FILE)
                if table_name not in metadata:
                    raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')

                columns = metadata[table_name]
                expected_count = len(columns) - 1  # без ID

                values_raw = parse_values(values_part)
                if len(values_raw) != expected_count:
                    raise ValueError(
                        f"Ожидается {expected_count} значений, передано {len(values_raw)}."
                    )

                # Преобразуем значения к нужным типам
                converted_values = []
                for i, val_raw in enumerate(values_raw):
                    col_def = columns[i + 1]  # пропускаем ID
                    converted = convert_value_to_type(val_raw, col_def["type"])
                    converted_values.append(converted)

                data = load_data(table_name) or []
                new_id = (max((r["ID"] for r in data), default=0) + 1) if data else 1
                record = {"ID": new_id}
                for (col_def, val) in zip(columns[1:], converted_values):
                    record[col_def["name"]] = val

                data = create(data, record)
                save_data(table_name, data)
                print(f'Запись с ID={new_id} успешно добавлена в таблицу "{table_name}".')
            except ValueError as e:
                print(f"Ошибка: {e}")


        # --- select from ---
        elif command_line.lower().startswith("select from "):
            match = re.match(r'select\s+from\s+(\w+)(?:\s+where\s+(.+))?', command_line, re.IGNORECASE)
            if not match:
                print("Ошибка синтаксиса SELECT.")
                continue
            table_name, where_part = match.groups()
            try:
                metadata = load_metadata(METADATA_FILE)
                if table_name not in metadata:
                    raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')
                columns = metadata[table_name]
                data = load_data(table_name) or []
                where_clause = parse_where_clause(where_part.strip()) if where_part else None
                filtered = filter_records(data, where_clause)
                print(format_table(filtered, columns))
            except ValueError as e:
                print(f"Ошибка: {e}")

        # --- update ---
        elif command_line.lower().startswith("update "):
            match = re.match(r'update\s+(\w+)\s+set\s+(.+)\s+where\s+(.+)', command_line, re.IGNORECASE)
            if not match:
                print("Ошибка синтаксиса UPDATE.")
                continue
            table_name, set_part, where_part = match.groups()
            try:
                metadata = load_metadata(METADATA_FILE)
                if table_name not in metadata:
                    raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')
                set_clause = parse_set_clause(set_part.strip())
                where_clause = parse_where_clause(where_part.strip())
                data = load_data(table_name) or []
                updated_count = 0
                # Цикл по всем записям для поиска совпадений с WHERE
                for row in data:
                    if all(row.get(k) == v for k, v in where_clause.items()):
                        row.update(set_clause)
                        updated_count += 1
                if updated_count > 0:
                    save_data(table_name, data)
                    print(f"Обновлено записей: {updated_count}")
                else:
                    print("Записей, удовлетворяющих условию WHERE, не найдено.")
            except ValueError as e:
                print(f"Ошибка: {e}")

        # --- delete from ---
        elif command_line.lower().startswith("delete from "):
            match = re.match(r'delete\s+from\s+(\w+)\s+where\s+(.+)', command_line, re.IGNORECASE)
            if not match:
                print("Ошибка синтаксиса DELETE.")
                continue
            table_name, where_part = match.groups()
            try:
                metadata = load_metadata(METADATA_FILE)
                if table_name not in metadata:
                    raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')
                where_clause = parse_where_clause(where_part.strip())
                data = load_data(table_name) or []
                initial_len = len(data)
                # Фильтрация списка: оставляем только те строки, которые НЕ подходят под WHERE
                data[:] = [row for row in data if not all(row.get(k) == v for k, v in where_clause.items())]
                deleted_count = initial_len - len(data)
                if deleted_count > 0:
                    save_data(table_name, data)
                    print(f"Удалено записей: {deleted_count}")
                else:
                    print("Записей, удовлетворяющих условию WHERE, не найдено.")
            except ValueError as e:
                print(f"Ошибка: {e}")

        # --- info ---
        elif command_line.lower().startswith("info "):
            parts = command_line.split()
            if len(parts) != 2:
                print("Ошибка: требуется имя таблицы. Формат: info <table>")
                continue
            table_name = parts[1]
            try:
                metadata = load_metadata(METADATA_FILE)
                if table_name not in metadata:
                    raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')
                columns = metadata[table_name]
                cols_desc = ", ".join(f"{c['name']}:{c['type']}" for c in columns)
                data = load_data(table_name) or []
                print(f"Таблица: {table_name}")
                print(f"Столбцы: {cols_desc}")
                print(f"Количество записей: {len(data)}")
            except ValueError as e:
                print(f"Ошибка: {e}")

        # --- help ---
        elif cmd == "help":
            print("\n***Процесс работы с таблицей***")
            print("Функции:")
            print("<command> create_table <имя_таблицы> <столбец1:тип> <столбец2:тип> ... - создать таблицу")
            print("<command> list_tables - показать список всех таблиц")
            print("<command> drop_table <имя_таблицы> - удалить таблицу")
    
            print("\nОперации с данными:")
            print("<command> insert into <имя_таблицы> values (<значение1>, <значение2>, ...) - добавить запись")
            print("<command> select from <имя_таблицы> [where <столбец> = <значение>] - выбрать записи")
            print("<command> update <имя_таблицы> set <столбец> = <новое_значение> where <условие> - обновить записи")
            print("<command> delete from <имя_таблицы> where <столбец> = <значение> - удалить записи")
            print("<command> info <имя_таблицы> - информация о таблице")
    
            print("\nОбщие команды:")
            print("<command> exit - выход из программы")
            print("<command> help - справка\n")

        # --- exit ---
        elif cmd == "exit":
            print("Выход из программы.")
            break

        else:
            print(f'Команды "{cmd}" нет. Попробуйте снова или введите "help".')
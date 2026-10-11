# src/primitive_db/engine.py
import shlex
from typing import Dict, Any
from .utils import load_metadata, save_metadata
from .core import create_table, drop_table, list_tables

METADATA_FILE = "db_meta.json"

def run():
    """Основной игровой цикл CLI"""
    print(">>> Введите команду: _", end="\r")  # можно убрать, если хочешь просто input()
    
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
        elif cmd == "drop_table":
            if len(parts) != 2:
                print("Ошибка: требуется имя таблицы. Формат: drop_table <name>")
                continue
            table_name = parts[1]
            try:
                metadata = load_metadata(METADATA_FILE)
                metadata = drop_table(metadata, table_name)
                save_metadata(METADATA_FILE, metadata)
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
                for t in tables:
                    print(f"- {t}")

        # --- help ---
        elif cmd == "help":
            print("Доступные команды:")
            print("  create_table <name> <col:type> ... — создать таблицу (автоматически добавляется ID:int)")
            print("  drop_table <name> — удалить таблицу")
            print("  list_tables — показать список таблиц")
            print("  help — справка")
            print("  exit — выход")

        # --- exit ---
        elif cmd == "exit":
            print("Выход из программы.")
            break

        else:
            print(f'Функции "{cmd}" нет. Попробуйте снова или введите "help".')

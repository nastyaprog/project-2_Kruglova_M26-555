# PrimitiveDB — примитивная база данных на Python

Учебный проект: реализация собственной базы данных с CRUD-операциями, декораторами, валидацией типов и обработкой условий WHERE.

## Возможности

- **CRUD-операции**: `create_table`, `insert`, `select`, `delete`, `drop_table`.
- **Типизация колонок**: поддержка `str`, `int`, `float`, `bool`.
- **Автоматическое поле `ID`**: добавляется ко всем таблицам.
- **Условия WHERE**: фильтрация и удаление по условиям (`=`, `>`, `<`, `>=`, `<=`, `!=`).
- **Валидация**: проверка типов данных, уникальности имени таблицы, корректности синтаксиса.
- **Декораторы**: логирование времени выполнения, подтверждение опасных действий, обработка ошибок.
- **Вывод результатов**: форматирование таблиц через `prettytable`.

## Архитектура проекта

Проект разбит на модули для разделения ответственности:

- `src/primitive_db/engine.py` — CLI-интерфейс, парсинг команд, цикл ввода.
- `src/primitive_db/core.py` — бизнес-логика CRUD, фильтрация, генерация ID.
- `src/primitive_db/parser.py` — парсинг определений колонок и условий WHERE.
- `src/primitive_db/decorators.py` — декораторы для логирования, подтверждения и обработки ошибок.
- `src/primitive_db/utils.py` — работа с файлами (JSON), загрузка/сохранение метаданных и данных.
- `src/primitive_db/constants.py` — константы (поддерживаемые типы и т.п.).

Данные хранятся в папке `data/` в виде JSON-файлов, метаданные — в `db_meta.json`.

## Быстрый старт

### Установка зависимостей

```bash
uv pip install prettytable

### Запуск базы данных

uv run database

После запуска появится приглашение:
Примитивная база данных. Введите 'help' для списка команд.
>>> Введите команду:

### Команды CLI

create_table <name> <col:type> - Создать таблицу с колонками. Пример: create_table users name:str age:int
drop_table <name> - Удалить таблицу. Пример: drop_table users
list_tables - Показать список таблиц. Пример: list_tables
insert into <name> values (...) - Вставить запись. Пример: insert into users values ('Alice', 25)
select from <name> [where ...] - Выбрать записи (с фильтром). Пример: select from users where age > 20
delete from <name> where ... - Удалить записи по условию. Пример: delete from users where name = 'Alice'
help - Показать справку. Пример: help
exit - Выход из программы. Пример: exit

Для операций drop_table и delete требуется подтверждение (y/n).

### Демонстрация работы программы (asciinema)

Сценарий для asciinema:

create_table users name:str age:int is_active:bool
insert into users values ('Alice', 25, true)
insert into users values ('Bob', 30, false)
insert into users values ('Charlie', 35, true)
select from users
select from users where age > 28
delete from users where name = 'Alice'
Вы уверены, что хотите выполнить "удаление записей"? [y/n]: y
select from users
drop_table users
Вы уверены, что хотите выполнить "удаление таблицы"? [y/n]: y
list_tables
exit

https://asciinema.org/a/GD5yhzWf9tv9IBru

### Особенности реализации

Автоинкремент ID: реализован через max(ID) + 1 при каждой вставке. ID не переиспользуются после удаления.
WHERE: поддерживается только одно условие (без AND/OR). Операторы: =, >, <, >=, <=, !=, <>.
Типы данных: str, int, float, bool.
Подтверждение опасных действий: требуется для drop_table и delete.
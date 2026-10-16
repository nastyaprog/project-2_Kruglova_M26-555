import time
from functools import wraps

# 1. Декоратор обработки ошибок
def handle_db_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError:
            print("Ошибка: Файл данных не найден. Возможно, база данных не инициализирована.")
        except KeyError as e:
            # Если это ошибка про таблицу, уберём лишние кавычки для красоты
            error_msg = str(e).replace("'", "")
            print(f"Ошибка: Таблица или столбец '{error_msg}' не найден.")
        except ValueError as e:
            print(f"Ошибка валидации: {e}")
        except Exception as e:
            print(f"Произошла непредвиденная ошибка: {e}")
    return wrapper


# 2. Декоратор с аргументом: подтверждение действия
def confirm_action(action_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            confirm = input(f"Вы уверены, что хотите выполнить \"{action_name}\"? [y/n]: ").strip().lower()
            if confirm != "y":
                print("Операция отменена пользователем.")
                return 0  # или None — главное, не запускать реальную функцию
            return func(*args, **kwargs)
        return wrapper
    return decorator


# 3. Декоратор замера времени
def log_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        result = func(*args, **kwargs)
        end = time.monotonic()
        print(f"Функция {func.__name__} выполнилась за {end - start:.3f} секунд.")
        return result
    return wrapper


# 4. Функция-фабрика для создания замыкания (кэш)
def create_cacher():
    cache = {}  # Это состояние замыкания! Оно будет жить, пока работает программа
    
    def cache_result(key, value_func):
        if key in cache:
            # print("(из кэша)") # Можно раскомментировать для отладки
            return cache[key]
        
        # Если нет в кэше — вычисляем, сохраняем и возвращаем
        result = value_func()
        cache[key] = result
        return result
    
    return cache_result

import prompt


def welcome():
    """Спрашивает имя пользователя и приветствует его."""
    name = prompt.string("May I have your name? ")
    print(f"Hello, {name}! Welcome to the primitive DB.")


def run_loop():
    """Игровой цикл с командами help/exit."""
    while True:
        print("\n<command> exit - выйти из программы")
        print("<command> help - справочная информация")
        command = input("Введите команду: ").strip().lower()

        if command == "exit":
            print("Goodbye!")
            break
        elif command == "help":
            print("Доступные команды: exit, help")
        else:
            print("Неизвестная команда. Используйте help для справки.")

#!/usr/bin/env python3


from .engine import run_loop, welcome


def main():
    welcome()      # Сначала спрашиваем имя и здороваемся
    run_loop()     # Потом запускаем цикл команд (help/exit)

if __name__ == "__main__":
    main()

from enum import StrEnum

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


class BaseActions(StrEnum):
    start = "Старт"
    register = "Регистрация"
    login = "Авторизация"
    logout = "Выход"
    cancel = "Отмена"


class AdminActions(StrEnum):
    make_reg_code = "Код"


def get_main_keyboard(*actions) -> ReplyKeyboardMarkup:
    """Главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=action)] for action in actions],
        resize_keyboard=True,  # Подгоняет размер кнопки под экран
        input_field_placeholder="Выберите действие...",  # Подсказка в поле ввода
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    """Удаляет reply-клавиатуру"""
    return ReplyKeyboardRemove()

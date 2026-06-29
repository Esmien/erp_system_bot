from enum import StrEnum

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


class Actions(StrEnum):
    start = "Старт"
    logout = "Выход"


def get_main_keyboard(action: Actions) -> ReplyKeyboardMarkup:
    """Главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=action)]],
        resize_keyboard=True,  # Подгоняет размер кнопки под экран
        input_field_placeholder="Выберите действие...",  # Подсказка в поле ввода
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    """Удаляет reply-клавиатуру"""
    return ReplyKeyboardRemove()

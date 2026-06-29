from typing import Literal

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def get_main_keyboard(action: Literal["Старт", "Выход"]) -> ReplyKeyboardMarkup:
    """Главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=action)]],
        resize_keyboard=True,  # Подгоняет размер кнопки под экран
        input_field_placeholder="Выберите действие...",  # Подсказка в поле ввода
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    """Удаляет reply-клавиатуру"""
    return ReplyKeyboardRemove()

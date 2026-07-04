from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class RoleCallback(CallbackData, prefix="role"):
    """Фабрика для коллбеков выбора роли. Хранит в себе системное имя роли."""

    name: str


def get_roles_inline_keyboard(roles: list[dict]) -> InlineKeyboardMarkup:
    """Генерирует инлайн-кнопки на основе списка ролей от бэкенда"""
    builder = InlineKeyboardBuilder()

    for role in roles:
        role_name = role["name"]
        # Делаем название с большой буквы для красоты в кнопке
        display_name = role_name.capitalize()

        builder.button(text=display_name, callback_data=RoleCallback(name=role_name))

    # Выстраиваем кнопки в один столбец
    builder.adjust(1)
    return builder.as_markup()

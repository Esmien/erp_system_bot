from enum import StrEnum

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder


class BaseActions(StrEnum):
    profile = "👤 Профиль"
    tasks = "📋 Мои задачи"
    schedule = "📅 Расписание"
    logout = "🚪 Выход"
    cancel = "❌ Отмена"


class AdminActions(StrEnum):
    make_reg_code = "⚙️ Код регистрации"


def get_main_keyboard(is_auth: bool, role: str | None = None) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
    """
    Генерирует навигационное меню.
    Если пользователь не авторизован - скрывает нижнюю клавиатуру (оставляя только инлайн).
    """
    if not is_auth:
        return ReplyKeyboardRemove()

    builder = ReplyKeyboardBuilder()

    # Базовые кнопки для авторизованных
    builder.button(text=BaseActions.tasks)
    builder.button(text=BaseActions.schedule)
    builder.button(text=BaseActions.profile)

    # Админские кнопки (проверяем на admin и manager)
    if role and role.lower() in ("admin", "manager"):
        builder.button(text=AdminActions.make_reg_code)

    # Выход всегда последним
    builder.button(text=BaseActions.logout)

    # Группируем красиво: 2 в ряд, затем по одной
    builder.adjust(2, 1, 1, 1)

    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Выберите раздел...")


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с одной кнопкой 'Отмена' для процессов FSM"""
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BaseActions.cancel)]], resize_keyboard=True)


def remove_keyboard() -> ReplyKeyboardRemove:
    """Удаляет reply-клавиатуру"""
    return ReplyKeyboardRemove()

import contextlib

from aiogram import types
from aiogram.fsm.context import FSMContext


async def clean_chat_history(message: types.Message, state: FSMContext) -> None:
    """
    Удаляет текущее сообщение пользователя и последний вопрос/меню бота.
    """
    # Удаляем сообщение юзера
    with contextlib.suppress(Exception):
        await message.delete()

    # Удаляем зависший вопрос бота
    data = await state.get_data()
    if last_msg_id := data.get("last_bot_msg_id"):
        with contextlib.suppress(Exception):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)

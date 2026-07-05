import contextlib

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.api_clients.api_user_client import ApiUserClient

router = Router()


@router.message(Command("me"))
async def get_my_info(message: types.Message, state: FSMContext, user_client: ApiUserClient):
    data = await state.get_data()

    # Пытаемся удалить прошлый вопрос/меню бота ДО очистки стейта
    if last_msg_id := data.get("last_bot_msg_id"):
        with contextlib.suppress(Exception):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)

    access_token = data.get("access_token")

    if not access_token:
        await message.answer(text="Что-то не так с авторизацией. Пройдите ее еще раз.")
        return

    my_info = await user_client.get_my_info(token=access_token)

    my_id = my_info.id
    name = my_info.name
    surname = my_info.surname
    last_name = my_info.last_name
    email = my_info.email
    role = my_info.role.name.capitalize()
    status = "Активен" if my_info.is_active else "Деактивирован"
    my_tg_id = my_info.tg_id

    response_text = (
        f"👤 <b>{role}</b>\n\n"
        f"ID: <code>{my_id}</code>\n"
        f"Фамилия: <b>{last_name}</b>\n"
        f"Имя: <b>{name}</b>\n"
        f"Отчество: <b>{surname}</b>\n"
        f"Email: <code>{email}</code>\n"
        f"Статус: <b>{status}</b>\n"
        f"TelegramID: <code>{my_tg_id}</code>"
    )

    await message.answer(text=response_text)

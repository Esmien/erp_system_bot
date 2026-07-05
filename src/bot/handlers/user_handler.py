import contextlib

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.api_clients.api_user_client import ApiUserClient

router = Router()


@router.message(Command("me"))
async def get_my_info(message: types.Message, state: FSMContext, user_client: ApiUserClient):
    # Сразу чистим чат от самой команды /me
    with contextlib.suppress(Exception):
        await message.delete()

    data = await state.get_data()

    # Удаляем старое сообщение/меню бота
    if last_msg_id := data.get("last_bot_msg_id"):
        with contextlib.suppress(Exception):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)

    access_token = data.get("access_token")

    if not access_token:
        msg = await message.answer(text="⚠️ Сессия не найдена. Пожалуйста, авторизуйтесь заново (/start).")
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    # Вешаем временную заглушку для отзывчивости интерфейса
    wait_msg = await message.answer("⏳ Загружаю профиль...")

    my_info = await user_client.get_my_info(token=access_token)

    # Убираем заглушку
    with contextlib.suppress(Exception):
        await wait_msg.delete()

    # Защита от падения, если бэкенд вернул None
    if not my_info:
        msg = await message.answer(text="❌ Ошибка получения данных. Возможно, сессия истекла. Нажми /start")
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    # Элегантная сборка данных
    status = "🟢 Активен" if my_info.is_active else "🔴 Деактивирован"
    role = my_info.role.name.capitalize()

    # Собираем ФИО, отбрасывая пустые поля
    full_name_parts = [my_info.last_name, my_info.name, my_info.surname]
    full_name = " ".join(part for part in full_name_parts if part)

    response_text = (
        f"👤 <b>Ваш профиль ({role})</b>\n\n"
        f"<b>ФИО:</b> {full_name}\n"
        f"<b>Email:</b> <code>{my_info.email}</code>\n"
        f"<b>Статус:</b> {status}\n\n"
        f"<i>ID: {my_info.id} | TG: {my_info.tg_id}</i>"
    )

    msg = await message.answer(text=response_text)

    # Сохраняем ID этой карточки, чтобы бот смог убрать ее потом
    await state.update_data(last_bot_msg_id=msg.message_id)

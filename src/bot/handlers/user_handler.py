import contextlib

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.api_clients.api_user_client import ApiUserClient
from bot.core.utils.chat_cleaner import clean_chat_history
from bot.views.user_view import UserRenderer as renderer

router = Router()


@router.message(Command("me"))
async def get_my_info(message: types.Message, state: FSMContext, user_client: ApiUserClient):
    await clean_chat_history(message=message, state=state)

    data = await state.get_data()
    access_token = data.get("access_token")

    if not access_token:
        msg = await message.answer(text=renderer.session_expired_msg)
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    # Вешаем временную заглушку для отзывчивости интерфейса
    wait_msg = await message.answer(text=renderer.profile_loading_msg)

    my_info = await user_client.get_my_info(token=access_token)

    # Убираем заглушку
    with contextlib.suppress(Exception):
        await wait_msg.delete()

    # Защита от падения, если бэкенд вернул None
    if not my_info:
        msg = await message.answer(text=renderer.loading_error_msg)
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    response_text = renderer.render_profile_text(user=my_info)
    msg = await message.answer(text=response_text)

    # Сохраняем ID этой карточки, чтобы бот смог убрать ее потом
    await state.update_data(last_bot_msg_id=msg.message_id)

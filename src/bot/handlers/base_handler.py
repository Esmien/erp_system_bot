import contextlib

from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.api_clients.api_auth_client import ApiAuthClient
from bot.keyboards.inline_keyboard import select_action
from bot.keyboards.reply_keyboard import AdminActions, BaseActions, get_main_keyboard, remove_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, auth_client: ApiAuthClient):
    """
    Точка входа.
    Выполняет тихую авторизацию, если TelegramID пользователя связан с учеткой ERP
    Если связи нет - предлагает авторизацию по логину и паролю или регистрацию
    """
    data = await state.get_data()

    # Пытаемся удалить прошлый вопрос/меню бота ДО очистки стейта
    if last_msg_id := data.get("last_bot_msg_id"):
        with contextlib.suppress(Exception):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)

    # Удаляем само сообщение юзера с командой /start, чтобы чат был чистым
    with contextlib.suppress(Exception):
        await message.delete()

    # Проверяем кэш FSM (тихая авторизация без дерганья бэкенда)
    if data.get("access_token"):
        msg = await message.answer(
            text="Вы уже авторизованы в системе.",
            reply_markup=get_main_keyboard(AdminActions.make_reg_code, BaseActions.logout),
        )
        # Перезаписываем ID, чтобы следующий /start снес и это сообщение
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    # Теперь безопасно очищаем стейт
    await state.clear()

    # Вешаем сообщение-заглушку на время запроса
    wait_msg = await message.answer(text="Проверяю учетную запись ERP...", reply_markup=remove_keyboard())

    # Если в стейте пусто, стучимся на бэкенд по tg_id
    access_token, refresh_token = await auth_client.attempt_telegram_login()

    # Удаляем заглушку, бэкенд ответил
    with contextlib.suppress(Exception):
        await wait_msg.delete()

    if access_token:
        msg = await message.answer(
            text="Вы успешно авторизованы в системе.",
            reply_markup=get_main_keyboard(AdminActions.make_reg_code, BaseActions.logout),
        )
        # Восстанавливаем токены в FSM и сохраняем ID нового сообщения
        await state.update_data(access_token=access_token, refresh_token=refresh_token, last_bot_msg_id=msg.message_id)
    else:
        # Пользователь не привязан к ТГ
        keyboard = select_action()
        msg = await message.answer(
            text=f"Привет, {message.from_user.first_name}!\nТы еще не авторизован в системе.\n\nВыбери действие:",
            reply_markup=keyboard,
        )
        # Сохраняем ID стартового меню
        await state.update_data(last_bot_msg_id=msg.message_id)

import contextlib

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.api_clients.api_auth_client import ApiAuthClient
from bot.core.utils.chat_cleaner import clean_chat_history
from bot.keyboards.inline_keyboard import ActionCallback, InlineActions
from bot.keyboards.reply_keyboard import AdminActions, BaseActions, get_main_keyboard, remove_keyboard
from bot.states.auth_state import AuthState
from bot.views.auth_view import AuthRenderer as renderer

router = Router()


@router.callback_query(ActionCallback.filter(F.action == InlineActions.login))
async def process_login_callback(callback: types.CallbackQuery, state: FSMContext):
    """Перехватываем нажатие на инлайн-кнопку 'Войти'"""
    # Блокируем кнопку до получения ответа от ТГ
    await callback.answer()

    # Сбрасываем стейт для избежания грязного состояния
    await state.clear()

    # Удаляем предыдущее сообщение с кнопкой
    with contextlib.suppress(Exception):
        await callback.message.delete()

    # Запускаем флоу авторизации
    msg = await callback.message.answer(
        text=renderer.welcome_auth_msg,
        reply_markup=get_main_keyboard(BaseActions.cancel),
    )
    # Сохраняем ID предыдущего сообщения для дальнейшей очистки
    await state.update_data(last_bot_msg_id=msg.message_id)

    # Переключаем стейт на ожидание email
    await state.set_state(AuthState.waiting_for_email)


@router.message(AuthState.waiting_for_email, F.text)
async def process_email(message: types.Message, state: FSMContext):
    """
    Хэндлер для обработки email пользователя.
    Срабатывает только тогда, когда контекст ожидает ввода email (waiting_for_email)
    После обработки меняет контекст на ожидание пароля (waiting_for_password)
    """
    await clean_chat_history(message=message, state=state)

    email = message.text.strip()

    # Отправляем новый вопрос и перезаписываем ID в FSM
    msg = await message.answer(
        text=renderer.waiting_for_password_msg, reply_markup=get_main_keyboard(BaseActions.cancel)
    )

    await state.update_data(email=email, last_bot_msg_id=msg.message_id)
    await state.set_state(AuthState.waiting_for_password)


@router.message(AuthState.waiting_for_password, F.text)
async def process_password(message: types.Message, state: FSMContext, auth_client: ApiAuthClient):
    """
    Хэндлер для обработки пароля.
    Срабатывает только тогда, когда контекст ожидает ввода пароля (waiting_for_password)
    """
    await clean_chat_history(message=message, state=state)

    # Достаем email из памяти FSM
    data = await state.get_data()
    email = data.get("email")
    password = message.text.strip()

    if not email or not isinstance(email, str):
        msg = await message.answer(text=renderer.wrong_email_format_msg)
        await state.set_state(AuthState.waiting_for_email)
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    # Если пользователь по ошибке или приколу отправил бинарник (картинка, стикер, медиафайл и так далее)
    if not password:
        msg = await message.answer(text=renderer.wrong_password_format_msg)
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    wait_msg = await message.answer(text=renderer.waiting_for_linked_telegram_msg)

    # Отправляем креды на бэкенд
    access_token, refresh_token = await auth_client.link_telegram_account(email=email, password=password)

    # На этом этапе получен ответ от бэка, удаляем заглушку
    with contextlib.suppress(Exception):
        await wait_msg.delete()

    if access_token:
        await state.clear()  # Очищаем email и пароль из памяти FSM, сбрасываем контекст

        # Сохраняем токен в контекст FSM
        await state.update_data(access_token=access_token, refresh_token=refresh_token)
        await message.answer(
            text=renderer.succeed_link_telegram_msg,
            reply_markup=get_main_keyboard(AdminActions.make_reg_code),
        )
    else:
        msg = await message.answer(text=renderer.bad_credentials_msg)

        # Откидываем юзера на шаг назад
        await state.set_state(AuthState.waiting_for_email)
        await state.update_data(last_bot_msg_id=msg.message_id)


@router.message(Command("logout"))
async def cmd_logout(message: types.Message, state: FSMContext, auth_client: ApiAuthClient):
    """
    Хэндлер отвязки TelegramID от аккаунта ERP.
    Отправляет запрос на удаление TGID из записи аккаунта в БД.
    Идентификация происходит по JWT access
    """
    with contextlib.suppress(Exception):
        await message.delete()

    wait_msg = await message.answer("Выполняю выход...")

    # Отвязываем ТГ на бэкенде
    is_unlinked = await auth_client.unlink_telegram_account()

    # Стираем все данные из памяти бота
    await state.clear()

    if is_unlinked:
        await message.answer(text=renderer.succeed_unlinked_telegram_msg, reply_markup=remove_keyboard())
    else:
        await message.answer(
            text=renderer.unlinked_with_error_msg,
            reply_markup=get_main_keyboard(BaseActions.cancel),
        )

    with contextlib.suppress(Exception):
        await wait_msg.delete()

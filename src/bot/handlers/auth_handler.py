import contextlib

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.api_clients.api_auth_client import ApiAuthClient
from bot.api_clients.api_user_client import ApiUserClient
from bot.core.utils.chat_cleaner import clean_chat_history
from bot.keyboards.inline_keyboard import ActionCallback, InlineActions, select_action
from bot.keyboards.reply_keyboard import (
    BaseActions,
    get_cancel_keyboard,
    get_main_keyboard,
)
from bot.services.auth_service import AuthService, LoginResult
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
        reply_markup=get_cancel_keyboard(),
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
    msg = await message.answer(text=renderer.waiting_for_password_msg, reply_markup=get_cancel_keyboard())

    await state.update_data(email=email, last_bot_msg_id=msg.message_id)
    await state.set_state(AuthState.waiting_for_password)


@router.message(AuthState.waiting_for_password, F.text)
async def process_password(
    message: types.Message, state: FSMContext, auth_client: ApiAuthClient, user_client: ApiUserClient
):
    """Хэндлер пароля. Собирает данные авторизации и отдает их сервису."""
    await clean_chat_history(message=message, state=state)

    data = await state.get_data()
    email = data.get("email")
    password = message.text.strip()

    # Базовая валидация ввода
    if not email or not isinstance(email, str):
        msg = await message.answer(text=renderer.wrong_email_format_msg)
        await state.set_state(AuthState.waiting_for_email)
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    if not password:
        msg = await message.answer(text=renderer.wrong_password_format_msg)
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    wait_msg = await message.answer(text=renderer.waiting_for_linked_telegram_msg)

    # Инициализируем сервис и передаем ему данные
    auth_service = AuthService(auth_client=auth_client, user_client=user_client)
    result: LoginResult = await auth_service.login_with_credentials(email=email, password=password)

    with contextlib.suppress(Exception):
        await wait_msg.delete()

    # Управляем UI на основе ответа сервиса
    if result.is_success:
        await state.clear()

        await state.update_data(access_token=result.access_token, refresh_token=result.refresh_token, role=result.role)

        await message.answer(
            text=renderer.succeed_link_telegram_msg,
            reply_markup=get_main_keyboard(is_auth=True, role=result.role),
        )
    else:
        msg = await message.answer(text=renderer.bad_credentials_msg)
        await state.set_state(AuthState.waiting_for_email)
        await state.update_data(last_bot_msg_id=msg.message_id)


@router.message(Command("logout"))
@router.message(F.text == BaseActions.logout)
async def cmd_logout(message: types.Message, state: FSMContext, auth_client: ApiAuthClient, user_client: ApiUserClient):
    """Хэндлер логаута. Отвязывает аккаунт ТГ от аккаунта ERP"""
    with contextlib.suppress(Exception):
        await message.delete()

    wait_msg = await message.answer("Выполняю выход...")

    # Делегируем работу сервису
    auth_service = AuthService(auth_client=auth_client, user_client=user_client)
    is_unlinked = await auth_service.logout()

    await state.clear()

    with contextlib.suppress(Exception):
        await wait_msg.delete()

    if is_unlinked:
        msg = await message.answer(text=renderer.succeed_unlinked_telegram_msg, reply_markup=select_action())
        cleaner = await message.answer("...", reply_markup=get_main_keyboard(is_auth=False))
        await cleaner.delete()
        await state.update_data(last_bot_msg_id=msg.message_id)
    else:
        await message.answer(
            text=renderer.unlinked_with_error_msg,
            reply_markup=get_main_keyboard(is_auth=False),
        )

import contextlib
import re

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from bot.api_clients.api_auth_client import ApiAuthClient
from bot.api_clients.api_registration_client import ApiRegistrationClient
from bot.api_clients.api_user_client import ApiUserClient
from bot.core.utils.chat_cleaner import clean_chat_history
from bot.keyboards.inline_keyboard import ActionCallback, InlineActions
from bot.keyboards.reply_keyboard import get_cancel_keyboard, get_main_keyboard
from bot.services.registration_service import RegistrationService
from bot.states.registration_state import RegistrationState
from bot.views.register_view import RegisterRenderer as renderer

router = Router()


@router.callback_query(ActionCallback.filter(F.action == InlineActions.register))
async def process_register_callback(callback: types.CallbackQuery, state: FSMContext):
    """Перехватываем нажатие на инлайн-кнопку 'Зарегистрироваться'"""
    await callback.answer()
    await state.clear()

    with contextlib.suppress(Exception):
        await callback.message.delete()

    # Запускаем флоу регистрации и сохраняем ID первого сообщения
    msg = await callback.message.answer(
        text=renderer.waiting_for_register_code_msg,
        reply_markup=get_cancel_keyboard(),
    )
    await state.update_data(last_bot_msg_id=msg.message_id)

    await state.set_state(RegistrationState.waiting_for_invite_code)


@router.message(RegistrationState.waiting_for_invite_code, F.text)
async def process_invite_code(
    message: types.Message,
    state: FSMContext,
    reg_client: ApiRegistrationClient,
    auth_client: ApiAuthClient,
    user_client: ApiUserClient,
):
    await clean_chat_history(message=message, state=state)
    code = message.text.strip()

    # Инициализируем сервис
    reg_service = RegistrationService(reg_client, auth_client, user_client)
    is_valid = await reg_service.check_invite_code(code=code)

    if not is_valid:
        msg = await message.answer(text=renderer.invalid_register_code_msg)
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    msg = await message.answer(text=renderer.waiting_for_email_msg)
    await state.update_data(register_code=code, last_bot_msg_id=msg.message_id)
    await state.set_state(RegistrationState.waiting_for_email)


@router.message(RegistrationState.waiting_for_email, F.text)
async def process_email(message: types.Message, state: FSMContext):
    await clean_chat_history(message=message, state=state)

    email = message.text.strip()

    if "@" not in email:
        msg = await message.answer(text=renderer.wrong_email_format_msg)
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    msg = await message.answer(text=renderer.waiting_for_full_name_msg)
    await state.update_data(email=email, last_bot_msg_id=msg.message_id)

    await state.set_state(RegistrationState.waiting_for_full_name)


@router.message(RegistrationState.waiting_for_full_name, F.text)
async def process_full_name(message: types.Message, state: FSMContext):
    await clean_chat_history(message=message, state=state)

    text = message.text.strip()

    # Валидация: только буквы (кириллица/латиница), пробелы и дефис для двойных фамилий
    if not re.match(r"^[А-Яа-яЁёA-Za-z\s-]+$", text):
        msg = await message.answer(text=renderer.wrong_full_name_format_msg, reply_markup=get_cancel_keyboard())
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    parts = text.split()

    # Проверяем, что ввели хотя бы 2 слова (Фамилия Имя) и не больше 3
    if len(parts) < 2 or len(parts) > 3:
        msg = await message.answer(text=renderer.wrong_full_name_length_msg, reply_markup=get_cancel_keyboard())
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    # Парсим с капитализацией (чтобы "иванов иван" стало "Иванов Иван")
    last_name = parts[0].capitalize()
    name = parts[1].capitalize()
    surname = parts[2].capitalize() if len(parts) == 3 else None

    # Идем дальше, спрашиваем пароль
    msg = await message.answer(text=renderer.waiting_for_password_msg, reply_markup=get_cancel_keyboard())

    await state.update_data(last_name=last_name, name=name, surname=surname, last_bot_msg_id=msg.message_id)
    await state.set_state(RegistrationState.waiting_for_password)


@router.message(RegistrationState.waiting_for_password, F.text)
async def process_password(
    message: types.Message,
    state: FSMContext,
):
    await clean_chat_history(message=message, state=state)

    password = message.text.strip()

    if len(password) < 3:
        msg = await message.answer(text=renderer.to_short_password_msg)
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    msg = await message.answer(text=renderer.waiting_for_repeat_password_msg)
    await state.update_data(password=password, last_bot_msg_id=msg.message_id)

    await state.set_state(RegistrationState.waiting_for_repeat_password)


@router.message(RegistrationState.waiting_for_repeat_password, F.text)
async def process_repeat_password(
    message: types.Message,
    state: FSMContext,
    reg_client: ApiRegistrationClient,
    auth_client: ApiAuthClient,
    user_client: ApiUserClient,
):
    await clean_chat_history(message=message, state=state)

    user_data = await state.get_data()
    password = user_data.get("password")
    repeated_password = message.text.strip()

    # Базовая валидация (Fail Fast) остается на контроллере, чтобы не дергать сервис впустую
    if repeated_password != password:
        msg = await message.answer(text=renderer.missmatch_password_msg)
        await state.update_data(last_bot_msg_id=msg.message_id)
        await state.set_state(RegistrationState.waiting_for_password)
        return

    await state.update_data(repeat_password=repeated_password)
    payload = await state.get_data()

    wait_msg = await message.answer(text=renderer.register_in_progress_msg)

    # Делегируем всю сложную логику транзакции сервису
    reg_service = RegistrationService(reg_client, auth_client, user_client)
    result = await reg_service.register_and_link(user_payload=payload)

    with contextlib.suppress(Exception):
        await wait_msg.delete()

    # Управляем интерфейсом на основе DTO ответа
    if result.is_success:
        # Имитируем старый UX с визуальным переходом
        await message.answer(text=renderer.waiting_for_telegram_link_msg)
        await state.clear()

        if result.is_linked:
            await state.update_data(
                access_token=result.access_token,
                refresh_token=result.refresh_token,
                role=result.role,
            )
            await message.answer(
                text=renderer.register_succeed_msg,
                reply_markup=get_main_keyboard(is_auth=True, role=result.role),
            )
        else:
            await message.answer(
                text=renderer.fail_for_link_telegram_msg,
                reply_markup=get_main_keyboard(is_auth=False),
            )

    elif result.status_code == 400:
        msg = await message.answer(
            text=f"❌ Ошибка: {result.error_msg}\nПопробуй ввести другой email.",
            reply_markup=get_cancel_keyboard(),
        )
        await state.update_data(last_bot_msg_id=msg.message_id)
        await state.set_state(RegistrationState.waiting_for_email)

    else:
        await state.clear()
        await message.answer(
            text="🛠 Произошла ошибка на сервере. Попробуй позже.\n/start",
            reply_markup=get_main_keyboard(is_auth=False),
        )

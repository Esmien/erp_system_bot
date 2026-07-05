import contextlib

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from loguru import logger

from bot.api_clients.api_auth_client import ApiAuthClient
from bot.api_clients.api_registration_client import ApiRegistrationClient
from bot.core.utils.chat_cleaner import clean_chat_history
from bot.keyboards.inline_keyboard import ActionCallback, InlineActions
from bot.keyboards.reply_keyboard import AdminActions, BaseActions, get_main_keyboard
from bot.schemas.user_schemas import UserRegister
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
        reply_markup=get_main_keyboard(BaseActions.cancel),
    )
    await state.update_data(last_bot_msg_id=msg.message_id)

    await state.set_state(RegistrationState.waiting_for_invite_code)


@router.message(RegistrationState.waiting_for_invite_code, F.text)
async def process_invite_code(message: types.Message, state: FSMContext, reg_client: ApiRegistrationClient):
    await clean_chat_history(message=message, state=state)

    code = message.text.strip()

    # Fail Fast в действии
    is_valid = await reg_client.check_registration_code(code=code)
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

    msg = await message.answer(text=renderer.waiting_for_last_name_msg)
    await state.update_data(email=email, last_bot_msg_id=msg.message_id)

    await state.set_state(RegistrationState.waiting_for_last_name)


@router.message(RegistrationState.waiting_for_last_name, F.text)
async def process_last_name(message: types.Message, state: FSMContext):
    await clean_chat_history(message=message, state=state)

    msg = await message.answer(text=renderer.waiting_for_name_msg)
    await state.update_data(last_name=message.text.strip(), last_bot_msg_id=msg.message_id)

    await state.set_state(RegistrationState.waiting_for_name)


@router.message(RegistrationState.waiting_for_name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    await clean_chat_history(message=message, state=state)

    msg = await message.answer(text=renderer.waiting_for_surname_msg)
    await state.update_data(name=message.text.strip(), last_bot_msg_id=msg.message_id)

    await state.set_state(RegistrationState.waiting_for_surname)


@router.message(RegistrationState.waiting_for_surname, F.text)
async def process_surname(message: types.Message, state: FSMContext):
    await clean_chat_history(message=message, state=state)

    msg = await message.answer(text=renderer.waiting_for_password_msg)
    await state.update_data(surname=message.text.strip(), last_bot_msg_id=msg.message_id)

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
):
    await clean_chat_history(message=message, state=state)

    user_data = await state.get_data()

    password = user_data.get("password")
    repeated_password = message.text.strip()

    if repeated_password != password:
        msg = await message.answer(text=renderer.missmatch_password_msg)

        # Возвращаем на шаг ввода первого пароля
        await state.update_data(last_bot_msg_id=msg.message_id)
        await state.set_state(RegistrationState.waiting_for_password)

        return

    # Сохраняем повторный пароль в стейт перед отправкой на бэк
    await state.update_data(repeat_password=repeated_password)

    # Отправляем временное сообщение-заглушку
    wait_msg = await message.answer(text=renderer.register_in_progress_msg)

    payload = await state.get_data()
    # Убираем техническое поле last_bot_msg_id перед отправкой в Pydantic
    payload.pop("last_bot_msg_id", None)

    user = UserRegister(**payload)

    # Стучимся на регистрацию
    status_code, response_data = await reg_client.register_new_user(user)

    # Бэкенд ответил, удаляем сообщение-заглушку
    with contextlib.suppress(Exception):
        await wait_msg.delete()

    if status_code == 201:
        # Успех. Очищаем стейт и выдаем финальное сообщение (оно уже не требует удаления)
        await message.answer(text=renderer.waiting_for_telegram_link_msg)

        # Немедленно склеиваем аккаунты
        access_token, refresh_token = await auth_client.link_telegram_account(email=user.email, password=user.password)

        await state.clear()

        if access_token:
            await state.update_data(access_token=access_token, refresh_token=refresh_token)
            await message.answer(
                text=renderer.register_succeed_msg,
                reply_markup=get_main_keyboard(AdminActions.make_reg_code),
            )
        else:
            await message.answer(text=renderer.fail_for_link_telegram_msg)

    elif status_code == 400:
        error_msg = response_data.get("detail") if response_data else "Ошибка валидации"
        msg = await message.answer(
            text=f"❌ Ошибка: {error_msg}\nПопробуй ввести другой email.",
            reply_markup=get_main_keyboard(BaseActions.cancel),
        )
        # Сохраняем ID сообщения с ошибкой, чтобы очистить его на следующем круге
        await state.update_data(last_bot_msg_id=msg.message_id)
        await state.set_state(RegistrationState.waiting_for_email)

    else:
        logger.error(f"Неизвестная ошибка при регистрации: {status_code} - {response_data}")
        await state.clear()
        await message.answer(text="🛠 Произошла ошибка на сервере. Попробуй позже.\n/start")

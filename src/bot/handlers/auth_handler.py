import contextlib

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.api_clients.api_auth_client import ApiAuthClient
from bot.keyboards.inline_keyboard import ActionCallback, InlineActions
from bot.keyboards.reply_keyboard import AdminActions, BaseActions, get_main_keyboard
from bot.states.auth_state import AuthState

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
        text="🔐 <b>Авторизация</b>\n------------------------------\n\n📧 Отправь свой рабочий email:",
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
    # Удаляем сообщение с почтой
    with contextlib.suppress(Exception):
        await message.delete()

    # Достаем ID прошлого вопроса бота и удаляем его
    data = await state.get_data()
    if last_msg_id := data.get("last_bot_msg_id"):
        with contextlib.suppress(Exception):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)

    email = message.text.strip()

    # Отправляем новый вопрос и перезаписываем ID в FSM
    msg = await message.answer(text="🔑 Введи пароль:", reply_markup=get_main_keyboard(BaseActions.cancel))

    await state.update_data(email=email, last_bot_msg_id=msg.message_id)
    await state.set_state(AuthState.waiting_for_password)


@router.message(AuthState.waiting_for_password, F.text)
async def process_password(message: types.Message, state: FSMContext, auth_client: ApiAuthClient):
    """
    Хэндлер для обработки пароля.
    Срабатывает только тогда, когда контекст ожидает ввода пароля (waiting_for_password)
    """
    # Пытаемся удалить сообщение с паролем ради безопасности
    with contextlib.suppress(Exception):
        await message.delete()

    # Достаем email из памяти FSM
    data = await state.get_data()
    email = data.get("email")
    password = message.text.strip()

    # Удаляем прошлый вопрос бота про пароль
    if last_msg_id := data.get("last_bot_msg_id"):
        with contextlib.suppress(Exception):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)

    if not email or not isinstance(email, str):
        msg = await message.answer(text="С почтой что-то не так. Отправь свой email повторно:")
        await state.set_state(AuthState.waiting_for_email)
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    # Если пользователь по ошибке или приколу отправил бинарник (картинка, стикер, медиафайл и так далее)
    if not password:
        msg = await message.answer("Пароль должен быть текстом. Попробуй еще раз:")
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    wait_msg = await message.answer("⏳ Выполняю привязку аккаунта...")

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
            text="✅ Учетная запись успешно привязана! Добро пожаловать.",
            reply_markup=get_main_keyboard(AdminActions.make_reg_code),
        )
    else:
        msg = await message.answer(
            "❌ Ошибка авторизации. Неверный email или пароль.\nДавай попробуем еще раз. Отправь свой email:"
        )

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
        await message.answer(text="Учетная запись отвязана. Для новой авторизации нажми /start")
    else:
        await message.answer(
            text="Выход выполнен локально, но сервер не ответил. Связь будет разорвана позже",
            reply_markup=get_main_keyboard(BaseActions.cancel),
        )

    with contextlib.suppress(Exception):
        await wait_msg.delete()

import contextlib

from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from bot.keyboards.reply_keyboard import Actions, get_main_keyboard
from bot.services.api_client import attempt_telegram_login, link_telegram_account, unlink_telegram_account
from bot.states.auth_state import AuthState

router = Router()


@router.message(CommandStart())
@router.message(F.text == Actions.start)
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Точка входа: авторизует пользователя по токену или запускает FSM-сценарий привязки аккаунта.
    """
    await message.answer("Проверяю учетную запись ERP...")

    # Стучимся на бэкенд
    token = await attempt_telegram_login(tg_id=message.from_user.id)

    # Если токен получен, значит, авторизация успешна
    if token:
        await state.update_data(access_token=token)
        await message.answer(
            text="Вы успешно авторизованы в системе.",
            # Рисуем кнопку выхода (отвязки) для удобства пользователя
            reply_markup=get_main_keyboard(Actions.logout),
        )
    else:
        await message.answer(
            f"Привет, {message.from_user.first_name}!\n"
            f"Ты еще не авторизован в системе.\n\n"
            f"Отправь свой email от ERP System:"
        )
        # Включаем FSM: теперь бот ждет email
        await state.set_state(AuthState.waiting_for_email)


@router.message(AuthState.waiting_for_email, F.text)
async def process_email(message: types.Message, state: FSMContext):
    """
    Хэндлер для обработки email пользователя.
    Срабатывает только тогда, когда контекст ожидает ввода email (waiting_for_email)
    После обработки меняет контекст на ожидание пароля (waiting_for_password)
    """
    # Сохраняем введенный email в память FSM
    await state.update_data(email=message.text.strip())

    await message.answer("Введи пароль:")
    # Переключаем FSM: теперь бот ждет пароль
    await state.set_state(AuthState.waiting_for_password)


@router.message(AuthState.waiting_for_password, F.text)
async def process_password(message: types.Message, state: FSMContext):
    """
    Хэндлер для обработки пароля.
    Срабатывает только тогда, когда контекст ожидает ввода пароля (waiting_for_password)
    """
    # Пытаемся удалить сообщение с паролем ради безопасности
    with contextlib.suppress(Exception):
        await message.delete()

    # Достаем email из памяти FSM
    user_data = await state.get_data()
    email = user_data.get("email")
    password = message.text.strip()

    if not email or not isinstance(email, str):
        await message.answer("С почтой что-то не так. Отправь свой email повторно:")
        await state.set_state(AuthState.waiting_for_email)
        return

    # Если пользователь по ошибке или приколу отправил бинарник (картинка, стикер, медиафайл и так далее)
    if not password:
        await message.answer("Пароль должен быть текстом. Попробуй еще раз:")
        return

    await message.answer("Выполняю привязку аккаунта...")

    # Отправляем креды на бэкенд
    token = await link_telegram_account(tg_id=message.from_user.id, email=email, password=password)

    if token:
        await state.clear()  # Очищаем email и пароль из памяти FSM, сбрасываем контекст
        # Сохраняем токен в контекст FSM
        await state.update_data(access_token=token)
        await message.answer(
            text="Учетная запись успешно привязана! Добро пожаловать.",
            reply_markup=get_main_keyboard(Actions.logout),
        )
    else:
        await message.answer(
            "Ошибка авторизации. Неверный email или пароль.\nДавай попробуем еще раз. Отправь свой email:"
        )
        # Откидываем юзера на шаг назад
        await state.set_state(AuthState.waiting_for_email)


@router.message(Command("logout"))
@router.message(F.text == Actions.logout)
async def cmd_logout(message: types.Message, state: FSMContext):
    """
    Хэндлер отвязки TelegramID от аккаунта ERP.
    Отправляет запрос на удаление TGID из записи аккаунта в БД.
    Идентификация происходит по JWT access
    """
    await message.answer("Выполняю выход...")

    # Отвязываем ТГ на бэкенде
    is_unlinked = await unlink_telegram_account(tg_id=message.from_user.id)

    # Стираем все данные из памяти бота
    await state.clear()

    if is_unlinked:
        await message.answer(
            text="Учетная запись отвязана. Для новой авторизации нажми /start",
            reply_markup=get_main_keyboard(Actions.start),
        )
    else:
        await message.answer(
            text="Выход выполнен локально, но сервер не ответил. Связь будет разорвана позже",
            reply_markup=get_main_keyboard(Actions.start),
        )

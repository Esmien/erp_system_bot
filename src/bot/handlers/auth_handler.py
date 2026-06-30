import contextlib

from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from bot.keyboards.reply_keyboard import AdminActions, BaseActions, get_main_keyboard
from bot.services.api_client import attempt_telegram_login, link_telegram_account, unlink_telegram_account
from bot.states.auth_state import AuthState

router = Router()


@router.message(CommandStart())
@router.message(F.text == BaseActions.start)
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Точка входа.
    Выполняет тихую авторизацию, если TelegramID пользователя связан с учеткой ERP
    Если связи нет - предлагает авторизацию по логину и паролю
    """
    data = await state.get_data()

    # Проверяем кэш FSM (тихая авторизация без дерганья бэкенда)
    if data.get("access_token"):
        await message.answer(
            text="Вы уже авторизованы в системе.",
            reply_markup=get_main_keyboard(BaseActions.logout, AdminActions.make_reg_code),
        )
        return

    await state.clear()
    await message.answer("Проверяю учетную запись ERP...")

    # Если в стейте пусто, стучимся на бэкенд по tg_id
    access_token, refresh_token = await attempt_telegram_login(tg_id=message.from_user.id)

    if access_token:
        # Сохраняем токены в FSM, они попадут в redis
        await state.update_data(access_token=access_token, refresh_token=refresh_token)
        await message.answer(
            text="Вы успешно авторизованы в системе.",
            reply_markup=get_main_keyboard(BaseActions.logout, AdminActions.make_reg_code),
        )
    else:
        # Пользователь не привязан к ТГ
        await message.answer(
            f"Привет, {message.from_user.first_name}!\n"
            f"Ты еще не авторизован в системе.\n\n"
            f"Отправь свой email от ERP System:"
        )
        await state.set_state(AuthState.waiting_for_email)


@router.message(Command("cancel"))
@router.message(F.text == BaseActions.cancel)
async def cmd_cancel(message: types.Message, state: FSMContext):
    """
    Хэндлер для сброса состояния при зависании состояния
    """
    current_state = await state.get_state()
    if current_state is None:
        return  # Стейта и так нет, ничего не делаем

    await state.clear()
    await message.answer(text="Действие отменено.", reply_markup=get_main_keyboard(BaseActions.start))


@router.message(AuthState.waiting_for_email, F.text)
async def process_email(message: types.Message, state: FSMContext):
    """
    Хэндлер для обработки email пользователя.
    Срабатывает только тогда, когда контекст ожидает ввода email (waiting_for_email)
    После обработки меняет контекст на ожидание пароля (waiting_for_password)
    """
    # Сохраняем введенный email в память FSM
    await state.update_data(email=message.text.strip())

    await message.answer(text="Введи пароль:", reply_markup=get_main_keyboard(BaseActions.cancel))
    # Переключаем FSM: теперь бот ждет пароль
    await state.set_state(AuthState.waiting_for_password)


@router.message(AuthState.waiting_for_password, F.text)
@router.message(F.text == BaseActions.cancel)
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
        await message.answer(
            text="С почтой что-то не так. Отправь свой email повторно:",
            reply_markup=get_main_keyboard(BaseActions.cancel),
        )
        await state.set_state(AuthState.waiting_for_email)
        return

    # Если пользователь по ошибке или приколу отправил бинарник (картинка, стикер, медиафайл и так далее)
    if not password:
        await message.answer("Пароль должен быть текстом. Попробуй еще раз:")
        return

    await message.answer("Выполняю привязку аккаунта...")

    # Отправляем креды на бэкенд
    access_token, refresh_token = await link_telegram_account(
        tg_id=message.from_user.id, email=email, password=password
    )

    if access_token:
        await state.clear()  # Очищаем email и пароль из памяти FSM, сбрасываем контекст
        # Сохраняем токен в контекст FSM
        await state.update_data(access_token=access_token, refresh_token=refresh_token)
        await message.answer(
            text="Учетная запись успешно привязана! Добро пожаловать.",
            reply_markup=get_main_keyboard(BaseActions.logout),
        )
    else:
        await message.answer(
            "Ошибка авторизации. Неверный email или пароль.\nДавай попробуем еще раз. Отправь свой email:"
        )
        # Откидываем юзера на шаг назад
        await state.set_state(AuthState.waiting_for_email)


@router.message(Command("logout"))
@router.message(F.text == BaseActions.logout)
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
            reply_markup=get_main_keyboard(BaseActions.start),
        )
    else:
        await message.answer(
            text="Выход выполнен локально, но сервер не ответил. Связь будет разорвана позже",
            reply_markup=get_main_keyboard(BaseActions.start, BaseActions.cancel),
        )

import contextlib

from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from bot.keyboards.reply_keyboard import get_main_keyboard
from bot.services.api_client import attempt_telegram_login, link_telegram_account, unlink_telegram_account
from bot.states.auth_state import AuthState

router = Router()


@router.message(CommandStart())
@router.message(F.text == "Старт")
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Проверяю учетную запись ERP...")

    # Стучимся на бэкенд
    token = await attempt_telegram_login(tg_id=message.from_user.id)

    if token:
        await state.update_data(access_token=token)
        await message.answer(
            text="Вы успешно авторизованы в системе.",
            reply_markup=get_main_keyboard("Выход"),
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
    # Сохраняем введенный email в память FSM
    await state.update_data(email=message.text.strip())

    await message.answer("Отлично. Теперь отправь пароль:")
    # Переключаем FSM: теперь бот ждет пароль
    await state.set_state(AuthState.waiting_for_password)


@router.message(AuthState.waiting_for_password, F.text)
async def process_password(message: types.Message, state: FSMContext):
    # Пытаемся удалить сообщение с паролем ради безопасности
    with contextlib.suppress(Exception):
        await message.delete()

    # Достаем email из памяти FSM
    user_data = await state.get_data()
    email = user_data.get("email")
    password = message.text

    if not email or not isinstance(email, str):
        await message.answer("С почтой что-то не так. Отправь свой email повторно:")
        await state.set_state(AuthState.waiting_for_email)
        return

    if not password:
        await message.answer("Пароль должен быть текстом. Попробуй еще раз:")
        return

    await message.answer("Выполняю привязку аккаунта...")

    # Отправляем креды на бэкенд
    token = await link_telegram_account(tg_id=message.from_user.id, email=email, password=password)

    if token:
        await state.clear()  # Очищаем email и пароль из памяти FSM
        await state.update_data(access_token=token)
        await message.answer(
            text="Учетная запись успешно привязана! Добро пожаловать.",
            reply_markup=get_main_keyboard("Выход"),
        )
    else:
        await message.answer(
            "Ошибка авторизации. Неверный email или пароль.\nДавай попробуем еще раз. Отправь свой email:"
        )
        # Откидываем юзера на шаг назад
        await state.set_state(AuthState.waiting_for_email)


@router.message(Command("logout"))
@router.message(F.text == "Выход")
async def cmd_logout(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    token = user_data.get("access_token")

    if not token or not isinstance(token, str):
        await message.answer("Вы и так не авторизованы.")
        return

    await message.answer("Выполняю выход...")

    # Отвязываем ТГ на бэкенде
    is_unlinked = await unlink_telegram_account(token=token)

    # Стираем все данные из памяти бота
    await state.clear()

    if is_unlinked:
        await message.answer(
            text="Учетная запись отвязана. Для новой авторизации нажми /start",
            reply_markup=get_main_keyboard("Старт"),
        )
    else:
        await message.answer(
            text="Выход выполнен локально, но сервер не ответил (возможно, токен истек).",
            reply_markup=get_main_keyboard("Старт"),
        )

import contextlib

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger

from bot.api_clients.api_auth_client import ApiAuthClient
from bot.api_clients.api_registration_client import ApiRegistrationClient
from bot.keyboards.reply_keyboard import AdminActions, BaseActions, get_main_keyboard
from bot.schemas.user_schemas import UserRegister
from bot.states.registration_state import RegistrationState

router = Router()


@router.message(Command("register"))
@router.message(F.text == BaseActions.register)
async def cmd_register(message: types.Message, state: FSMContext):
    """Начало сценария регистрации"""
    await state.clear()
    await message.answer(
        text="📝 <b>Регистрация</b>\n\nВведи 6-значный одноразовый инвайт-код, выданный администратором:",
        reply_markup=get_main_keyboard(BaseActions.cancel),
    )
    await state.set_state(state=RegistrationState.waiting_for_invite_code)


@router.message(RegistrationState.waiting_for_invite_code, F.text)
async def process_invite_code(message: types.Message, state: FSMContext, reg_client: ApiRegistrationClient):
    code = message.text.strip()

    if len(code) != 6:
        await message.answer("⚠️ Код должен состоять ровно из 6 символов. Попробуй еще раз:")
        return

    # Fail Fast в действии: проверяем код ДО того, как мучить юзера формами
    is_valid = await reg_client.check_registration_code(code=code)
    if not is_valid:
        await message.answer("❌ Код недействителен или уже использован. Запроси новый у админа:")
        return

    await state.update_data(register_code=code)
    await message.answer("Отлично. Код принят!\nТеперь отправь свой рабочий email:")
    await state.set_state(RegistrationState.waiting_for_email)


@router.message(RegistrationState.waiting_for_email, F.text)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()

    if "@" not in email:
        await message.answer("⚠️ Это не похоже на email. Попробуй еще раз:")
        return

    await state.update_data(email=email)
    await message.answer("Как к тебе обращаться? Введи свое имя:")
    await state.set_state(RegistrationState.waiting_for_name)


@router.message(RegistrationState.waiting_for_name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Осталось придумать пароль (минимум 3 символа):")
    await state.set_state(RegistrationState.waiting_for_password)


@router.message(RegistrationState.waiting_for_password, F.text)
async def process_password(
    message: types.Message,
    state: FSMContext,
    reg_client: ApiRegistrationClient,
    auth_client: ApiAuthClient,  # Берем клиент авторизации для немедленной привязки
):
    password = message.text.strip()

    with contextlib.suppress(Exception):
        await message.delete()

    if len(password) < 3:
        await message.answer("⚠️ Пароль слишком короткий. Придумай пароль от 3 символов:")
        return

    await message.answer("⏳ Создаю учетную запись...")

    user_data = await state.get_data()
    payload = UserRegister(
        email=user_data["email"],
        name=user_data["name"],
        password=password,
        repeat_password=password,
        register_code=user_data["register_code"],
    )

    # Стучимся на регистрацию
    status_code, response_data = await reg_client.register_new_user(payload)

    if status_code == 201:
        await message.answer("✅ Учетная запись успешно создана! Выполняю привязку к Telegram...")

        # Немедленно склеиваем аккаунты
        access_token, refresh_token = await auth_client.link_telegram_account(email=payload.email, password=password)

        await state.clear()

        if access_token:
            await state.update_data(access_token=access_token, refresh_token=refresh_token)
            await message.answer(
                text="🎉 Регистрация завершена! Вы авторизованы в системе.",
                reply_markup=get_main_keyboard(BaseActions.logout, AdminActions.make_reg_code),
            )
        else:
            await message.answer(
                text="⚠️ Аккаунт создан, но привязка Telegram не удалась. Нажми /start для входа.",
                reply_markup=get_main_keyboard(BaseActions.start),
            )

    elif status_code == 400:
        error_msg = response_data.get("detail") if response_data else "Ошибка валидации"
        await message.answer(
            text=f"❌ Ошибка: {error_msg}\nПопробуй ввести другой email.",
            reply_markup=get_main_keyboard(BaseActions.cancel),
        )
        await state.set_state(RegistrationState.waiting_for_email)

    else:
        logger.error(f"Неизвестная ошибка при регистрации: {status_code} - {response_data}")
        await state.clear()
        await message.answer(
            text="🛠 Произошла ошибка на сервере. Попробуй позже.", reply_markup=get_main_keyboard(BaseActions.start)
        )

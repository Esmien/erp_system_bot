from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.services.api_client import attempt_telegram_login

# from bot.states.auth import AuthState

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    # Визуальный отклик, что бот не завис, так как запрос к API может занять время
    await message.answer("Проверяю учетную запись ERP...")

    # Стучимся на наш бэкенд
    token = await attempt_telegram_login(tg_id=message.from_user.id)

    if token:
        # Юзер уже привязан к системе
        await state.update_data(access_token=token)
        await message.answer("Вы успешно авторизованы в системе.")
    else:
        # Юзера нет, нужно запрашивать email
        await message.answer(
            f"Привет, {message.from_user.first_name}!\n"
            f"Ты еще не авторизован в системе.\n\n"
            f"Отправь свой email от ERP System:"
        )
        # await state.set_state(AuthState.waiting_for_email)

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.keyboards.reply_keyboard import AdminActions, BaseActions, get_main_keyboard
from bot.services.api_client import get_registration_code

router = Router()


@router.message(Command("make_reg_code"))
@router.message(F.text == AdminActions.make_reg_code)
async def make_reg_code(message: types.Message, state: FSMContext):
    """Хэндлер для генерации кода регистрации"""
    data = await state.get_data()
    token: str | None = data.get("access_token")

    if not token:
        await message.answer("Сначала необходимо авторизоваться в системе.")
        return

    status_code, register_code = await get_registration_code(token=token)

    statuses = {
        201: "✅ <b>Код регистрации успешно создан!</b>\n\n"
        f"<code>{register_code}</code>\n\n"
        "⏳ <i>Код одноразовый и действителен 24 часа. Отправьте его новому сотруднику.</i>",
        401: "⚠️ Ваша сессия истекла. Пожалуйста, авторизуйтесь заново.",
        403: "❌ У вас недостаточно прав для генерации инвайт-кодов.",
    }

    if not status_code:
        await message.answer(
            text="Проблемы на сервере, попробуйте позже", reply_markup=get_main_keyboard(BaseActions.start)
        )

    if status_code in statuses:
        await message.answer(statuses.get(status_code))

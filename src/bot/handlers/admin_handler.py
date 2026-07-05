from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.api_clients.api_registration_client import ApiRegistrationClient
from bot.keyboards.inline_keyboard import RoleCallback, get_roles_inline_keyboard
from bot.keyboards.reply_keyboard import AdminActions
from bot.services.admin_service import AdminService
from bot.views.admin_view import AdminRenderer as renderer

router = Router()


@router.message(Command("make_reg_code"))
@router.message(F.text == AdminActions.make_reg_code)
async def cmd_make_reg_code(message: types.Message, state: FSMContext, reg_client: ApiRegistrationClient):
    """Хэндлер для запроса списка ролей"""
    data = await state.get_data()
    token: str | None = data.get("access_token")

    if not token:
        await message.answer(text=renderer.auth_required_msg)
        return

    admin_service = AdminService(reg_client=reg_client)
    roles = await admin_service.get_roles(token=token)

    if not roles:
        await message.answer(text=renderer.roles_not_found_msg)
        return

    keyboard = get_roles_inline_keyboard(roles=roles)
    await message.answer(text=renderer.select_role_msg, reply_markup=keyboard)


@router.callback_query(RoleCallback.filter())
async def process_select_role_for_code(
    callback: types.CallbackQuery,
    callback_data: RoleCallback,
    state: FSMContext,
    reg_client: ApiRegistrationClient,
):
    """Шаг 2: Генерируем код с выбранной ролью через сервис"""
    await callback.answer()

    data = await state.get_data()
    token: str | None = data.get("access_token")

    if not token:
        await callback.message.answer(text=renderer.session_expired_msg)
        return

    # Передаем сервису только чистые строки (токен и имя роли)
    admin_service = AdminService(reg_client=reg_client)
    result = await admin_service.generate_invite_code(token=token, role_name=callback_data.name)

    # Роутинг UI на основе семантического ответа сервиса
    if result.is_success:
        role = callback_data.name.capitalize()
        text = renderer.succeed_generated_code(role=role, code=result.code)
        await callback.message.edit_text(text=text)

    elif result.is_forbidden:
        await callback.message.edit_text(text=renderer.access_denied_msg)

    else:
        await callback.message.edit_text(text=renderer.server_error_msg)

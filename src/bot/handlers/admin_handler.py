from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.api_clients.api_registration_client import ApiRegistrationClient
from bot.keyboards.inline_keyboard import RoleCallback, get_roles_inline_keyboard
from bot.keyboards.reply_keyboard import AdminActions
from bot.schemas.user_schemas import RoleDTO
from bot.views.admin_view import AdminRenderer as renderer

router = Router()


@router.message(Command("make_reg_code"))
@router.message(F.text == AdminActions.make_reg_code)
async def cmd_make_reg_code(message: types.Message, state: FSMContext, reg_client: ApiRegistrationClient):
    """Хэндлер для генерации кода регистрации"""
    data = await state.get_data()
    token: str | None = data.get("access_token")

    if not token:
        await message.answer(text=renderer.auth_required_msg)
        return

    roles = await reg_client.get_roles(token=token)

    if not roles:
        await message.answer(text=renderer.roles_not_found_msg)
        return

    keyboard = get_roles_inline_keyboard(roles=roles)

    await message.answer(text=renderer.select_role_msg, reply_markup=keyboard)


@router.callback_query(RoleCallback.filter())
async def process_select_role_for_code(
    callback: types.CallbackQuery,
    callback_data: RoleCallback,  # Сюда магически прилетит распакованный payload кнопки
    state: FSMContext,
    reg_client: ApiRegistrationClient,
):
    """Шаг 2: Генерируем код с выбранной ролью"""
    # Обязательно "гасим" часики на нажатой кнопке, чтобы ТГ не ругался
    await callback.answer()

    data = await state.get_data()
    token: str | None = data.get("access_token")

    if not token:
        await callback.message.answer(text=renderer.session_expired_msg)
        return

    # Оборачиваем системное имя роли из кнопки в нашу DTO-схему
    role_dto = RoleDTO(name=callback_data.name)

    # Запрашиваем код
    status_code, register_code = await reg_client.get_registration_code(token=token, role_name=role_dto)

    if status_code == 201:
        role = callback_data.name.capitalize()
        text = renderer.succeed_generated_code(role=role, code=register_code)
        # Редактируем сообщение с кнопками, заменяя его на итоговый текст
        await callback.message.edit_text(text=text)

    elif status_code == 403:
        await callback.message.edit_text(text=renderer.access_denied_msg)
    else:
        await callback.message.edit_text(text=renderer.server_error_msg)

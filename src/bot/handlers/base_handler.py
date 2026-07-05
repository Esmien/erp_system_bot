import contextlib

from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from bot.api_clients.api_auth_client import ApiAuthClient
from bot.api_clients.api_user_client import ApiUserClient
from bot.core.utils.chat_cleaner import clean_chat_history
from bot.keyboards.inline_keyboard import select_action
from bot.keyboards.reply_keyboard import BaseActions, get_main_keyboard, remove_keyboard
from bot.services.auth_service import AuthService
from bot.views.base_view import BaseRenderer as renderer

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, auth_client: ApiAuthClient, user_client: ApiUserClient):
    """
    Точка входа. Управляет UI на основе ответа от AuthService.
    """
    await clean_chat_history(message=message, state=state)

    with contextlib.suppress(Exception):
        await message.delete()

    data = await state.get_data()
    access_token = data.get("access_token")

    # Если токена нет, очищаем стейт и показываем "часики", так как сервис пойдет на бэк
    wait_msg = None
    if not access_token:
        await state.clear()
        wait_msg = await message.answer(text=renderer.waiting_for_check_account_msg, reply_markup=remove_keyboard())

    # 1. Инициализируем сервис и отдаем ему бизнес-логику
    # (в будущем инстанс сервиса тоже можно будет инжектить через мидлварь)
    auth_service = AuthService(auth_client=auth_client, user_client=user_client)

    result = await auth_service.resolve_start_auth(access_token=access_token, current_role=data.get("role"))

    # Убираем часики
    if wait_msg:
        with contextlib.suppress(Exception):
            await wait_msg.delete()

    # 2. Роутинг UI на основе результата
    if result.is_auth:
        # Если сервис выдал новые токены (произошел тихий логин), обновляем FSM
        if result.is_new_login:
            await state.update_data(access_token=result.access_token, refresh_token=result.refresh_token)
            text = renderer.succeed_auth_msg
        else:
            text = renderer.already_auth_msg

        # Всегда обновляем роль в памяти (на случай, если она подтянулась заново)
        await state.update_data(role=result.role)

        msg = await message.answer(
            text=text,
            reply_markup=get_main_keyboard(is_auth=True, role=result.role),
        )
        await state.update_data(last_bot_msg_id=msg.message_id)

    else:
        # Гость
        msg = await message.answer(
            text=renderer.welcome_msg(message=message),
            reply_markup=select_action(),
        )
        # Сносим нижнюю клавиатуру костылем
        cleaner_msg = await message.answer("...", reply_markup=remove_keyboard())
        await cleaner_msg.delete()

        await state.update_data(last_bot_msg_id=msg.message_id)


@router.message(Command("cancel"))
@router.message(F.text == BaseActions.cancel)
async def cmd_cancel(message: types.Message, state: FSMContext, auth_client: ApiAuthClient, user_client: ApiUserClient):
    """Сброс состояния и возврат в главное меню."""
    await clean_chat_history(message=message, state=state)
    await state.clear()

    # Прокидываем оба клиента в старт
    await cmd_start(message=message, state=state, auth_client=auth_client, user_client=user_client)

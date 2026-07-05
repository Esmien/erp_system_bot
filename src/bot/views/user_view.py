from bot.schemas.user_schemas import UserRead


class UserRenderer:
    session_expired_msg = "⚠️ Сессия не найдена. Пожалуйста, авторизуйтесь заново (/start)."
    profile_loading_msg = "⏳ Загружаю профиль..."
    loading_error_msg = "❌ Ошибка получения данных. Возможно, сессия истекла. Нажми /start"

    @classmethod
    def render_profile_text(cls, user: UserRead) -> str:
        """
        Занимается текстовым представлением данных пользователя
        """
        status = "🟢 Активен" if user.is_active else "🔴 Деактивирован"
        role = user.role.name.capitalize()

        full_name_parts = [user.last_name, user.name, user.surname]
        full_name = " ".join(part for part in full_name_parts if part)

        return (
            f"👤 <b>Ваш профиль ({role})</b>\n\n"
            f"<b>ФИО:</b> {full_name}\n"
            f"<b>Email:</b> <code>{user.email}</code>\n"
            f"<b>Статус:</b> {status}\n\n"
            f"<i>ID: {user.id} | TG: {user.tg_id}</i>"
        )

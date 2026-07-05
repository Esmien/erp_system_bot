class AdminRenderer:
    auth_required_msg = "Сначала необходимо авторизоваться в системе."
    roles_not_found_msg = "Не удалось получить список ролей. Попробуй позже."
    select_role_msg = "Выбери роль для нового инвайт-кода:"
    session_expired_msg = "Сессия истекла. Пожалуйста, авторизуйтесь заново."
    access_denied_msg = "❌ У вас недостаточно прав для генерации инвайт-кодов."
    server_error_msg = "🛠 Проблемы на сервере, попробуйте позже."

    @classmethod
    def succeed_generated_code(cls, role: str, code: str | None):
        return (
            f"✅ <b>Код регистрации успешно создан!</b>\n\n"
            f"Назначенная роль: <b>{role}</b>\n"
            f"<code>{code}</code>\n\n"
            f"⏳ <i>Код одноразовый и действителен 24 часа. Отправьте его новому сотруднику.</i>"
        )

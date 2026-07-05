class AuthRenderer:
    welcome_auth_msg = "🔐 <b>Авторизация</b>\n------------------------------\n\n📧 Отправь свой рабочий email:"
    waiting_for_password_msg = "🔑 Введи пароль:"
    wrong_email_format_msg = "С почтой что-то не так. Отправь свой email повторно:"
    wrong_password_format_msg = "Пароль должен быть текстом. Попробуй еще раз:"
    waiting_for_linked_telegram_msg = "⏳ Выполняю привязку аккаунта..."
    succeed_link_telegram_msg = "✅ Учетная запись успешно привязана! Добро пожаловать."
    bad_credentials_msg = (
        "❌ Ошибка авторизации. Неверный email или пароль.\nДавай попробуем еще раз. Отправь свой email:"  # noqa: E501
    )
    succeed_unlinked_telegram_msg = "Учетная запись отвязана. Для новой авторизации нажми /start"
    unlinked_with_error_msg = "Выход выполнен локально, но сервер не ответил. Связь будет разорвана позже"

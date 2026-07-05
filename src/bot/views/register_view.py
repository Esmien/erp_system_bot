class RegisterRenderer:
    waiting_for_register_code_msg = (
        "📝 <b>Регистрация</b>\n\nВведи 6-значный одноразовый инвайт-код, выданный администратором:"  # noqa: E501
    )
    invalid_register_code_msg = "❌ Код недействителен или уже использован. Запроси новый у админа:"
    waiting_for_email_msg = "Отлично. Код принят!\nТеперь отправь свой рабочий email:"
    wrong_email_format_msg = "⚠️ Это не похоже на email. Попробуй еще раз:"
    waiting_for_last_name_msg = "Фамилия:"
    waiting_for_name_msg = "Имя:"
    waiting_for_surname_msg = "Отчество:"
    waiting_for_password_msg = "Осталось придумать пароль (минимум 3 символа):"
    to_short_password_msg = "⚠️ Пароль слишком короткий. Придумай пароль от 3 символов:"
    waiting_for_repeat_password_msg = "Повтори пароль:"
    missmatch_password_msg = "❌ Пароли не совпадают, попробуй еще раз (введи новый пароль):"
    register_in_progress_msg = "⏳ Создаю учетную запись..."
    waiting_for_telegram_link_msg = "✅ Учетная запись успешно создана! Выполняю привязку к Telegram..."
    register_succeed_msg = "🎉 Регистрация завершена! Вы авторизованы в системе."
    fail_for_link_telegram_msg = "⚠️ Аккаунт создан, но привязка Telegram не удалась. Нажми /start для входа."

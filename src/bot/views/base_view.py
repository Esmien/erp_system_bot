class BaseRenderer:
    already_auth_msg = "Вы уже авторизованы в системе."
    waiting_for_check_account_msg = "Проверяю учетную запись ERP..."
    succeed_auth_msg = "Вы успешно авторизованы в системе."

    @classmethod
    def welcome_msg(cls, message):
        return f"Привет, {message.from_user.first_name}!\nТы еще не авторизован в системе.\n\nВыбери действие:"

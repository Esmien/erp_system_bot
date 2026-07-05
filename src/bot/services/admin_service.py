from dataclasses import dataclass

from bot.api_clients.api_registration_client import ApiRegistrationClient
from bot.schemas.user_schemas import RoleDTO


@dataclass
class GenerateCodeResult:
    """Объект результата генерации инвайт-кода"""

    is_success: bool
    code: str | None = None
    is_forbidden: bool = False
    is_server_error: bool = False


class AdminService:
    def __init__(self, reg_client: ApiRegistrationClient):
        self.reg_client = reg_client

    async def get_roles(self, token: str) -> list[dict] | None:
        """Проксируем запрос ролей (пока здесь нет сложной логики)"""
        return await self.reg_client.get_roles(token=token)

    async def generate_invite_code(self, token: str, role_name: str) -> GenerateCodeResult:
        """
        Бизнес-логика создания кода.
        Инкапсулирует работу с DTO и HTTP-статусами.
        """
        # Собираем DTO там, где оно должно собираться — в слое логики
        role_dto = RoleDTO(name=role_name)

        status_code, register_code = await self.reg_client.get_registration_code(token=token, role_name=role_dto)

        if status_code == 201:
            return GenerateCodeResult(is_success=True, code=register_code)
        elif status_code == 403:
            return GenerateCodeResult(is_success=False, is_forbidden=True)
        else:
            return GenerateCodeResult(is_success=False, is_server_error=True)

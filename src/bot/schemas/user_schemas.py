from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class RoleBase(BaseModel):
    name: str


class RoleDTO(RoleBase):
    pass


class UserBase(BaseModel):
    """Схема с базовыми параметрами пользователя"""

    email: EmailStr = Field(..., examples=["user@example.com"])
    name: str = Field(..., examples=["Иван"])
    surname: str | None = Field(default=None, examples=["Иванович"])
    last_name: str | None = Field(default=None, examples=["Иванов"])


class UserLogin(BaseModel):
    """Схема для аутентификации пользователя"""

    username: EmailStr
    password: str
    tg_id: int


class RegisterCode(BaseModel):
    register_code: str = Field(
        ..., min_length=6, max_length=6, description="Одноразовый код для регистрации на платформе"
    )


class UserRead(UserBase):
    """Схема для возврата клиенту"""

    id: int
    tg_id: int
    is_active: bool
    role: RoleDTO
    team_id: int | None = Field(default=None)


class UserRegister(UserBase):
    """Схема с полями для регистрации и валидацией пароля"""

    password: str = Field(..., min_length=3, max_length=72, examples=["secret_password"])
    repeat_password: str = Field(..., min_length=3, max_length=72, examples=["secret_password"])
    register_code: str = Field(
        ..., min_length=6, max_length=6, description="Одноразовый код для регистрации на платформе"
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.password != self.repeat_password:
            raise ValueError("Пароли не совпадают!")
        return self


class UserUpdate(BaseModel):
    """Схема для обновления данных пользователя"""

    name: str | None = Field(default=None, examples=["Алексей"])
    surname: str | None = Field(default=None, examples=["Алексеевич"])
    last_name: str | None = Field(default=None, examples=["Алексеев"])
    tg_id: int | None = Field(default=None, examples=["123456789"])

    model_config = ConfigDict(extra="forbid")


class Token(BaseModel):
    """Схема модели JWT-токена"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str

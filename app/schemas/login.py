from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    user: str
    password: str

    @field_validator("user", mode="before")
    def strip(cls, user):
        if isinstance(user, str):
            user = user.strip()

        return user

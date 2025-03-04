from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    user_id: str
    password: str

    @field_validator("user_id", mode="before")
    def strip(cls, user_id):
        if isinstance(user_id, str):
            user_id = user_id.strip()

        return user_id

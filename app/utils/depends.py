from fastapi import HTTPException

from app.utils.settings import settings
from app.utils.variables import ROOT_ROLE


def delete_root_role(role: str):
    if role == ROOT_ROLE:
        raise HTTPException(status_code=403, detail="Root role cannot be deleted.")


def update_root_role(role: str):
    if role == ROOT_ROLE:
        raise HTTPException(status_code=403, detail="Root role cannot be updated.")


def delete_root_user(user: str):
    if user == settings.auth.root_user:
        raise HTTPException(status_code=403, detail="Root user cannot be deleted.")


def update_root_user(user: str):
    if user == settings.auth.root_user:
        raise HTTPException(status_code=403, detail="Root user cannot be updated.")


def delete_root_token(user: str):
    if user == settings.auth.root_key:
        raise HTTPException(status_code=403, detail="Root token cannot be deleted.")

import bcrypt
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--api_url", type=str, default="http://localhost:8080")
parser.add_argument("--master_key", type=str, default="changeme")
parser.add_argument("--first_username", type=str, default="me")
parser.add_argument("--first_password", type=str, default="changeme")
parser.add_argument("--playground_postgres_host", type=str, default="localhost")
parser.add_argument("--playground_postgres_port", type=int, default=5432)
parser.add_argument("--playground_postgres_password", type=str, default="changeme")


def get_hashed_password(password: str) -> str:
    return bcrypt.hashpw(password=password.encode(encoding="utf-8"), salt=bcrypt.gensalt()).decode(encoding="utf-8")


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


if __name__ == "__main__":
    args = parser.parse_args()

    headers = {"Authorization": f"Bearer {args.master_key}"}
    postgres_url = f"postgresql://postgres:{args.playground_postgres_password}@{args.playground_postgres_host}:{args.playground_postgres_port}/playground"  # fmt: off

    #  Get models list
    response = requests.get(f"{args.api_url}/v1/models", headers=headers)
    assert response.status_code == 200, response.text
    models = response.json()["data"]
    models = [model["id"] for model in models]

    # Create a new admin role
    limits = []
    for model in models:
        limits.append({"model": model, "type": "rpm", "value": None})
        limits.append({"model": model, "type": "rpd", "value": None})
        limits.append({"model": model, "type": "tpm", "value": None})
        limits.append({"model": model, "type": "tpd", "value": None})

    limits.append({"model": "web-search", "type": "rpm", "value": None})
    limits.append({"model": "web-search", "type": "rpd", "value": None})
    limits.append({"model": "web-search", "type": "tpm", "value": None})
    limits.append({"model": "web-search", "type": "tpd", "value": None})

    response = requests.post(
        url=f"{args.api_url}/roles",
        headers=headers,
        json={
            "name": "admin",
            "permissions": [
                "create_role",
                "read_role",
                "update_role",
                "delete_role",
                "create_user",
                "read_user",
                "update_user",
                "delete_user",
                "create_public_collection",
                "read_metric",
            ],
            "limits": limits,
        },
    )
    assert response.status_code == 201, response.text

    role_id = response.json()["id"]

    # Create a new admin user
    response = requests.post(url=f"{args.api_url}/users", headers=headers, json={"name": "admin", "role": role_id})
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]

    # Create a new token for the admin user
    response = requests.post(url=f"{args.api_url}/tokens", headers=headers, json={"name": "admin", "user": user_id})
    assert response.status_code == 201, response.text

    api_key = response.json()["token"]
    api_key_id = response.json()["id"]

    print(f"""
New user created:
- Username: {args.first_username}
- Password: {args.first_password}
- API key: {api_key}
""")

    # Create playground account for the admin user
    engine = create_engine(url=postgres_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = next(get_session())
    session.execute(
        text("""
            INSERT INTO "user" (name, password, api_user_id, api_role_id, api_key_id, api_key, created_at, updated_at)
            VALUES (:name, :password, :api_user_id, :api_role_id, :api_key_id, :api_key, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {
            "name": args.first_username,
            "password": get_hashed_password(password=args.first_password),
            "api_user_id": user_id,
            "api_role_id": role_id,
            "api_key_id": api_key_id,
            "api_key": api_key,
        },
    )
    session.commit()

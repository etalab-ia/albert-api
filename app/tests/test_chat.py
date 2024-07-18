from fastapi.testclient import TestClient

from app.main import app

model = "AgentPublic/llama3-instruct-8b"
prompt = "Hello world !"
user = "pytest"

def test_chat_completions():
    with TestClient(app) as client:

        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "user": user,
            "stream": False,
        }
        response = client.post("/v1/chat/completions", json=data)
        assert response.status_code == 200


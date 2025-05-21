import json
from types import SimpleNamespace

from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS

class LLMClient:
    def __init__(self):
        pass
    async def post_on_llm_model(self, body):
        from app.utils.lifespan import context
        model = context.models(model=body.model)
        client = model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
        http_llm_response = await client.forward_request(method="POST", json=body.model_dump())
        return json.loads(http_llm_response.text, object_hook=lambda d: SimpleNamespace(**d))
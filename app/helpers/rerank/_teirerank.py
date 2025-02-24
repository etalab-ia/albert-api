from typing import List
from urllib.parse import urljoin

import httpx

from app.schemas.rerank import Rerank
from app.utils.variables import ENDPOINT__RERANK


class TEIRerank:
    def __init__(self, client=None) -> None:
        self.client = client

    async def create(self, prompt: str, input: list[str], model: str) -> List[Rerank]:
        json = {"query": prompt, "texts": input}
        url = urljoin(base=str(self.client.api_url), url=self.client.ENDPOINT_TABLE[ENDPOINT__RERANK])
        headers = {"Authorization": f"Bearer {self.client.api_key}"}

        async with httpx.AsyncClient() as async_client:
            response = await async_client.post(url=url, headers=headers, json=json, timeout=self.client.timeout)
            response.raise_for_status()
            data = response.json()
            data = [Rerank(**item) for item in data]

        return data

from abc import ABC
import ast
import importlib
from json import dumps, loads
from typing import Literal, Optional, Type
from urllib.parse import urljoin

from fastapi import HTTPException
import httpx

from app.utils.variables import (
    MODEL_CLIENT_TYPE__OPENAI,
    MODEL_CLIENT_TYPE__TEI,
    MODEL_CLIENT_TYPE__VLLM,
)


class BaseModelClient(ABC):
    @staticmethod
    def import_constructor(type: Literal[MODEL_CLIENT_TYPE__OPENAI, MODEL_CLIENT_TYPE__VLLM, MODEL_CLIENT_TYPE__TEI]) -> "Type[BaseModelClient]":
        module = importlib.import_module(f"app.clients.model._{type}modelclient")
        return getattr(module, f"{type.capitalize()}ModelClient")

    def _format_request(self, endpoint: str, json: Optional[dict] = None, files: Optional[dict] = None, data: Optional[dict] = None) -> dict:
        url = urljoin(base=str(self.base_url), url=self.ENDPOINT_TABLE[endpoint])
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if json and "model" in json:
            json["model"] = self.model

        return url, headers, json, files, data

    async def forward_request(
        self,
        endpoint: str,
        method: str,
        json: Optional[dict] = None,
        files: Optional[dict] = None,
        data: Optional[dict] = None,
        additional_data_value: Optional[list] = None,
        additional_data_key: Optional[str] = None,
    ) -> httpx.Response:
        """
        Forward a request to a client model and add additional data to the response if provided.

        Args:
            endpoint(str): The endpoint to forward the request to.
            method(str): The method to use for the request.
            json(dict): The JSON body to use for the request.
            files(dict): The files to use for the request.
            data(dict): The data to use for the request.
            additional_data_value(list): The value to add to the response.
            additional_data_key(str): The key to add the value to.

        Returns:
            httpx.Response: The response from the API.
        """

        url, headers, json, files, data = self._format_request(endpoint=endpoint, json=json, files=files, data=data)

        async with httpx.AsyncClient(timeout=self.timeout) as async_client:
            try:
                response = await async_client.request(method=method, url=url, headers=headers, json=json, files=files, data=data)
            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                raise HTTPException(status_code=504, detail="Request timed out, model is too busy.")
            except Exception as e:
                raise HTTPException(status_code=500, detail=type(e).__name__)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError:
                message = loads(response.text)

                # format error message
                if "message" in message:
                    try:
                        message = ast.literal_eval(message["message"])
                    except Exception:
                        message = message["message"]
                raise HTTPException(status_code=response.status_code, detail=message)

        # add additional data to the response
        if additional_data_value and additional_data_key:
            data = response.json()
            data[additional_data_key] = additional_data_value
            response = httpx.Response(status_code=response.status_code, content=dumps(data))

        return response

    async def forward_stream(
        self,
        endpoint: str,
        method: str,
        json: Optional[dict] = None,
        files: Optional[dict] = None,
        data: Optional[dict] = None,
        additional_data_value: Optional[list] = None,
        additional_data_key: Optional[str] = None,
    ):
        """
        Forward a stream request to a client model and add additional data to the response if provided.

        Args:
            endpoint(str): The endpoint to forward the request to.
            method(str): The method to use for the request.
            json(dict): The JSON body to use for the request.
            files(dict): The files to use for the request.
            data(dict): The data to use for the request.
            additional_data_value(list): The value to add to the response (only on the first chunk).
            additional_data_key(str): The key to add the value to (only on the first chunk).
        """

        url, headers, json, files, data = self._format_request(endpoint=endpoint, json=json, files=files, data=data)

        async with httpx.AsyncClient(timeout=self.timeout) as async_client:
            try:
                async with async_client.stream(method=method, url=url, headers=headers, json=json, files=files, data=data) as response:
                    first_chunk = True
                    async for chunk in response.aiter_raw():
                        # format error message
                        if response.status_code // 100 != 2:
                            chunks = loads(chunk.decode(encoding="utf-8"))
                            if "message" in chunks:
                                try:
                                    chunks["message"] = ast.literal_eval(chunks["message"])
                                except Exception:
                                    pass
                            chunk = dumps(chunks).encode(encoding="utf-8")

                        # add additional data to the first chunk
                        elif first_chunk and additional_data_value and additional_data_key:
                            chunks = chunk.decode(encoding="utf-8").split(sep="\n\n")
                            chunk = loads(chunks[0].lstrip("data: "))
                            chunk[additional_data_key] = additional_data_value
                            chunks[0] = f"data: {dumps(chunk)}"
                            chunk = "\n\n".join(chunks).encode(encoding="utf-8")

                        first_chunk = False
                        yield chunk, response.status_code

            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                yield dumps({"detail": "Request timed out, model is not available."}).encode(), 504
            except Exception as e:
                yield dumps({"detail": type(e).__name__}).encode(), 500

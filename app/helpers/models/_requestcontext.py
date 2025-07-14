import asyncio
from typing import Callable, Union, Awaitable

from app.clients.model import BaseModelClient
import inspect


class RequestContext:
    def __init__[R](
        self,
        handler: Callable[[BaseModelClient], Union[R, Awaitable[R]]],
    ):
        self.handler = handler

        self.loop = asyncio.get_running_loop()  # get the loop the RequestContext was created in
        self.future = self.loop.create_future()

    def _get_callback(self, client: BaseModelClient):
        """
        Returns a synchronous callback, and adapts when the handler is async.
        """
        if inspect.iscoroutinefunction(self.handler):
            def _shim():
                async def _run_and_set_async():
                    try:
                        result = await self.handler(client)
                        self.future.set_result(result)
                    except Exception as exc:
                        self.future.set_exception(exc)

                # schedule the coroutine on the same loop
                self.loop.create_task(_run_and_set_async())

            return _shim

        def _run_and_set():
            try:
                result = self.handler(client)
                self.future.set_result(result)
            except Exception as exc:
                self.future.set_exception(exc)

        return _run_and_set


    def complete(self, client: BaseModelClient):
        if self.loop.is_closed():
            return

        self.loop.call_soon_threadsafe(self._get_callback(client))



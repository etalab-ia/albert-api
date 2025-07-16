import asyncio
import inspect

from uuid import uuid4

from typing import Callable, Union, Awaitable, TYPE_CHECKING

if TYPE_CHECKING:
    # only for type‐checkers and linters, not at runtime
    # Used to break circular import
    from app.clients.model import BaseModelClient


class WorkingContext:
    def __init__[R](
        self,
        endpoint: str,
        handler: Callable[["BaseModelClient"], Union[R, Awaitable[R]]],
    ):
        self.handler = handler
        self.endpoint = endpoint

        self.id = str(uuid4())

        self.loop = asyncio.get_running_loop()  # get the loop the RequestContext was created in
        self.result = self.loop.create_future()

    def _get_callback(self, client: "BaseModelClient"):
        """
        Returns a synchronous callback, and adapts when the handler is async.
        """
        if inspect.iscoroutinefunction(self.handler):
            def _shim():
                async def _run_and_set_async():
                    try:
                        result = await self.handler(client)
                        self.result.set_result(result)
                    except Exception as exc:
                        self.result.set_exception(exc)

                # schedule the coroutine on the same loop
                self.loop.create_task(_run_and_set_async())

            return _shim

        def _run_and_set():
            try:
                result = self.handler(client)
                self.result.set_result(result)
            except Exception as exc:
                self.result.set_exception(exc)

        return _run_and_set


    def complete(self, client: "BaseModelClient"):
        if self.loop.is_closed():
            return

        self.loop.call_soon_threadsafe(self._get_callback(client))

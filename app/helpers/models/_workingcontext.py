import asyncio
import inspect

from uuid import uuid4

from typing import Callable, Union, Awaitable, TYPE_CHECKING

if TYPE_CHECKING:
    # only for type‐checkers and linters, not at runtime
    # Used to break circular import
    from app.clients.model import BaseModelClient


class WorkingContext:
    """
    When RabbitMQ is enabled, the user request does not travel the API's layers in a classical way:
      the request is sent through the queue, and get caught by consumers, using callback architectures.
    It would be way too complex, rigid and inefficient to pass the request itself through RabbitMQ,  so it is
      represented as a unique uuid4. But once the request is about to get executed, the API needs its actual content
      and context, specifically the handler the user gave.
    To reconcile both sides (a simple message vs a complex and abstract request), the user adds its handler and
      its (thread) context to a register, managed by the objects that, on the other hand, consume a queue
      (ModelRouter and ModelClient). This way, when the consumer callback is called, it gets request content
      through this inner register.

    This class gathers both the context and the content of the user's request.
    """

    def __init__[R](
        self,
        endpoint: str,
        handler: Callable[["BaseModelClient"], Union[R, Awaitable[R]]],
    ):
        self.handler = handler
        self.endpoint = endpoint

        self.id = str(uuid4())

        self.loop = asyncio.get_running_loop()  # get the loop the WorkingContext was created in
        self.result = self.loop.create_future()

    def _get_callback(self, client: "BaseModelClient"):
        """
        Returns a synchronous callback that executes the handler and sets its result.
            It adapts when the handler is async.
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
        """
        Completes the request, ie executes the handler, in the right thread.
        """
        if self.loop.is_closed():
            return

        self.loop.call_soon_threadsafe(self._get_callback(client))

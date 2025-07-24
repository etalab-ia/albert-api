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

    async def work[R](self, client: "BaseModelClient") -> R | Exception:
        """
        Actually executes the user request.

        Args:
            client(BaseModelClient): the client to send to heavy work to.

        Returns:
            Either the result of the handler, or an Exception, if one is raised.
        """
        try:
            if inspect.iscoroutinefunction(self.handler):
                return await self.handler(client)

            return self.handler(client)
        except Exception as e:
            return e

    def send_result[R](self, result: R | Exception):
        """
        Sets a result or an exception to the promise, within the right event loop.

        Args:
            result(R | Exception): Either the wished result, or an exception, if something went wrong.
        """
        if isinstance(result, Exception):
            def _set():
                self.result.set_exception(result)
        else:
            def _set():
                self.result.set_result(result)

        self.loop.call_soon_threadsafe(_set)


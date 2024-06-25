import time
from typing import Optional

from redis import Redis


class RedisChatHistory(Redis):
    """
    RedisChatHistory is a class that manages chat history in Redis.

    Args:
        client (Redis): Redis client instance

    Methods:
        add_messages: Add messages to chat history
        get_chat_history: Get chat history from Redis
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize Redis client.
        """

        super().__init__(*args, **kwargs)

    def add_messages(
        self, user_id: str, chat_id: str, user_message: dict, assistant_message: dict
    ) -> None:
        """
        Add messages to chat history.

        Args:
            user_id (str): User ID
            chat_id (Optional[str]): Chat ID (default: None)
            user_message (dict): User message
            assistant_message (dict): Assistant message
        """
        if self.exists(user_id):
            if self.json().get(user_id, f"$.{chat_id}"):
                self.json().arrappend(user_id, f"$.{chat_id}.messages", user_message)
                self.json().arrappend(user_id, f"$.{chat_id}.messages", assistant_message)
            else:
                self.json().set(user_id, f"$.{chat_id}", {})
                self.json().set(
                    user_id, f"$.{chat_id}.messages", [user_message, assistant_message]
                )
                self.json().set(user_id, f"$.{chat_id}.created", round(time.time()))
        else:
            self.json().set(
                user_id,
                "$",
                {
                    chat_id: {
                        "messages": [user_message, assistant_message],
                        "created": round(time.time()),
                    }
                },
            )

    def get_chat_history(self, user_id: str, chat_id: Optional[str] = None) -> dict:
        """
        Get chat history from Redis.

        Args:
            user_id (str): User ID
            chat_id (Optional[str]): Chat ID (default: None)

        Returns:
            chat_history (dict): Chat history for the user_id
        """
        if self.exists(user_id):
            if chat_id:
                chat_history = self.json().get(user_id, f".{chat_id}")
            else:
                chat_history = self.json().get(user_id) 
        else:
            chat_history = {}

        return chat_history

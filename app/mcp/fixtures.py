from copy import deepcopy

DEFAULT_LLM_RESPONSE = {
    "id": "chatcmpl-9361ad51d8f04a46a6bb83ea54d2f25c",
    "choices": [{
        "finish_reason": "stop",
        "index": 0,
        "logprobs": None,
        "message": {
            "content": "Salut, je suis albert-API",
            "refusal": None,
            "role": "",
            "audio": None,
            "function_call": None,
            "tool_calls": [],
            "reasoning_content": None
        },
        "stop_reason": None
    }],
    "created": 1747410275,
    "model": "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
    "object": "chat.completion",
    "service_tier": None,
    "system_fingerprint": None,
    "usage": {
        "completion_tokens": 36,
        "prompt_tokens": 241,
        "total_tokens": 277,
        "completion_tokens_details": None,
        "prompt_tokens_details": None
    },
    "search_results": [],
    "prompt_logprobs": None
}

DEFAULT_MCP_TOOLS = {
            "weather": {
                "_meta": None,
                "nextCursor": None,
                "tools": [{
                    "name": "get_alerts",
                    "description": "Get weather alerts for a US state.\n\n    Args:\n        state: Two-letter US state code (e.g. CA, NY)\n    ",
                    "inputSchema": {
                        "properties": {
                            "state": {
                                "title": "State",
                                "type": "string"
                            }
                        },
                        "required": ["state"],
                        "title": "get_alertsArguments",
                        "type": "object"
                    },
                    "annotations": None
                }, {
                    "name": "get_forecast",
                    "description": "Get weather forecast for a location.\n\n    Args:\n        latitude: Latitude of the location\n        longitude: Longitude of the location\n    ",
                    "inputSchema": {
                        "properties": {
                            "latitude": {
                                "title": "Latitude",
                                "type": "number"
                            },
                            "longitude": {
                                "title": "Longitude",
                                "type": "number"
                            }
                        },
                        "required": ["latitude", "longitude"],
                        "title": "get_forecastArguments",
                        "type": "object"
                    },
                    "annotations": None
                }]
            }
        }


def merge_with_defaults(user_data, default_data):
    if isinstance(default_data, dict):
        result = {}
        for key in default_data:
            if key in user_data:
                result[key] = merge_with_defaults(user_data[key], default_data[key])
            else:
                result[key] = deepcopy(default_data[key])
        return result
    elif isinstance(default_data, list) and default_data:
        if isinstance(user_data, list):
            return [merge_with_defaults(item, default_data[0]) for item in user_data]
        else:
            return deepcopy(default_data)
    else:
        return user_data if user_data is not None else deepcopy(default_data)

def generate_mocked_llm_response(**kwargs):
    return merge_with_defaults(kwargs, DEFAULT_LLM_RESPONSE)

def generate_mocked_mcp_bridge_tools(**kwargs):
    return merge_with_defaults(kwargs, DEFAULT_MCP_TOOLS)
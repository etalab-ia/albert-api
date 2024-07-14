import sys

from fastapi import APIRouter, Security

sys.path.append("..")
from schemas.tools import ToolResponse
from utils.security import check_api_key
from tools import *
from tools import __all__ as tools_list

router = APIRouter()


@router.get("/tools")
def tools(api_key: str = Security(check_api_key)) -> ToolResponse:
    """
    Get list a availables tools. Only RAG functions are currenty supported.
    """
    data = [
        {
            "id": globals()[tool].__name__,
            "description": globals()[tool].__doc__.strip(),
            "object": "tool",
        }
        for tool in tools_list
    ]
    response = {"object": "list", "data": data}

    return response

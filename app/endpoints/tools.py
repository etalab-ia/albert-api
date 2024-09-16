from app.schemas.tools import Tools
from app.tools import *
from app.tools import __all__ as tools_list
from app.utils.security import check_api_key
from fastapi import APIRouter, Security

router = APIRouter()


@router.get("/tools")
def tools(user: str = Security(check_api_key)) -> Tools:
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

    return Tools(**response)

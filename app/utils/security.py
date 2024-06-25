from typing import Annotated

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import CONFIG, logging

auth_scheme = HTTPBearer(scheme_name="API key")
API_KEYS = (
    [key["key"] for key in CONFIG["general"]["access"]] if CONFIG["general"]["access"] else []
)
logging.info(f"find {len(API_KEYS)} API keys in the configuration file.")

if API_KEYS:

    def check_api_key(api_key: Annotated[HTTPAuthorizationCredentials, Depends(auth_scheme)]):
        if api_key.scheme != "Bearer":
            raise HTTPException(status_code=403, detail="Invalid authentication scheme")
        if api_key.credentials not in API_KEYS:
            raise HTTPException(status_code=403, detail="Invalid API key")
else:

    def check_api_key():
        pass

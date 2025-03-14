import json
import traceback
from typing import Annotated, List

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.auth import PermissionType, User
from app.utils.exceptions import (
    CollectionNotFoundException,
    InsufficientRightsException,
    InvalidAPIKeyException,
    InvalidAuthenticationSchemeException,
    ModelNotFoundException,
)
from app.utils.logging import logger
from app.utils.variables import (
    COLLECTION_TYPE__PUBLIC,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__COLLECTIONS,
    ENDPOINT__DOCUMENTS,
    ENDPOINT__FILES,
    ROOT_ROLE,
)


class Authorization:
    def __init__(self, permissions: List[PermissionType] = []):
        self.permissions = permissions

    async def __call__(self, request: Request, api_key: Annotated[HTTPAuthorizationCredentials, Depends(dependency=HTTPBearer(scheme_name="API key"))]) -> User:  # fmt: off
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        from app.utils.lifespan import context

        user = await context.auth.check_token(token=api_key.credentials)

        if not user:
            raise InvalidAPIKeyException()

        if user.role == ROOT_ROLE:
            return user

        # permissions
        if self.permissions and not all(perm in user.permissions for perm in self.permissions):
            raise InsufficientRightsException()

        # POST
        if request.method == "POST":
            body = await request.body()
            body = json.loads(body) if body else {}

            # model
            if "model" in body and user.limits[body["model"]].rpd != 0 and user.limits[body["model"]].rpm != 0:
                raise ModelNotFoundException()  # the user doesn't see that they don't have the rights to access the model

            # limits
            if request.url.path.endswith(ENDPOINT__CHAT_COMPLETIONS):  # @TODO: extend to other models endpoints
                try:
                    await context.limiter(user=user, model=body["model"])
                except Exception:
                    logger.error(msg="Error during rate limit check.")
                    logger.error(msg=traceback.format_exc())

            # create public collection
            if request.url.path.endswith(ENDPOINT__COLLECTIONS) and request.method == "POST":
                if body["type"] == COLLECTION_TYPE__PUBLIC and PermissionType.CREATE_PUBLIC_COLLECTION not in user.permissions:
                    raise InsufficientRightsException()

            # create public document
            if request.url.path.endswith(ENDPOINT__FILES) and request.method == "POST":
                if body["type"] == COLLECTION_TYPE__PUBLIC and PermissionType.CREATE_PUBLIC_COLLECTION not in user.permissions:
                    raise InsufficientRightsException()

        # DELETE
        if request.method == "DELETE":
            # delete public collection
            if request.url.path.endswith(ENDPOINT__COLLECTIONS):
                collection_id = request.path_params["collection"]
                collections = await context.databases.search.get_collections(collection_ids=[collection_id])
                if not collections:
                    raise CollectionNotFoundException()
                if collections[0]["type"] == COLLECTION_TYPE__PUBLIC and PermissionType.DELETE_PUBLIC_COLLECTION not in user.permissions:
                    raise InsufficientRightsException()

            # delete public document
            # TODO change
            if request.url.path.endswith(ENDPOINT__DOCUMENTS):
                pass

        return user

from typing import Optional

from fastapi import HTTPException


# 400
class SearchMethodNotAvailableException(HTTPException):
    def __init__(self, detail: str = "Method not available."):
        super().__init__(status_code=400, detail=detail)


class WrongSearchMethodException(HTTPException):
    def __init__(self, detail: str = "Wrong search method."):
        super().__init__(status_code=400, detail=detail)


class WebSearchNotAvailableException(HTTPException):
    def __init__(self, detail: str = "Web search is not available."):
        super().__init__(status_code=400, detail=detail)


class MultiAgentsSearchNotAvailableException(HTTPException):
    def __init__(self, detail: str = "Multi agents search is not available."):
        super().__init__(status_code=400, detail=detail)


class RoleAlreadyExistsException(HTTPException):
    def __init__(self, detail: str = "Role already exists."):
        super().__init__(status_code=400, detail=detail)


class DeleteRoleWithUsersException(HTTPException):
    def __init__(self, detail: str = "Delete role with users is not allowed."):
        super().__init__(status_code=400, detail=detail)


class UserAlreadyExistsException(HTTPException):
    def __init__(self, detail: str = "User already exists."):
        super().__init__(status_code=400, detail=detail)


class InsufficientBudgetException(HTTPException):
    def __init__(self, detail: str = "Insufficient budget."):
        super().__init__(status_code=400, detail=detail)


# 403
class InvalidPasswordException(HTTPException):
    def __init__(self, detail: str = "Invalid password."):
        super().__init__(status_code=403, detail=detail)


class InvalidAuthenticationSchemeException(HTTPException):
    def __init__(self, detail: str = "Invalid authentication scheme.") -> None:
        super().__init__(status_code=403, detail=detail)


class InvalidAPIKeyException(HTTPException):
    def __init__(self, detail: str = "Invalid API key.") -> None:
        super().__init__(status_code=403, detail=detail)


class InsufficientPermissionException(HTTPException):
    def __init__(self, detail: str = "Insufficient rights.") -> None:
        super().__init__(status_code=403, detail=detail)


# 404
class CollectionNotFoundException(HTTPException):
    def __init__(self, detail: str = "Collection not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class DocumentNotFoundException(HTTPException):
    def __init__(self, detail: str = "Document not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class ChunkNotFoundException(HTTPException):
    def __init__(self, detail: str = "Chunk not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class ModelNotFoundException(HTTPException):
    def __init__(self, detail: str = "Model not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class RoleNotFoundException(HTTPException):
    def __init__(self, detail: str = "Role not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class TokenNotFoundException(HTTPException):
    def __init__(self, detail: str = "Token not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class UserNotFoundException(HTTPException):
    def __init__(self, detail: str = "User not found.") -> None:
        super().__init__(status_code=404, detail=detail)


# 413
class FileSizeLimitExceededException(HTTPException):
    MAX_CONTENT_SIZE = 20 * 1024 * 1024  # 20MB

    def __init__(self, detail: str = f"File size limit exceeded (max: {MAX_CONTENT_SIZE} bytes).") -> None:
        super().__init__(status_code=413, detail=detail)


# 422
class ParsingDocumentFailedException(HTTPException):
    def __init__(self, detail: str = "Parsing document failed.") -> None:
        super().__init__(status_code=422, detail=detail)


class ChunkingFailedException(HTTPException):
    def __init__(self, detail: str = "Chunking failed.") -> None:
        super().__init__(status_code=422, detail=detail)


class VectorizationFailedException(HTTPException):
    def __init__(self, detail: str = "Vectorization failed.") -> None:
        super().__init__(status_code=422, detail=detail)


class InvalidJSONFileFormatException(HTTPException):
    def __init__(self, detail: str = "Invalid JSON file format.") -> None:
        super().__init__(status_code=422, detail=detail)


class WrongModelTypeException(HTTPException):
    def __init__(self, detail: str = "Wrong model type.") -> None:
        super().__init__(status_code=422, detail=detail)


class MaxTokensExceededException(HTTPException):
    def __init__(self, detail: str = "Max tokens exceeded.") -> None:
        super().__init__(status_code=422, detail=detail)


class DifferentCollectionsModelsException(HTTPException):
    def __init__(self, detail: str = "Different collections models.") -> None:
        super().__init__(status_code=422, detail=detail)


class UnsupportedFileTypeException(HTTPException):
    def __init__(self, detail: str = "Unsupported file type.") -> None:
        super().__init__(status_code=422, detail=detail)


class NotImplementedException(HTTPException):
    def __init__(self, detail: str = "Not implemented.") -> None:
        super().__init__(status_code=400, detail=detail)


class UnsupportedFileUploadException(HTTPException):
    def __init__(self, detail: str = "Unsupported collection name for upload file.") -> None:
        super().__init__(status_code=422, detail=detail)


# 429
class RateLimitExceeded(HTTPException):
    """
    exception raised when a rate limit is hit.
    """

    limit = None

    def __init__(self, detail: Optional[str] = None) -> None:
        detail = f"Rate limit exceeded: {detail}" if detail else "Rate limit exceeded."
        super(RateLimitExceeded, self).__init__(status_code=429, detail=detail)

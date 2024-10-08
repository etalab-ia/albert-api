from fastapi import HTTPException


# 400
class ParsingFileFailedException(HTTPException):
    def __init__(self, detail: str = "Parsing file failed."):
        super().__init__(status_code=400, detail=detail)


class NoChunksToUpsertException(HTTPException):
    def __init__(self, detail: str = "No chunks to upsert."):
        super().__init__(status_code=400, detail=detail)


# 403
class InvalidAuthenticationSchemeException(HTTPException):
    def __init__(self, detail: str = "Invalid authentication scheme."):
        super().__init__(status_code=403, detail=detail)


class InvalidAPIKeyException(HTTPException):
    def __init__(self, detail: str = "Invalid API key."):
        super().__init__(status_code=403, detail=detail)


# 404
class CollectionNotFoundException(HTTPException):
    def __init__(self, detail: str = "Collection not found."):
        super().__init__(status_code=404, detail=detail)


class ModelNotFoundException(HTTPException):
    def __init__(self, detail: str = "Model not found."):
        super().__init__(status_code=404, detail=detail)


# 413
class ContextLengthExceededException(HTTPException):
    def __init__(self, detail: str = "Context length exceeded."):
        super().__init__(status_code=413, detail=detail)


class FileSizeLimitExceededException(HTTPException):
    def __init__(self, detail: str = "File size limit exceeded."):
        super().__init__(status_code=413, detail=detail)


# 422
class InvalidJSONFormatException(HTTPException):
    def __init__(self, detail: str = "Invalid JSON file format."):
        super().__init__(status_code=422, detail=detail)


class WrongModelTypeException(HTTPException):
    def __init__(self, detail: str = "Wrong model type."):
        super().__init__(status_code=422, detail=detail)


class MaxTokensExceededException(HTTPException):
    def __init__(self, detail: str = "Max tokens exceeded."):
        super().__init__(status_code=422, detail=detail)


class WrongCollectionTypeException(HTTPException):
    def __init__(self, detail: str = "Wrong collection type."):
        super().__init__(status_code=422, detail=detail)


class DifferentCollectionsModelsException(HTTPException):
    def __init__(self, detail: str = "Different collections models."):
        super().__init__(status_code=422, detail=detail)


class UnsupportedFileTypeException(HTTPException):
    def __init__(self, detail: str = "Unsupported file type."):
        super().__init__(status_code=422, detail=detail)

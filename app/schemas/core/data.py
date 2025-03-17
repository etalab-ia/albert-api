from pydantic import BaseModel


class Collection(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    model: str
    type: str
    created_at: int


class ParserOutputMetadata(BaseModel):
    collection_id: str
    document_id: str
    document_name: str
    document_created_at: int

    class Config:
        extra = "allow"


class ParserOutput(BaseModel):
    content: str
    metadata: ParserOutputMetadata

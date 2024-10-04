from pydantic import BaseModel


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

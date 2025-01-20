import json
import time
from typing import Dict, List, Optional
import uuid

from fastapi import UploadFile

from app.schemas.data import ParserOutput, ParserOutputMetadata
from app.schemas.files import JsonFile
from app.utils.exceptions import InvalidJSONFormatException

from ._baseparser import BaseParser


class JSONParser(BaseParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse(self, file: UploadFile, metadata: Optional[Dict]) -> List[ParserOutput]:
        """
        Parse a JSON file and converts it into a list of parsed outputs.

        Args:
            file (JsonFile): JSON file to be processed.

        Returns:
            List[ParserOutput]: List of parsed outputs.
        """

        file = json.loads(file.file.read())
        try:
            file = JsonFile(documents=file)
        except Exception as e:
            raise InvalidJSONFormatException(detail=f"Invalid JSON file format: {e}")

        output = list()
        created_at = round(time.time())
        for document in file.documents:
            content = self.clean(document.text)
            document_metadata = ParserOutputMetadata(
                collection_id=self.collection_id,
                document_id=str(uuid.uuid4()),
                document_name=document.title,
                document_created_at=created_at,
                **document.metadata,
                **metadata,
            )
            output.append(ParserOutput(content=content, metadata=document_metadata))

        return output

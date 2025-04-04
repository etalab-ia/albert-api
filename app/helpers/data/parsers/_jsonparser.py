import json
from typing import List

from fastapi import UploadFile

from app.schemas.core.data import ParserOutput

from ._baseparser import BaseParser


class JSONParser(BaseParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse(self, file: UploadFile) -> List[ParserOutput]:
        """
        Parse a JSON file and converts it into a list of parsed outputs.

        Args:
            file (JsonFile): JSON file to be processed.

        Returns:
            List[ParserOutput]: List of parsed outputs.
        """

        document = json.loads(file.file.read())
        content = self.clean(text=document["text"])
        metadata = document["metadata"]
        output = ParserOutput(contents=[content], metadata=metadata)

        return output

import os
import tempfile
from typing import TYPE_CHECKING, Any, Callable, List, Optional
import magic

from langchain_community.document_loaders.unstructured import UnstructuredBaseLoader

from ._universalparser import UniversalParser

if TYPE_CHECKING:
    import botocore


class S3FileLoader(UnstructuredBaseLoader):
    """Load from `Amazon AWS S3` files into Langchain documents."""

    def __init__(
        self,
        s3,
        *,
        mode: str = "single",
        post_processors: Optional[List[Callable]] = None,
        chunk_size: Optional[int],
        chunk_overlap: Optional[int] ,
        chunk_min_size: Optional[int] ,
        **unstructured_kwargs: Any,
    ):
        """Initialize loader.

        Args:
            s3: S3 client object.
            mode (str): Mode in which to read the file. Valid options are "single", "paged", and "elements".
            post_processors (list of callable): Post processing functions to be applied to extracted elements.
            **unstructured_kwargs: Arbitrary additional keyword arguments to pass in when calling `partition`.
        """
        super().__init__(mode, post_processors, **unstructured_kwargs)
        self.s3 = s3
        self.parser = UniversalParser()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunk_min_size = chunk_min_size

    def _get_elements(
        self,
        bucket: str,
        file_id: str,
        json_key_to_embed: Optional[str],
        json_metadata_keys: Optional[List[str]],
    ) -> List:
        """Get elements.

        Args:
            bucket (str): The name of the bucket.
            file_id (str): The file ID.

        Returns:
            documents (list): list of Langchain documents.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = f"{temp_dir}/{file_id}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.s3.download_file(bucket, file_id, file_path)

            # Returns a list of Langchain documents
            return self.parser.parse_and_chunk(
                file_path=file_path,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                chunk_min_size=self.chunk_min_size,
                json_key_to_embed=json_key_to_embed,
                json_metadata_keys=json_metadata_keys,
            )

    def _get_metadata(self, bucket, file_id) -> dict:
        return {"source": f"s3://{bucket}/{file_id}"}

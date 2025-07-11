import requests
import streamlit as st
from typing import Optional
import time

from ui.configuration import configuration
from ui.backend.documents import upload_document, create_collection_with_id


def parse_document(file, output_format: str = "markdown", force_ocr: bool = False, page_range: str = "", paginate_output: bool = False) -> dict:
    """
    Parse un document via l'API de parsing.

    Args:
        file: Le fichier à parser
        output_format: Format de sortie ('markdown', 'json', 'html')
        force_ocr: Forcer l'OCR
        page_range: Range de pages à convertir
        paginate_output: Paginer la sortie

    Returns:
        dict: Réponse de l'API contenant le document parsé
    """
    files = {"file": (file.name, file.getvalue(), file.type)}
    data = {"output_format": output_format, "force_ocr": force_ocr, "page_range": page_range, "paginate_output": paginate_output}

    response = requests.post(
        url=f"{configuration.playground.api_url}/v1/parse-beta",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 200:
        raise Exception(f"Erreur lors du parsing: {response.status_code} - {response.json()}")

    return response.json()


def count_document_characters(parsed_document: dict) -> int:
    """
    Compte le nombre de caractères dans un document parsé.

    Args:
        parsed_document: Document parsé retourné par l'API

    Returns:
        int: Nombre total de caractères
    """
    total_chars = 0
    for page in parsed_document.get("data", []):
        content = page.get("content", "")
        total_chars += len(content)

    return total_chars


def extract_text_from_parsed_document(parsed_document: dict) -> str:
    """
    Extrait tout le texte d'un document parsé.

    Args:
        parsed_document: Document parsé retourné par l'API

    Returns:
        str: Texte complet du document
    """
    text_parts = []
    for page in parsed_document.get("data", []):
        content = page.get("content", "")
        if content.strip():
            text_parts.append(content)

    return "\n\n".join(text_parts)


def process_large_document(file, char_count: int) -> Optional[int]:
    """
    Traite un document volumineux en créant une collection et en l'uploadant.

    Returns:
        Optional[int]: ID de la collection créée
    """
    try:
        # Créer une collection
        collection_name = f"Doc_{file.name.split(".")[0]}_{int(time.time())}"
        collection_description = f"Collection auto-créée pour {file.name} ({char_count:,} caractères)"

        collection_id = create_collection_with_id(collection_name, collection_description)

        if collection_id is None:
            return None

        # Uploader le document
        success = upload_document(file, str(collection_id))

        if success:
            return collection_id
        else:
            return None

    except Exception as e:
        st.error(f"Erreur lors du traitement du document volumineux: {str(e)}")
        return None

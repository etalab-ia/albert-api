from typing import List, Literal

from pydantic import BaseModel, Field


class OCRResponse(BaseModel):
    object: Literal["list"] = "list"
    data: List[dict]


class OCRRequest(BaseModel):
    model: str = Field(
        description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only models that support image processing are supported."
    )
    dpi: int = Field(default=150, description="DPI to use for PDF to image conversion")
    prompt: str = Field(
        default=(
            "Tu es un système d'OCR très précis. Extrait tout le texte visible de cette image. "
            "Ne décris pas l'image, n'ajoute pas de commentaires. Réponds uniquement avec le texte brut extrait, "
            "en préservant les paragraphes, la mise en forme et la structure du document. "
            "Si aucun texte n'est visible, réponds avec 'Aucun texte détecté'. "
            "Je veux une sortie au format markdown. Tu dois respecter le format de sortie pour bien conserver les tableaux."
        ),
        description="Prompt to use for OCR text extraction",
    )

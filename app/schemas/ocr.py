from fastapi import Form

DEFAULT_PROMPT = """Tu es un système d'OCR très précis. Extrait tout le texte visible de cette image. 
Ne décris pas l'image, n'ajoute pas de commentaires. Réponds uniquement avec le texte brut extrait, 
en préservant les paragraphes, la mise en forme et la structure du document. 
Si aucun texte n'est visible, réponds avec 'Aucun texte détecté'. 
Je veux une sortie au format markdown. Tu dois respecter le format de sortie pour bien conserver les tableaux."""


ModelForm: str = Form(default=..., description="The model to use for the OCR.")  # fmt: off
DPIForm: int = Form(default=150, ge=100, le=600, description="The DPI to use for the OCR (each page will be rendered as an image at this DPI).")  # fmt: off
PromptForm: str = Form(default=DEFAULT_PROMPT, description="The prompt to use for the OCR.")  # fmt: off

import re
import unicodedata


class BaseParser:
    def clean(self, text):
        text = re.sub(r"(\x00|\x1f|\x7f|\x9f)", "", text)
        text = unicodedata.normalize("NFC", text)

        return text

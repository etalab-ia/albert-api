import re
import unicodedata


class TextCleaner:
    def __init__(self):
        pass

    def clean_string(self, input_string):
        """
        Clean the input string by removing NUL bytes and other problematic characters.
        """
        if input_string is None:
            return input_string

        # Remove NUL bytes
        input_string = input_string.replace("\x00", "")

        # Remove non-printable characters
        input_string = re.sub(r"(\x00|\x1f|\x7f|\x9f)", "", input_string)

        # Normalize Unicode characters to NFC (Normalization Form C)
        input_string = unicodedata.normalize("NFC", input_string)

        return input_string

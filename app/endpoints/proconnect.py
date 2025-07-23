# This module is deprecated. Please use app.endpoints.proconnect package instead.
# All functionality has been moved to:
# - app.endpoints.proconnect.__init__.py (routes)
# - app.endpoints.proconnect.token.py (token management)
# - app.endpoints.proconnect.encryption.py (encryption functions)

# Import for backward compatibility - these imports are used by the module loader
from .proconnect import *

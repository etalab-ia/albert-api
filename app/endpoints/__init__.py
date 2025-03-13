import importlib
from pathlib import Path
import pkgutil

endpoints_modules = {}

# Get the path to the current package
package_path = Path(__file__).parent

# Find all submodule names
for _, name, ispkg in pkgutil.iter_modules([str(package_path)]):
    # Import the submodule
    module = importlib.import_module(f"{__name__}.{name}")
    endpoints_modules[name] = module

import importlib.util
import os

try:
    ROHE_PATH = os.environ["ROHE_PATH"]
except KeyError:
    raise RuntimeError("ROHE_PATH is not defined, please defined it ")

package_name = "rohe"

spec = importlib.util.find_spec(package_name)

if spec and spec.origin:
    # Get the directory path by removing the file part
    PACKAGE_DIR = os.path.dirname(spec.origin)
else:
    raise RuntimeError(f"The package '{package_name}' is not installed.")

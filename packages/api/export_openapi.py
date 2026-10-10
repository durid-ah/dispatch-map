import json
from pathlib import Path
import sys

# Ensure packages/api is on sys.path
API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from fastapi.openapi.utils import get_openapi
from main import app


def export_schema() -> None:
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    output_path = API_DIR / "openapi.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
        f.write("\n")
    print(f"OpenAPI schema successfully exported to {output_path}")


if __name__ == "__main__":
    export_schema()

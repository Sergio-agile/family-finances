"""Print the OpenAPI schema, for generating the frontend client: `uv run python -m app.openapi`."""

import json

from app.main import app

if __name__ == "__main__":
    print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))

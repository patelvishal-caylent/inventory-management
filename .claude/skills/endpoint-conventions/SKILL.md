---
name: endpoint-conventions
description: Use when adding or changing any FastAPI endpoint in server/main.py. Sets the required decorator metadata for new routes.
---

# Endpoint conventions

Every new route added to `server/main.py` must:

1. Set `tags=["inventory-v2"]` in its `@app.get(...)` decorator.
2. Set a one-line `summary="..."` in the same decorator.
3. Use a Pydantic `response_model`.

Existing routes are left as they are.

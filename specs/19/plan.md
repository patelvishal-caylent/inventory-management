# Plan: Add inventory category counts endpoint (#19)

Status: draft

## Files That Change

- `server/main.py`: add `CategoryCount` Pydantic model and the `GET /api/inventory/categories` route, declared before `/api/inventory/{item_id}`.
- `tests/backend/test_inventory.py`: add `TestCategoryCountsEndpoint` covering AC-1 to AC-4.

## Order of Work

1. Commit this spec and plan alone (`spec(#19): ...`).
2. Add `CategoryCount` model and route: filter with the existing `apply_filters(inventory_items, warehouse)`, count with `collections.Counter`, sort by `(-count, category)`.
3. Add tests, each docstring naming its AC ID.
4. Run `cd server && uv run pytest ../tests/backend`.

## Proof

- New tests in `TestCategoryCountsEndpoint` pass, along with the existing backend suite.
- PR description includes an AC coverage table mapping AC-1 to AC-5 to their tests.

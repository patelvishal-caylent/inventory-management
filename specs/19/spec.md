# Spec: Add inventory category counts endpoint (#19)

Status: draft

## Objective

Give operations a quick count of inventory items per category via `GET /api/inventory/categories`.

## Acceptance Criteria

| ID | Criterion | Verification (test name or manual step) |
|----|-----------|------------------------------------------|
| AC-1 | `GET /api/inventory/categories` returns a JSON list of `{"category": <name>, "count": <number of inventory items>}` | `test_category_counts_shape_and_totals` |
| AC-2 | The list is sorted by `count` descending, ties broken by `category` ascending | `test_category_counts_sorted_by_count_then_category` |
| AC-3 | The endpoint honors the `warehouse` query filter with the same semantics as `GET /api/inventory` | `test_category_counts_warehouse_filter_matches_inventory` |
| AC-4 | `GET /api/inventory/categories` is not captured by `/api/inventory/{item_id}` | `test_category_counts_route_not_shadowed_by_item_id` |
| AC-5 | pytest tests in `tests/backend/test_inventory.py` cover AC-1 to AC-4 | Tests above exist in `tests/backend/test_inventory.py` and pass |

## Out of Scope

- Client changes
- New dependencies
- Changes to other endpoints
- A `category` query filter on this endpoint

## Risks and Gotchas

- Route order: the static path must be declared before `/api/inventory/{item_id}`, otherwise `categories` is treated as an item id and returns 404.
- `warehouse=all` and an omitted `warehouse` must behave the same; an unknown warehouse returns `[]`, not 404.

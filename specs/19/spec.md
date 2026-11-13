# Spec: Add inventory category counts endpoint (#19)

Status: draft

## Objective

Operations want a quick count of inventory items per category. Add `GET /api/inventory/categories`, which returns one `{"category", "count"}` object per category present in the (optionally warehouse-filtered) inventory.

## Acceptance Criteria

| ID | Criterion | Verification (test name or manual step) |
|----|-----------|------------------------------------------|
| AC-1 | `GET /api/inventory/categories` returns a JSON list of objects `{"category": <name>, "count": <number of inventory items>}`, one per category, with counts matching `GET /api/inventory`. | `test_category_counts_shape_and_values` |
| AC-2 | The list is sorted by `count` descending, ties broken by `category` ascending. | `test_category_counts_sorted_by_count_then_category` |
| AC-3 | The endpoint honors the `warehouse` query filter with the same semantics as `GET /api/inventory` (exact match, `all` or omitted means no filter, unknown warehouse yields `[]`). | `test_category_counts_warehouse_filter_matches_inventory`, `test_category_counts_warehouse_all_same_as_no_filter`, `test_category_counts_nonmatching_warehouse_returns_empty_list` |
| AC-4 | `GET /api/inventory/categories` is not captured by `/api/inventory/{item_id}`; unknown item ids still return 404. | `test_category_counts_route_not_shadowed_by_item_id` |
| AC-5 | pytest tests in `tests/backend/test_inventory.py` cover AC-1 to AC-4. | `cd server && uv run pytest ../tests/backend` passes |

## Out of Scope

- Client changes.
- New dependencies.
- Changes to other endpoints.
- A `category` query filter on this endpoint (not requested).

## Risks and Gotchas

- Route ordering: FastAPI matches in declaration order, so the static `/api/inventory/categories` route must be declared before `/api/inventory/{item_id}`, otherwise it returns 404 "Item not found".
- Categories are grouped by their exact stored name; the dataset uses consistent casing, so no normalization is applied.

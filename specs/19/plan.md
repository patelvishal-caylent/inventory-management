# Plan: Add inventory category counts endpoint (#19)

Status: draft

## Files That Change

- `server/main.py`: add a `CategoryCount` Pydantic model and a `GET /api/inventory/categories` route declared before `/api/inventory/{item_id}`.
- `tests/backend/test_inventory.py`: add a `TestCategoryCountsEndpoint` test class.

## Order of Work

1. Commit this spec and plan.
2. Add the model and route, reusing `apply_filters` for the `warehouse` filter.
3. Add tests for AC-1 to AC-4.
4. Run `pytest tests/backend/`.

## Proof

- AC-1: `test_category_counts_shape_and_totals`
- AC-2: `test_category_counts_sorted_by_count_then_category`
- AC-3: `test_category_counts_warehouse_filter_matches_inventory`
- AC-4: `test_category_counts_route_not_shadowed_by_item_id`
- AC-5: all of the above live in `tests/backend/test_inventory.py` and pass under `pytest tests/backend/`.

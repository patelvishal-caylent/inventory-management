"""
Tests for inventory API endpoints.
"""
import pytest


class TestInventoryEndpoints:
    """Test suite for inventory-related endpoints."""

    def test_get_all_inventory(self, client):
        """Test getting all inventory items."""
        response = client.get("/api/inventory")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Verify structure of first item
        first_item = data[0]
        assert "id" in first_item
        assert "sku" in first_item
        assert "name" in first_item
        assert "category" in first_item
        assert "warehouse" in first_item
        assert "quantity_on_hand" in first_item
        assert "reorder_point" in first_item
        assert "unit_cost" in first_item

    def test_get_inventory_by_warehouse(self, client):
        """Test filtering inventory by warehouse."""
        response = client.get("/api/inventory?warehouse=San Francisco")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # All items should be from San Francisco
        for item in data:
            assert item["warehouse"] == "San Francisco"

    def test_get_inventory_by_category(self, client):
        """Test filtering inventory by category."""
        response = client.get("/api/inventory?category=Circuit Boards")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # All items should be Circuit Boards
        for item in data:
            assert item["category"].lower() == "circuit boards"

    def test_get_inventory_by_warehouse_and_category(self, client):
        """Test filtering inventory by both warehouse and category."""
        response = client.get("/api/inventory?warehouse=London&category=Sensors")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # All items should match both filters
        for item in data:
            assert item["warehouse"] == "London"
            assert item["category"].lower() == "sensors"

    def test_get_inventory_with_all_filter(self, client):
        """Test that 'all' filter returns all items."""
        response_all = client.get("/api/inventory?warehouse=all")
        response_no_filter = client.get("/api/inventory")

        assert response_all.status_code == 200
        assert response_no_filter.status_code == 200

        # Should return same number of items
        assert len(response_all.json()) == len(response_no_filter.json())

    def test_get_inventory_item_by_id(self, client):
        """Test getting a specific inventory item by ID."""
        # First get all items to find a valid ID
        response = client.get("/api/inventory")
        all_items = response.json()
        assert len(all_items) > 0

        first_item_id = all_items[0]["id"]

        # Now get that specific item
        response = client.get(f"/api/inventory/{first_item_id}")
        assert response.status_code == 200

        item = response.json()
        assert item["id"] == first_item_id

    def test_get_nonexistent_inventory_item(self, client):
        """Test getting an inventory item that doesn't exist."""
        response = client.get("/api/inventory/nonexistent-id-999")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_inventory_item_fields(self, client):
        """Test that inventory items have all required fields."""
        response = client.get("/api/inventory")
        data = response.json()

        required_fields = [
            "id", "sku", "name", "category", "warehouse",
            "quantity_on_hand", "reorder_point", "unit_cost",
            "location", "last_updated"
        ]

        for item in data:
            for field in required_fields:
                assert field in item, f"Missing field: {field}"

    def test_inventory_quantity_types(self, client):
        """Test that quantity fields are proper numeric types."""
        response = client.get("/api/inventory")
        data = response.json()

        for item in data:
            assert isinstance(item["quantity_on_hand"], int)
            assert isinstance(item["reorder_point"], int)
            assert isinstance(item["unit_cost"], (int, float))
            assert item["quantity_on_hand"] >= 0
            assert item["reorder_point"] >= 0
            assert item["unit_cost"] >= 0

    def test_get_inventory_power_supplies_category(self, client):
        """Test filtering by Power Supplies category (newly added)."""
        response = client.get("/api/inventory?category=Power Supplies")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Should have at least one Power Supplies item
        assert len(data) > 0

        # All items should be Power Supplies
        for item in data:
            assert item["category"].lower() == "power supplies"


LOW_STOCK_FIELDS = [
    "id",
    "sku",
    "name",
    "category",
    "warehouse",
    "quantity_on_hand",
    "reorder_point",
    "unit_cost",
    "location",
    "last_updated",
    "shortfall",
]


def _expected_low_stock_ids(client, params):
    """Ids from GET /api/inventory (same params) with quantity_on_hand < reorder_point."""
    items = client.get("/api/inventory", params=params).json()
    return {i["id"] for i in items if i["quantity_on_hand"] < i["reorder_point"]}


class TestLowStockEndpoint:
    """Test suite for GET /api/inventory/low-stock (issue #5)."""

    def test_low_stock_matches_strictly_below_reorder_point(self, client):
        """AC-1: only items with quantity_on_hand < reorder_point, matching /api/inventory."""
        response = client.get("/api/inventory/low-stock")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        for item in data:
            assert item["quantity_on_hand"] < item["reorder_point"]
        assert {i["id"] for i in data} == _expected_low_stock_ids(client, {})

    def test_low_stock_item_fields_and_shortfall(self, client):
        """AC-2: all inventory fields plus shortfall = reorder_point - quantity_on_hand > 0."""
        data = client.get("/api/inventory/low-stock").json()
        assert len(data) > 0

        for item in data:
            for field in LOW_STOCK_FIELDS:
                assert field in item, f"Missing field: {field}"
            assert item["shortfall"] > 0
            assert item["shortfall"] == item["reorder_point"] - item["quantity_on_hand"]

    def test_low_stock_sorted_by_shortfall_then_sku(self, client):
        """AC-3: worst shortfall first, ties broken by sku ascending."""
        data = client.get("/api/inventory/low-stock").json()
        assert len(data) > 1
        assert data == sorted(data, key=lambda i: (-i["shortfall"], i["sku"]))

    @pytest.mark.parametrize(
        "params",
        [
            {"warehouse": "Tokyo"},
            {"category": "Actuators"},
            {"category": "actuators"},
            {"warehouse": "Tokyo", "category": "Power Supplies"},
            {"warehouse": "London", "category": "Sensors"},
            {"warehouse": "all", "category": "all"},
        ],
    )
    def test_low_stock_filters_match_inventory_subset(self, client, params):
        """AC-4: filters behave like GET /api/inventory (warehouse exact, category case-insensitive)."""
        response = client.get("/api/inventory/low-stock", params=params)
        assert response.status_code == 200

        data = response.json()
        for item in data:
            if params.get("warehouse", "all") != "all":
                assert item["warehouse"] == params["warehouse"]
            if params.get("category", "all") != "all":
                assert item["category"].lower() == params["category"].lower()
        assert {i["id"] for i in data} == _expected_low_stock_ids(client, params)
        if params != {"warehouse": "all", "category": "all"}:
            assert len(data) > 0

    def test_low_stock_warehouse_all_same_count_as_no_filter(self, client):
        """AC-4: warehouse=all returns the same count as no filter."""
        all_filter = client.get("/api/inventory/low-stock?warehouse=all")
        no_filter = client.get("/api/inventory/low-stock")
        assert all_filter.status_code == 200
        assert len(all_filter.json()) == len(no_filter.json())
        assert len(no_filter.json()) > 0

    def test_low_stock_nonmatching_filter_returns_empty_list(self, client):
        """AC-4/AC-5: a nonmatching filter yields 200 with [], not 404."""
        response = client.get("/api/inventory/low-stock?warehouse=Nowhere")
        assert response.status_code == 200
        assert response.json() == []

    def test_low_stock_route_not_shadowed_by_item_id(self, client):
        """AC-5: low-stock is not captured by /{item_id}; unknown ids still 404."""
        response = client.get("/api/inventory/low-stock")
        assert response.status_code != 404
        assert isinstance(response.json(), list)

        missing = client.get("/api/inventory/nonexistent-id-999")
        assert missing.status_code == 404


def _expected_category_counts(client, params):
    """Category -> item count, derived from GET /api/inventory with the same params."""
    counts = {}
    for item in client.get("/api/inventory", params=params).json():
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    return counts


class TestCategoryCountsEndpoint:
    """Test suite for GET /api/inventory/categories (issue #19)."""

    def test_category_counts_shape_and_values(self, client):
        """AC-1: list of {category, count} objects whose counts match GET /api/inventory."""
        response = client.get("/api/inventory/categories")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        for entry in data:
            assert set(entry.keys()) == {"category", "count"}
            assert isinstance(entry["category"], str)
            assert isinstance(entry["count"], int)
            assert entry["count"] > 0

        categories = [entry["category"] for entry in data]
        assert len(categories) == len(set(categories))
        assert {e["category"]: e["count"] for e in data} == _expected_category_counts(client, {})
        assert sum(e["count"] for e in data) == len(client.get("/api/inventory").json())

    @pytest.mark.parametrize(
        "params",
        [{}, {"warehouse": "San Francisco"}, {"warehouse": "London"}, {"warehouse": "Tokyo"}],
    )
    def test_category_counts_sorted_by_count_then_category(self, client, params):
        """AC-2: sorted by count descending, ties broken by category ascending."""
        data = client.get("/api/inventory/categories", params=params).json()
        assert len(data) > 1
        assert data == sorted(data, key=lambda e: (-e["count"], e["category"]))

    def test_category_counts_tie_broken_by_category_ascending(self, client, monkeypatch, sample_inventory_item):
        """AC-2: equal counts are ordered by category name ascending."""
        import main

        def item(category):
            return {**sample_inventory_item, "category": category}

        synthetic = [item("Zeta"), item("Alpha"), item("Mid"), item("Mid"), item("Zeta"), item("Alpha"), item("Beta")]
        monkeypatch.setattr(main, "inventory_items", synthetic)

        data = client.get("/api/inventory/categories").json()
        assert data == [
            {"category": "Alpha", "count": 2},
            {"category": "Mid", "count": 2},
            {"category": "Zeta", "count": 2},
            {"category": "Beta", "count": 1},
        ]

    @pytest.mark.parametrize("warehouse", ["San Francisco", "London", "Tokyo"])
    def test_category_counts_warehouse_filter_matches_inventory(self, client, warehouse):
        """AC-3: warehouse filter counts match GET /api/inventory?warehouse=<same>."""
        response = client.get("/api/inventory/categories", params={"warehouse": warehouse})
        assert response.status_code == 200

        data = response.json()
        assert len(data) > 0
        expected = _expected_category_counts(client, {"warehouse": warehouse})
        assert {e["category"]: e["count"] for e in data} == expected
        assert expected != _expected_category_counts(client, {})

    def test_category_counts_warehouse_all_same_as_no_filter(self, client):
        """AC-3: warehouse=all returns the same result as no filter."""
        all_filter = client.get("/api/inventory/categories?warehouse=all")
        no_filter = client.get("/api/inventory/categories")
        assert all_filter.status_code == 200
        assert no_filter.status_code == 200
        assert all_filter.json() == no_filter.json()

    def test_category_counts_nonmatching_warehouse_returns_empty_list(self, client):
        """AC-3: an unknown warehouse yields 200 with [], like GET /api/inventory."""
        response = client.get("/api/inventory/categories?warehouse=Nowhere")
        assert response.status_code == 200
        assert response.json() == []
        assert client.get("/api/inventory?warehouse=Nowhere").json() == []

    def test_category_counts_route_not_shadowed_by_item_id(self, client):
        """AC-4: categories is not captured by /{item_id}; unknown ids still 404."""
        response = client.get("/api/inventory/categories")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

        missing = client.get("/api/inventory/nonexistent-id-999")
        assert missing.status_code == 404

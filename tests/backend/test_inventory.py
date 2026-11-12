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


class TestLowStockEndpoint:
    """Tests for GET /api/inventory/low-stock."""

    def test_only_items_below_reorder_point(self, client):
        """Criterion 1: only quantity_on_hand < reorder_point is returned."""
        all_items = client.get("/api/inventory").json()
        expected = {i["id"] for i in all_items if i["quantity_on_hand"] < i["reorder_point"]}

        response = client.get("/api/inventory/low-stock")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert {i["id"] for i in data} == expected
        for item in data:
            assert item["quantity_on_hand"] < item["reorder_point"]

    def test_includes_inventory_fields_and_shortfall(self, client):
        """Criterion 2: all InventoryItem fields plus shortfall."""
        by_id = {i["id"]: i for i in client.get("/api/inventory").json()}
        data = client.get("/api/inventory/low-stock").json()
        assert len(data) > 0
        for item in data:
            assert item["shortfall"] == item["reorder_point"] - item["quantity_on_hand"]
            for key, value in by_id[item["id"]].items():
                assert item[key] == value

    def test_sorted_by_shortfall_desc_then_sku_asc(self, client):
        """Criterion 3: shortfall descending, ties broken by sku ascending."""
        data = client.get("/api/inventory/low-stock").json()
        keys = [(-i["shortfall"], i["sku"]) for i in data]
        assert keys == sorted(keys)

    def test_honors_warehouse_and_category_filters(self, client):
        """Criterion 4: same filter semantics as /api/inventory."""
        data = client.get("/api/inventory/low-stock?warehouse=San Francisco").json()
        assert all(i["warehouse"] == "San Francisco" for i in data)

        data = client.get("/api/inventory/low-stock?category=circuit boards").json()
        assert all(i["category"].lower() == "circuit boards" for i in data)

        unfiltered = client.get("/api/inventory/low-stock").json()
        all_filter = client.get("/api/inventory/low-stock?warehouse=all&category=all").json()
        assert all_filter == unfiltered

    def test_empty_result_via_filters(self, client):
        """Criteria 4 and 6: filters matching nothing give an empty list, not an error."""
        response = client.get("/api/inventory/low-stock?warehouse=Nowhere")
        assert response.status_code == 200
        assert response.json() == []

    def test_not_captured_by_item_id_route(self, client):
        """Criterion 5: 'low-stock' returns the list, never a 404 item lookup."""
        response = client.get("/api/inventory/low-stock")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

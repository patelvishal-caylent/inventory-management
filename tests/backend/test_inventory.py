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
    """Test suite for the low-stock inventory endpoint."""

    @staticmethod
    def _expected_low_stock(items):
        """Build the expected low-stock list from raw inventory items."""
        expected = [
            {**item, "shortfall": item["reorder_point"] - item["quantity_on_hand"]}
            for item in items
            if item["quantity_on_hand"] < item["reorder_point"]
        ]
        return sorted(expected, key=lambda item: (-item["shortfall"], item["sku"]))

    def test_get_low_stock_only_below_reorder_point(self, client):
        """Test that only items strictly below their reorder point are returned (AC 1)."""
        response = client.get("/api/inventory/low-stock")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for item in data:
            assert item["quantity_on_hand"] < item["reorder_point"]

        all_items = client.get("/api/inventory").json()
        expected_ids = {
            item["id"] for item in all_items
            if item["quantity_on_hand"] < item["reorder_point"]
        }
        assert {item["id"] for item in data} == expected_ids

    def test_low_stock_item_fields_and_shortfall(self, client):
        """Test that items include all InventoryItem fields plus shortfall (AC 2)."""
        all_items = {item["id"]: item for item in client.get("/api/inventory").json()}
        data = client.get("/api/inventory/low-stock").json()
        assert len(data) > 0

        for item in data:
            original = all_items[item["id"]]
            for field, value in original.items():
                assert item[field] == value, f"Mismatch in field: {field}"
            assert set(item.keys()) == set(original.keys()) | {"shortfall"}
            assert isinstance(item["shortfall"], int)
            assert item["shortfall"] == item["reorder_point"] - item["quantity_on_hand"]
            assert item["shortfall"] > 0

    def test_low_stock_sorted_by_shortfall_desc_then_sku(self, client):
        """Test sorting by shortfall descending with sku ascending tie-break (AC 3)."""
        data = client.get("/api/inventory/low-stock").json()
        all_items = client.get("/api/inventory").json()

        assert [item["sku"] for item in data] == [
            item["sku"] for item in self._expected_low_stock(all_items)
        ]

        for current, following in zip(data, data[1:]):
            assert current["shortfall"] >= following["shortfall"]
            if current["shortfall"] == following["shortfall"]:
                assert current["sku"] < following["sku"]

    def test_low_stock_tie_broken_by_sku(self, client):
        """Test that the dataset's equal-shortfall items are ordered by sku (AC 3)."""
        data = client.get("/api/inventory/low-stock").json()
        shortfalls = [item["shortfall"] for item in data]
        tied = [s for s in set(shortfalls) if shortfalls.count(s) > 1]
        assert tied, "Expected at least one shortfall tie in the mock data"

        for shortfall in tied:
            skus = [item["sku"] for item in data if item["shortfall"] == shortfall]
            assert skus == sorted(skus)

    @pytest.mark.parametrize("query", [
        "warehouse=Tokyo",
        "category=Actuators",
        "category=actuators",
        "warehouse=Tokyo&category=Power Supplies",
    ])
    def test_get_low_stock_with_filters(self, client, query):
        """Test that warehouse/category filters match GET /api/inventory semantics (AC 4)."""
        response = client.get(f"/api/inventory/low-stock?{query}")
        assert response.status_code == 200

        filtered_inventory = client.get(f"/api/inventory?{query}").json()
        data = response.json()
        assert len(data) > 0
        assert data == self._expected_low_stock(filtered_inventory)

    def test_get_low_stock_with_all_filter(self, client):
        """Test that 'all' filter values return the unfiltered result (AC 4)."""
        response_all = client.get("/api/inventory/low-stock?warehouse=all&category=all")
        response_no_filter = client.get("/api/inventory/low-stock")

        assert response_all.status_code == 200
        assert response_all.json() == response_no_filter.json()

    def test_get_low_stock_empty_result_via_filters(self, client):
        """Test that filters with no low-stock matches return an empty list (AC 4, 6)."""
        response = client.get("/api/inventory/low-stock?warehouse=San Francisco")
        assert response.status_code == 200
        assert response.json() == []

        response = client.get("/api/inventory/low-stock?category=Nonexistent Category")
        assert response.status_code == 200
        assert response.json() == []

    def test_low_stock_route_not_captured_by_item_id(self, client):
        """Test that /low-stock is not handled by /api/inventory/{item_id} (AC 5)."""
        response = client.get("/api/inventory/low-stock")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

        response = client.get("/api/inventory/nonexistent-id-999")
        assert response.status_code == 404

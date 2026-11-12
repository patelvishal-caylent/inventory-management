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


def _make_item(item_id, sku, quantity_on_hand, reorder_point,
               warehouse="Tokyo", category="Sensors"):
    return {
        "id": item_id,
        "sku": sku,
        "name": f"Item {sku}",
        "category": category,
        "warehouse": warehouse,
        "quantity_on_hand": quantity_on_hand,
        "reorder_point": reorder_point,
        "unit_cost": 10.0,
        "location": f"{warehouse} Warehouse",
        "last_updated": "2025-09-30T10:30:00"
    }


@pytest.fixture
def controlled_inventory(monkeypatch):
    """Replace the inventory with a fixed set covering ties and the reorder-point boundary."""
    import main

    items = [
        _make_item("1", "BBB-002", 10, 50),                      # shortfall 40
        _make_item("2", "AAA-001", 10, 50, warehouse="London"),  # shortfall 40, sorts before BBB-002
        _make_item("3", "CCC-003", 95, 100, category="Actuators"),  # shortfall 5
        _make_item("4", "DDD-004", 100, 100),                    # at reorder point: excluded
        _make_item("5", "EEE-005", 500, 100),                    # well stocked: excluded
        _make_item("6", "FFF-006", 0, 70, category="Actuators"),  # shortfall 70
    ]
    monkeypatch.setattr(main, "inventory_items", items)
    return items


class TestLowStockEndpoint:
    """Test suite for GET /api/inventory/low-stock."""

    INVENTORY_FIELDS = [
        "id", "sku", "name", "category", "warehouse",
        "quantity_on_hand", "reorder_point", "unit_cost",
        "location", "last_updated"
    ]

    def test_low_stock_route_not_captured_by_item_id_route(self, client):
        """Criterion 5: /low-stock returns the list, not a 404 for item 'low-stock'."""
        response = client.get("/api/inventory/low-stock")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

        # The item-by-id route still works alongside it
        assert client.get("/api/inventory/1").status_code == 200

    def test_low_stock_returns_only_items_below_reorder_point(self, client):
        """Criterion 1: exactly the items with quantity_on_hand < reorder_point."""
        all_items = client.get("/api/inventory").json()
        expected_ids = {
            item["id"] for item in all_items
            if item["quantity_on_hand"] < item["reorder_point"]
        }

        data = client.get("/api/inventory/low-stock").json()

        assert len(data) > 0
        assert {item["id"] for item in data} == expected_ids
        assert len(data) == len(expected_ids)
        for item in data:
            assert item["quantity_on_hand"] < item["reorder_point"]

    def test_low_stock_excludes_items_at_reorder_point(self, client, controlled_inventory):
        """Criterion 1: strict inequality, so items exactly at reorder point are excluded."""
        data = client.get("/api/inventory/low-stock").json()
        skus = {item["sku"] for item in data}

        assert "DDD-004" not in skus
        assert "EEE-005" not in skus
        assert skus == {"AAA-001", "BBB-002", "CCC-003", "FFF-006"}

    def test_low_stock_includes_inventory_fields_and_shortfall(self, client):
        """Criterion 2: all InventoryItem fields plus shortfall = reorder_point - quantity_on_hand."""
        all_items = {item["id"]: item for item in client.get("/api/inventory").json()}
        data = client.get("/api/inventory/low-stock").json()
        assert len(data) > 0

        for item in data:
            for field in self.INVENTORY_FIELDS:
                assert field in item, f"Missing field: {field}"
                assert item[field] == all_items[item["id"]][field]
            assert isinstance(item["shortfall"], int)
            assert item["shortfall"] == item["reorder_point"] - item["quantity_on_hand"]
            assert item["shortfall"] > 0

    def test_low_stock_sorted_by_shortfall_desc_then_sku(self, client, controlled_inventory):
        """Criterion 3: shortfall descending, ties broken by sku ascending."""
        data = client.get("/api/inventory/low-stock").json()

        assert [item["sku"] for item in data] == ["FFF-006", "AAA-001", "BBB-002", "CCC-003"]
        assert [item["shortfall"] for item in data] == [70, 40, 40, 5]

    def test_low_stock_sort_order_on_real_data(self, client):
        """Criterion 3: ordering holds against the shipped inventory data."""
        data = client.get("/api/inventory/low-stock").json()
        sort_keys = [(-item["shortfall"], item["sku"]) for item in data]
        assert sort_keys == sorted(sort_keys)

    def test_low_stock_filter_by_warehouse(self, client):
        """Criterion 4: warehouse filter matches GET /api/inventory semantics."""
        inventory = client.get("/api/inventory?warehouse=Tokyo").json()
        expected_ids = {
            item["id"] for item in inventory
            if item["quantity_on_hand"] < item["reorder_point"]
        }

        response = client.get("/api/inventory/low-stock?warehouse=Tokyo")
        assert response.status_code == 200
        data = response.json()

        assert len(data) > 0
        assert {item["id"] for item in data} == expected_ids
        for item in data:
            assert item["warehouse"] == "Tokyo"

    def test_low_stock_filter_by_category_case_insensitive(self, client):
        """Criterion 4: category filter is case-insensitive, like GET /api/inventory."""
        inventory = client.get("/api/inventory?category=actuators").json()
        expected_ids = {
            item["id"] for item in inventory
            if item["quantity_on_hand"] < item["reorder_point"]
        }

        response = client.get("/api/inventory/low-stock?category=actuators")
        assert response.status_code == 200
        data = response.json()

        assert len(data) > 0
        assert {item["id"] for item in data} == expected_ids
        for item in data:
            assert item["category"].lower() == "actuators"

    def test_low_stock_filter_by_warehouse_and_category(self, client, controlled_inventory):
        """Criterion 4: combined filters apply together, and sorting still holds."""
        data = client.get("/api/inventory/low-stock?warehouse=Tokyo&category=Actuators").json()
        assert [item["sku"] for item in data] == ["FFF-006", "CCC-003"]

    def test_low_stock_all_filter_value_is_ignored(self, client):
        """Criterion 4: 'all' means no filter, as with GET /api/inventory."""
        unfiltered = client.get("/api/inventory/low-stock").json()
        all_filtered = client.get("/api/inventory/low-stock?warehouse=all&category=all").json()
        assert all_filtered == unfiltered

    def test_low_stock_empty_result_via_filters(self, client):
        """Criteria 1 and 4: filters can narrow the result to an empty list (not a 404)."""
        # San Francisco has stock, but none of it is below reorder point
        assert len(client.get("/api/inventory?warehouse=San Francisco").json()) > 0

        response = client.get("/api/inventory/low-stock?warehouse=San Francisco")
        assert response.status_code == 200
        assert response.json() == []

    def test_low_stock_empty_result_via_unknown_filter(self, client):
        """Criterion 4: a filter matching nothing returns an empty list."""
        response = client.get("/api/inventory/low-stock?category=Nonexistent")
        assert response.status_code == 200
        assert response.json() == []

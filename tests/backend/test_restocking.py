"""
Tests for restock order API endpoints.
"""
import pytest

from main import restock_orders


@pytest.fixture(autouse=True)
def reset_restock_orders():
    """Clear submitted restock orders before each test."""
    # Cleared in place so the list object main.py bound at import time is preserved
    restock_orders.clear()


class TestRestockOrdersEndpoints:
    """Test suite for restock-order-related endpoints."""

    def test_get_all_restock_orders_empty(self, client):
        """Test getting restock orders when none have been submitted."""
        response = client.get("/api/restock-orders")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_create_restock_order(self, client):
        """Test submitting a restock order."""
        response = client.post("/api/restock-orders", json={
            "budget": 50000,
            "items": [
                {
                    "sku": "TMP-201",
                    "name": "Temperature Sensor Module",
                    "quantity": 295,
                    "unit_cost": 89.5
                }
            ]
        })
        assert response.status_code == 201

        data = response.json()
        assert isinstance(data, dict)
        assert "id" in data
        assert "order_number" in data
        assert "items" in data
        assert "status" in data
        assert "created_date" in data
        assert "expected_delivery" in data
        assert "lead_time_days" in data
        assert "total_value" in data

        assert data["order_number"].startswith("RST-")
        assert data["status"] == "Submitted"
        assert data["budget"] == 50000

    def test_restock_order_dates_format(self, client):
        """Test that restock order dates are in proper format."""
        response = client.post("/api/restock-orders", json={
            "items": [
                {
                    "sku": "HMD-202",
                    "name": "Humidity Sensor Module",
                    "quantity": 120,
                    "unit_cost": 125.0
                }
            ]
        })
        assert response.status_code == 201

        data = response.json()
        assert "-" in data["created_date"]
        assert "T" in data["created_date"]  # Has time component
        assert "-" in data["expected_delivery"]
        assert "T" in data["expected_delivery"]

    def test_restock_order_total_value_calculation(self, client):
        """Test that restock order total value matches its line items."""
        response = client.post("/api/restock-orders", json={
            "items": [
                {
                    "sku": "TMP-201",
                    "name": "Temperature Sensor Module",
                    "quantity": 295,
                    "unit_cost": 89.5
                },
                {
                    "sku": "SRV-301",
                    "name": "Micro Servo Motor",
                    "quantity": 95,
                    "unit_cost": 445.0
                }
            ]
        })
        assert response.status_code == 201

        data = response.json()
        calculated_total = sum(
            item["quantity"] * item["unit_cost"]
            for item in data["items"]
        )
        # Allow small floating point differences
        assert abs(data["total_value"] - calculated_total) < 0.01

    def test_restock_order_category_resolution(self, client):
        """Test that line item categories are resolved from inventory."""
        response = client.post("/api/restock-orders", json={
            "items": [
                {
                    "sku": "PCB-003",
                    "name": "Multi Layer PCB Assembly",
                    "quantity": 245,
                    "unit_cost": 34.5
                }
            ]
        })
        assert response.status_code == 201

        data = response.json()
        assert data["items"][0]["category"] == "Circuit Boards"

    def test_restock_order_lead_time_calculation(self, client):
        """Test that lead time is the maximum across item categories."""
        response = client.post("/api/restock-orders", json={
            "items": [
                {
                    "sku": "PSU-505",
                    "name": "48V DC Power Supply Unit",
                    "quantity": 155,
                    "unit_cost": 67.5
                },
                {
                    "sku": "STP-303",
                    "name": "Stepper Motor NEMA 17",
                    "quantity": 68,
                    "unit_cost": 325.0
                }
            ]
        })
        assert response.status_code == 201

        data = response.json()
        assert isinstance(data["lead_time_days"], int)
        # Power Supplies is 10 days, Actuators is 18 - the slower line wins
        assert data["lead_time_days"] == 18

    def test_restock_order_unknown_sku_uses_default_lead_time(self, client):
        """Test that a SKU missing from inventory falls back to the default lead time."""
        response = client.post("/api/restock-orders", json={
            "items": [
                {
                    "sku": "NOPE-999",
                    "name": "Unknown Part",
                    "quantity": 5,
                    "unit_cost": 10.0
                }
            ]
        })
        assert response.status_code == 201

        data = response.json()
        assert data["lead_time_days"] == 14
        assert data["items"][0]["category"] == "Unknown"

    def test_create_restock_order_empty_items(self, client):
        """Test that a restock order with no items is rejected."""
        response = client.post("/api/restock-orders", json={"items": []})
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data

    def test_create_restock_order_invalid_quantity(self, client):
        """Test that a restock order with a non-positive quantity is rejected."""
        response = client.post("/api/restock-orders", json={
            "items": [
                {
                    "sku": "TMP-201",
                    "name": "Temperature Sensor Module",
                    "quantity": 0,
                    "unit_cost": 89.5
                }
            ]
        })
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data

    def test_get_restock_orders_after_create(self, client):
        """Test that a submitted restock order is returned by the list endpoint."""
        create_response = client.post("/api/restock-orders", json={
            "items": [
                {
                    "sku": "PSU-508",
                    "name": "Battery Backup Power Supply",
                    "quantity": 185,
                    "unit_cost": 185.5
                }
            ]
        })
        assert create_response.status_code == 201
        created = create_response.json()

        response = client.get("/api/restock-orders")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == created["id"]
        assert data[0]["order_number"] == created["order_number"]

    def test_restock_orders_do_not_affect_dashboard(self, client):
        """Test that restock orders are kept out of the customer orders aggregates."""
        before = client.get("/api/dashboard/summary").json()

        client.post("/api/restock-orders", json={
            "items": [
                {
                    "sku": "SRV-302",
                    "name": "Standard Servo Motor",
                    "quantity": 67,
                    "unit_cost": 725.0
                }
            ]
        })

        after = client.get("/api/dashboard/summary").json()
        assert after["pending_orders"] == before["pending_orders"]
        assert after["total_orders_value"] == before["total_orders_value"]

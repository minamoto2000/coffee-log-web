import pytest
from fastapi.testclient import TestClient

from app import db as database
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()

    with TestClient(app) as test_client:
        yield test_client


def _create(client, name="Test Set"):
    response = client.post(
        "/equipment-sets",
        json={
            "name": name,
            "filter_label": "Paper",
            "brewer_label": "V60",
            "grinder_label": "Test Grinder",
            "grind_setting_unit": "click",
            "note": None,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_patch_updates_only_provided_fields(client):
    created = _create(client)

    response = client.patch(f"/equipment-sets/{created['id']}", json={"name": "Renamed"})

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"
    assert response.json()["brewer_label"] == "V60"


def test_patch_empty_body_returns_400(client):
    created = _create(client)

    response = client.patch(f"/equipment-sets/{created['id']}", json={})

    assert response.status_code == 400
    assert response.json() == {"detail": "No fields to update"}


def test_patch_rejects_null_for_required_field(client):
    created = _create(client)

    response = client.patch(f"/equipment-sets/{created['id']}", json={"name": None})

    assert response.status_code == 422


def test_patch_missing_resource_returns_404(client):
    response = client.patch("/equipment-sets/999", json={"name": "Renamed"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Equipment set not found"}


def test_delete_is_soft_and_hides_the_set(client):
    kept = _create(client, name="Kept")
    removed = _create(client, name="Removed")

    delete_response = client.delete(f"/equipment-sets/{removed['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json()["is_active"] is False
    assert client.get(f"/equipment-sets/{removed['id']}").status_code == 404
    assert [item["id"] for item in client.get("/equipment-sets").json()] == [kept["id"]]
    assert client.delete(f"/equipment-sets/{removed['id']}").status_code == 404

    with database.get_connection() as conn:
        row = conn.execute(
            "SELECT is_active FROM equipment_sets WHERE id = ?", (removed["id"],)
        ).fetchone()
    assert row["is_active"] == 0

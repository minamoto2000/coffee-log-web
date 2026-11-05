"""HTML pages of the experiment workflow (01b 9).

These check that each page renders the values it is responsible for and
that its inline JavaScript parses. Form behaviour is checked by hand
(see the PR description); HTTP 200 alone is not treated as E2E evidence.
"""
import re
import shutil
import subprocess

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


def steps(first_pour_temp):
    return [
        {"step_type": "pour", "start_s": 0, "water_g": 30, "kettle_temp_c": first_pour_temp},
        {"step_type": "agitate", "start_s": 10, "agitation_method": "swirl"},
        {"step_type": "pour", "start_s": 120, "water_g": 220, "kettle_temp_c": 93},
    ]


@pytest.fixture
def experiment(client):
    equipment = client.post(
        "/equipment-sets",
        json={"name": "Home V60", "filter_label": "Paper", "brewer_label": "V60",
              "grinder_label": "Grinder", "grind_setting_unit": "click", "note": None},
    ).json()
    body = client.post(
        "/experiments",
        json={
            "title": "Bloom temperature",
            "hypothesis": "50℃の蒸らしでTDSが下がる",
            "changed_variable": "1投目のケトル温度",
            "bean_label": "Ethiopia Guji",
            "roast_date": "2026-10-28",
            "equipment_set_id": equipment["id"],
            "extraction_style": "percolation",
            "planned_trials_per_condition": 3,
            "conditions": [
                {"label": "A", "name": "50℃蒸らし", "dose_g": 15, "steps": steps(50)},
                {"label": "B", "name": "93℃蒸らし", "dose_g": 15, "steps": steps(93)},
            ],
        },
    ).json()
    condition_a = body["conditions"][0]["id"]
    trial = client.post(
        f"/conditions/{condition_a}/trials",
        json={"brewed_at": "2026-11-05T08:30:00+09:00", "dose_g_actual": 15.02, "beverage_mass_g": 212.4,
              "followed_plan": True, "tds_readings": [{"tds_pct": 1.38}, {"tds_pct": 1.40}],
              "sensory": {"overall_score": 7, "blinded": False}},
    ).json()
    return {"id": body["id"], "trial_id": trial["id"]}


def get_page(client, url):
    response = client.get(url)
    assert response.status_code == 200, url
    assert response.headers["content-type"].startswith("text/html")
    return response.text


def assert_scripts_parse(html, tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    for index, script in enumerate(re.findall(r"<script>(.*?)</script>", html, re.S)):
        path = tmp_path / f"inline_{index}.js"
        path.write_text(script)
        result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


def test_home_links_to_the_workflow(client):
    html = get_page(client, "/")

    assert 'href="/pages/experiments/new"' in html
    assert 'href="/pages/equipment-sets"' in html


def test_experiment_list(client, experiment):
    html = get_page(client, "/pages/experiments")

    assert f'href="/pages/experiments/{experiment["id"]}"' in html
    assert "実施中" in html
    assert "1 / 0" in html


def test_experiment_form_lists_active_equipment_and_parses(client, experiment, tmp_path):
    html = get_page(client, "/pages/experiments/new")

    assert "Home V60" in html
    assert "copy-a-to-b" in html
    assert_scripts_parse(html, tmp_path)


def test_experiment_form_without_equipment_points_to_registration(client):
    html = get_page(client, "/pages/experiments/new")

    assert 'href="/pages/equipment-sets/new"' in html


def test_experiment_detail_shows_diff_plan_and_trials(client, experiment, tmp_path):
    html = get_page(client, f"/pages/experiments/{experiment['id']}")

    assert "steps[1].kettle_temp_c: 50.0 → 93.0" in html
    assert "次に淹れる条件：B" in html
    assert 'class="diff"' in html
    assert "回す" in html  # agitation method label
    assert "1.39" in html  # TDS mean of the trial
    assert "19.7" in html  # EY of the trial, 1 decimal
    assert "2026-11-05 08:30" in html  # local time
    assert 'id="delete-experiment"' not in html  # deletion is offered only without trials
    assert_scripts_parse(html, tmp_path)


def test_trial_form_preselects_next_condition(client, experiment, tmp_path):
    html = get_page(client, f"/pages/experiments/{experiment['id']}/trials/new")

    assert re.search(r'selected>\s*B：93℃蒸らし（次に淹れる条件）', html)
    assert_scripts_parse(html, tmp_path)


def test_trial_detail_shows_measured_and_derived(client, experiment, tmp_path):
    html = get_page(client, f"/pages/trials/{experiment['trial_id']}")

    assert "1.39 %（2 回測定）" in html
    assert "19.7 %" in html
    assert "8 日" in html  # days since roast in local time
    assert "BEVERAGE_MASS_V1" in html
    assert_scripts_parse(html, tmp_path)


def test_comparison_page_shows_values_spread_and_warnings(client, experiment):
    html = get_page(client, f"/pages/experiments/{experiment['id']}/comparison")

    assert 'data-metric="tds_pct"' in html
    assert 'data-metric="sweetness"' not in html  # no data in either condition
    assert 'data-code="N_SMALL"' in html
    assert 'data-code="NOT_BLINDED"' in html
    assert "1.390" in html  # mean TDS of A with one more decimal
    assert "測定のばらつき" in html
    assert "効果あり" in html and "判定はしません" in html


def test_comparison_page_can_include_deviated_trials(client, experiment):
    html = get_page(client, f"/pages/experiments/{experiment['id']}/comparison?include_deviated=true")

    assert "逸脱した試行を含めて表示中" in html


def test_missing_pages_return_404(client):
    assert client.get("/pages/experiments/999").status_code == 404
    assert client.get("/pages/trials/999").status_code == 404


def test_equipment_set_pages(client, tmp_path):
    created = client.post(
        "/equipment-sets",
        json={"name": "Home V60", "filter_label": "Paper", "brewer_label": "V60",
              "grinder_label": "Grinder", "grind_setting_unit": "click", "note": None},
    ).json()

    listing = get_page(client, "/pages/equipment-sets")
    new_form = get_page(client, "/pages/equipment-sets/new")
    edit_form = get_page(client, f"/pages/equipment-sets/{created['id']}/edit")

    assert "Home V60" in listing
    assert 'value="Home V60"' in edit_form
    for html in (listing, new_form, edit_form):
        assert_scripts_parse(html, tmp_path)


def test_legacy_pages_are_gone(client):
    assert client.get("/pages/logs").status_code == 404
    assert client.get("/logs").status_code == 404

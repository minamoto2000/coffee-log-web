"""End-to-end: a real server and a real browser walk the Core Vertical Slice.

Runs only when E2E_BASE_URL points at a running app (CI starts uvicorn on
an empty database). Unit and API tests cover the rules; this covers the
pages, their JavaScript and the round trips between them.
"""
import os
import re

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL is not set")

# condition, TDS readings, beverage g, overall score
BREWS = [
    ("A", ["1.30", "1.32"], "212", "6"),
    ("B", ["1.40", "1.42"], "210", "7"),
    ("A", ["1.34", "1.34"], "213", "7"),
    ("B", ["1.44", "1.44"], "211", "8"),
]


@pytest.fixture
def page():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(base_url=BASE_URL, timezone_id="Asia/Tokyo", locale="ja-JP")
        tab = context.new_page()
        errors = []
        tab.on("pageerror", lambda error: errors.append(str(error)))
        tab.on("dialog", lambda dialog: dialog.accept())
        yield tab
        browser.close()
        assert errors == [], errors


def fill_step(row, start, water, temp):
    row.locator('[data-field="start_s"]').fill(start)
    row.locator('[data-field="water_g"]').fill(water)
    row.locator('[data-field="kettle_temp_c"]').fill(temp)


def test_core_vertical_slice_in_the_browser(page):
    # equipment
    page.goto("/pages/equipment-sets/new")
    for name, value in [("name", "E2E V60"), ("brewer_label", "V60"), ("filter_label", "Paper"), ("grinder_label", "Grinder")]:
        page.fill(f'input[name="{name}"]', value)
    page.click('button[type="submit"]')
    page.wait_for_url("**/pages/equipment-sets")
    assert page.locator("text=E2E V60").count() == 1

    # experiment: A = 50 C bloom, copy to B, change only the first pour to 93 C
    page.goto("/pages/experiments/new")
    page.fill('input[name="title"]', "E2E bloom temperature")
    page.fill('textarea[name="hypothesis"]', "50℃の蒸らしでTDSが下がる")
    page.fill('input[name="changed_variable"]', "1投目のケトル温度")
    page.fill('input[name="bean_label"]', "Ethiopia")
    page.fill('input[name="roast_date"]', "2026-10-28")
    page.select_option('select[name="equipment_set_id"]', label="E2E V60（V60 / Grinder）")
    a = page.locator("#condition-A")
    a.locator('[data-field="name"]').fill("50℃蒸らし")
    a.locator('[data-field="dose_g"]').fill("15")
    fill_step(a.locator("tbody tr").nth(0), "0", "30", "50")
    a.locator('[data-action="add-step"]').click()
    fill_step(a.locator("tbody tr").nth(1), "120", "220", "93")
    page.click("#copy-a-to-b")
    b = page.locator("#condition-B")
    b.locator('[data-field="name"]').fill("93℃蒸らし")
    b.locator("tbody tr").nth(0).locator('[data-field="kettle_temp_c"]').fill("93")
    assert page.locator("#diff").inner_text().strip() == "steps[1].kettle_temp_c: 50 → 93"
    page.click('button[type="submit"]')
    page.wait_for_url(re.compile(r"/pages/experiments/\d+$"))
    experiment_url = page.url
    assert "steps[1].kettle_temp_c: 50.0 → 93.0" in page.content()

    # trials: follow the next-condition hint, which the form preselects
    for hour, (label, readings, beverage, overall) in enumerate(BREWS):
        page.goto(experiment_url)
        assert page.locator("h2", has_text="次に淹れる条件").inner_text().endswith(label)
        page.click("text=試行を記録する")
        assert page.locator('select[name="condition_id"] option:checked').inner_text().strip().startswith(label)
        page.fill('input[name="brewed_at"]', f"2026-11-05T{8 + hour:02d}:00")
        page.fill('input[name="beverage_mass_g"]', beverage)
        page.fill('input[name="brew_time_s"]', "200")
        rows = page.locator("#tds-rows tr")
        for index, value in enumerate(readings):
            rows.nth(index).locator('[data-field="tds_pct"]').fill(value)
        page.select_option('select[name="overall_score"]', overall)
        page.check('input[name="blinded"]')
        page.click('button[type="submit"]')
        page.wait_for_url(experiment_url)

    detail = page.content()
    assert "予定反復数に到達" not in detail  # planned 3 per condition, 2 recorded
    assert "2026-11-05 08:00" in detail  # shown in local time

    # comparison
    page.click("text=条件を比較する")
    tds_row = page.locator('tr[data-metric="tds_pct"]').inner_text()
    assert "1.325" in tds_row and "1.425" in tds_row and "0.100" in tds_row
    assert page.locator('[data-code="N_SMALL"]').count() == 1
    assert page.locator('[data-code="NOT_BLINDED"]').count() == 0

    # exclude one trial and see the comparison change
    page.goto(experiment_url)
    page.locator("table").last.locator("a").first.click()
    page.check('input[name="excluded"]')
    page.fill('input[name="exclusion_reason"]', "こぼした")
    page.click('#trial-form button[type="submit"]')
    page.wait_for_selector("text=比較から除外されています")  # the page reloads after the PATCH
    page.goto(experiment_url + "/comparison")
    assert page.locator('[data-code="DEVIATED_OR_EXCLUDED"]').count() == 1

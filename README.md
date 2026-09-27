# Coffee Log Web

ハンドドリップの抽出条件と評価を記録し、次回変更する操作を1つ返すFastAPI製Webアプリです。

このリポジトリは一社目のBackend / Web Engineer就活で提示する主成果物として、API設計、Pydantic validation、SQLiteの参照整合性、transaction、PATCH semantics、ルールベースRecommendation、テストを説明できる状態を目的にしています。

## Core Vertical Slice

現在の実装で、次の一連の操作をWeb画面またはAPIから実行できます。

```text
Equipment Setを登録
→ Brew Log + Evaluationを同時登録
→ 保存したログを確認
→ Recommendationを1つ表示
```

主な画面:

- `/` — Home
- `/pages/equipment-sets` — Equipment Set一覧
- `/pages/equipment-sets/new` — Equipment Set作成
- `/pages/equipment-sets/{id}/edit` — Equipment Set編集
- `/pages/logs` — Brew Log一覧
- `/pages/logs/new` — Brew Log + Evaluation作成
- `/pages/logs/{id}` — Brew Log詳細、snapshot、Evaluation、Recommendation
- `/pages/logs/{id}/recommendation` — Recommendation詳細

ExternalBenchmarkには一覧・作成画面があります。

- `/pages/benchmarks`
- `/pages/benchmarks/new`

## Technology

- Python 3.12
- FastAPI
- Pydantic v2
- SQLite
- Jinja2
- pytest
- GitHub Actions

フロントエンドはCurrent MVPではJinja2 + 最小限のJavaScriptです。React / Next.jsは使用していません。

## Data Model

### EquipmentSet

抽出器具の組み合わせを管理します。

主な項目:

- `name`
- `filter_label`
- `brewer_label`
- `grinder_label`
- `grind_setting_unit`
- `note`
- `is_active`

DELETEは物理削除ではなく、`is_active = false` にするsoft deleteです。

### BrewLog

抽出条件を保存します。

主な項目:

- `brewed_at`
- `equipment_set_id`
- `bean_label`
- `dose_g`
- `water_g`
- `water_temp_c`
- `grind_setting_value`
- `bloom_time_s`
- `agitation_level`
- `pours`
- `finish_pouring_s`
- `brew_end_s`

BrewLog保存時にEquipmentSetの表示用情報をsnapshotとして保存します。後からEquipmentSetを編集・非表示化しても、過去ログのsnapshotは変わりません。

### Evaluation

BrewLogと1対1です。

```sql
UNIQUE (brew_log_id)
```

主な項目:

- `confidence`
- `overall_score`
- `taste_defect`
- `aroma_defect`
- `aftertaste_defect`
- `texture_defect`
- `memo`

BrewLog削除時はSQLite Foreign Keyの `ON DELETE CASCADE` によりEvaluationも削除されます。

### ExternalBenchmark

カフェ等で飲んだ外部基準のscoreを、Evaluationと同じ1〜10尺度で記録します。

Recommendationの入力には使用しません。

## API

### EquipmentSet

```text
GET    /equipment-sets
POST   /equipment-sets
GET    /equipment-sets/{equipment_set_id}
PATCH  /equipment-sets/{equipment_set_id}
DELETE /equipment-sets/{equipment_set_id}
```

### BrewLog

```text
GET    /logs
POST   /logs
GET    /logs/{log_id}
PATCH  /logs/{log_id}
DELETE /logs/{log_id}
```

`POST /logs` はBrewLogとEvaluationを1つのrequestで受け取り、同一transactionで保存します。

Response:

```json
{
  "brew_log": {},
  "evaluation": {}
}
```

`GET /logs` は次の順序で返します。

```text
brewed_at DESC, id DESC
```

### Evaluation

```text
GET   /logs/{log_id}/evaluation
PATCH /logs/{log_id}/evaluation
```

Evaluation単体のPOST endpointはありません。BrewLog作成時に同時作成します。

### Recommendation

```text
GET /recommendations/latest
GET /logs/{log_id}/recommendation
```

RecommendationはDBへ保存せず、BrewLog + Evaluationから決定的に計算します。

Decision priority:

1. `confidence = 1`
2. primary `taste_defect`
3. `aroma_defect`
4. `aftertaste_defect`
5. `texture_defect`
6. 欠点なし + `overall_score >= 8`
7. その他

返すactionは常に1つです。

実行不能なRecommendationは次へfallbackします。

```text
recommendation_mode = experiment
action_type = keep_same
direction = none
amount = 0
unit = none
```

例:

- 99℃から+2℃を提案しない
- agitation level 0から-1を提案しない
- `grind_setting_unit = other` で数値的な±1を提案しない
- grind setting value未入力時にgrind adjustmentを提案しない

### ExternalBenchmark

```text
GET    /benchmarks
POST   /benchmarks
GET    /benchmarks/{benchmark_id}
DELETE /benchmarks/{benchmark_id}
GET    /benchmarks/trends/score
```

`GET /benchmarks/trends/score` は次のfieldsを `consumed_at ASC, id ASC` で返します。

- `benchmark_id`
- `consumed_at`
- `product_name`
- `overall_score`

## Validation and PATCH Semantics

必須文字列はtrim後にvalidationします。空文字は422です。

対象例:

- EquipmentSetの `name`, `filter_label`, `brewer_label`, `grinder_label`
- BrewLogの `bean_label`
- ExternalBenchmarkの `product_name`

BrewLog domain validationの例:

- `water_temp_c` は0より大きく100以下
- `agitation_level` は0〜3
- `pours.at_s` は単調増加
- pours合計と `water_g` の差は0.5g以内
- `finish_pouring_s` は最終pour以降
- `brew_end_s` はfinish以降

PATCHでは「省略」と「明示的なnull」を区別します。

- field omitted: 現在値を維持
- nullable fieldの明示的null: 値をクリア
- non-nullable fieldのnull: 422
- 空PATCH: 400

BrewLog / Evaluation PATCHは、既存値とpatch値をmergeした完全resourceを再validationしてから保存します。

例えば `water_g` だけ変更してpours合計と不整合になる場合は422です。

## Datetime

- API datetimeはRFC 3339 / ISO 8601
- `brewed_at` は必須
- timezone offsetなしの `brewed_at` は422
- `brewed_at` はUTCへ正規化して保存
- responseの `brewed_at`, `created_at`, `updated_at` はUTCとして返す
- `consumed_at` はdateとして扱う

SQLiteへdatetime/dateを書き込む際はISO文字列へ明示的にserializeしています。

## Database Integrity

SQLite接続ごとにForeign Keyを有効化します。

```sql
PRAGMA foreign_keys = ON;
```

主なDB制約:

- EquipmentSet 1 : N BrewLog
- BrewLog 1 : 1 Evaluation
- `UNIQUE(evaluations.brew_log_id)`
- BrewLog削除時のEvaluation cascade
- Evaluation confidence / score整合性
- 各enum相当値のCHECK制約

## Local Run

Python 3.12を想定しています。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Windows PowerShellの場合:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

起動時にSQLite schemaを自動初期化します。

- Web UI: `http://127.0.0.1:8000/`
- OpenAPI docs: `http://127.0.0.1:8000/docs`

## Tests

Development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run:

```bash
python -m pytest -q
```

テストでは以下を含むSubmission-critical behaviorを確認しています。

- Evaluation GET / PATCH
- PATCH omitted / null semantics
- Evaluation merge validation
- BrewLog merge validation
- BrewLog + Evaluation transaction rollback
- BrewLog削除時のEvaluation cascade
- BrewLog list ordering
- latest Recommendation ordering
- Recommendation feasibility fallback
- EquipmentSet required-string trim
- UTC normalization
- ExternalBenchmark score trend schema / ordering
- Core Vertical Slice Jinja pages

## CI / Reproducibility

`.github/workflows/tests.yml` でpush / pull requestごとに次を実行します。

1. clean checkout
2. Python 3.12 setup
3. dependency install
4. `compileall`
5. pytest
6. uvicorn startup smoke test
7. `GET /equipment-sets` が200を返すことを確認

2026-09-27時点の最新確認では、CIで20 testsがpassし、clean checkoutからuvicorn起動まで成功しています。

## Repository Structure

```text
.
├── main.py
├── models.py
├── database.py
├── recommendation.py
├── requirements.txt
├── requirements-dev.txt
├── templates/
├── static/
├── tests/
└── .github/workflows/tests.yml
```

責務:

- `main.py`: FastAPI routes / Jinja pages / DB操作のapplication layer
- `models.py`: request / response schemaとdomain validation
- `database.py`: SQLite connection / schema
- `recommendation.py`: 決定的なRecommendation rule
- `tests/`: API、domain、integrity、submission acceptance tests

## Current MVP Boundary

このMVPには次を含めません。

- authentication / multi-user
- AI recommendation
- React / Next.js
- PostgreSQL
- Docker
- cloud deployment
- Experiment table / experiment chain
- automatic diff
- advanced analytics

これらはSubmission readinessの前提ではありません。

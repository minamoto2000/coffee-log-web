# Coffee Log Web

コーヒー抽出の条件と測定結果の関係を、自分の器具で検証するためのFastAPI製Webアプリです。

このリポジトリは一社目のBackend / Web Engineer就活で提示する主成果物です。API設計、Pydantic validation、SQLiteの参照整合性、transaction、PATCH semantics、テストを説明できる状態を目的にしています。

## Status: 再設計への移行中

2026-11-04に開発目的を「抽出記録と改善提案」から「抽出の実験・測定・検証」へ変更しました。理由は次の3点です。

1. 多様な抽出方法を、抽出全体に固定したパラメータで表現することに限界がある
2. 科学的根拠が不十分な改善提案を中心機能にしない
3. 条件を変えたときの影響を、TDSなどの測定で自分で確かめられるようにする

新しいCore Vertical Sliceは次のとおりです。画面とAPIの両方で一通り動作します。

```text
実験作成（2条件＋抽出工程）
→ 試行記録（TDS・飲料重量・官能評価）
→ 条件比較（記述統計・ばらつき・注意）
```

移行はPR単位で進め、各PRはテストが通る状態で閉じます。

- 完了：ルールベースRecommendationとExternalBenchmarkの削除、`app/` パッケージへの分割、domainの純粋関数、新テーブル、実験・試行・比較のAPIと画面
- 最後：旧ドメイン（BrewLog / Evaluation）の撤去とREADMEの全面改稿

移行前の版（記録＋ルールベース改善提案）はタグ `legacy-v1-recommendation` で参照できます。

### 現在動作する機能

新しいAPI（詳細は `/docs` のOpenAPI）:

```text
POST   /experiments                         実験＋2条件＋工程を作成
GET    /experiments/{id}                    条件差分・試行の要約・次の条件
PUT    /conditions/{id}/protocol            計画の置換（試行後は409）
POST   /conditions/{id}/trials              試行＋TDS測定＋官能評価を記録
GET    /trials/{id}                         実測値と派生値（TDS平均・EY・焙煎後日数）
GET    /experiments/{id}/comparison         条件比較（記述統計・2種のばらつき・注意）
```

新しい画面:

- `/pages/experiments` — 実験一覧
- `/pages/experiments/new` — 実験作成（条件Aの工程を入力し、Bへ複製して1か所だけ変える。差分を即時表示）
- `/pages/experiments/{id}` — 実験詳細（A・Bの工程と差分の強調、試行一覧、次に淹れる条件）
- `/pages/experiments/{id}/trials/new` — 試行の記録（次の条件を初期選択、TDSの複数回測定、官能評価）
- `/pages/trials/{id}` — 試行の詳細と編集（派生値、除外・逸脱、TDS測定の追加・削除、官能評価）
- `/pages/experiments/{id}/comparison` — 条件比較

旧ドメインの画面（移行の最終段階で撤去）:

- `/` — Home
- `/pages/equipment-sets` — Equipment Set一覧
- `/pages/equipment-sets/new` — Equipment Set作成
- `/pages/equipment-sets/{id}/edit` — Equipment Set編集
- `/pages/logs` — Brew Log一覧
- `/pages/logs/new` — Brew Log + Evaluation作成
- `/pages/logs/{id}` — Brew Log詳細、snapshot、Evaluation

## Technology

- Python 3.12
- FastAPI
- Pydantic v2
- SQLite
- Jinja2
- pytest
- GitHub Actions

フロントエンドはJinja2 + 最小限のJavaScriptです。React / Next.jsは使用していません。

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

## API

### EquipmentSet

```text
GET    /equipment-sets
POST   /equipment-sets
GET    /equipment-sets/{equipment_set_id}
PATCH  /equipment-sets/{equipment_set_id}
DELETE /equipment-sets/{equipment_set_id}
```

`POST` は201 Createdを返します。`DELETE` は物理削除ではなくsoft deleteです。

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

## Validation and PATCH Semantics

必須文字列はtrim後にvalidationします。空文字は422です。

対象例:

- EquipmentSetの `name`, `filter_label`, `brewer_label`, `grinder_label`
- BrewLogの `bean_label`

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

SQLiteへdatetimeを書き込む際はISO文字列へ明示的にserializeしています。

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
uvicorn app.main:app --reload
```

Windows PowerShellの場合:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
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
- EquipmentSet required-string trim
- EquipmentSet PATCH / soft delete（空PATCHは400、非表示後は404）
- UTC normalization
- 主要Jinja画面の表示

## CI / Reproducibility

`.github/workflows/tests.yml` でpush / pull requestごとに次を実行します。

1. clean checkout
2. Python 3.12 setup
3. dependency install
4. `compileall`
5. pytest
6. uvicorn startup smoke test
7. `GET /equipment-sets` が200を返すことを確認

## Repository Structure

```text
.
├── app/
│   ├── main.py            # FastAPIアプリの組み立て（router登録、例外ハンドラ、static）
│   ├── db.py              # SQLite接続（foreign_keys = ON）とschema初期化
│   ├── errors.py          # service層の業務エラーと、HTTP status への対応付け
│   ├── templating.py      # Jinja2の設定
│   ├── schemas/           # request / response schemaとvalidation
│   ├── repositories/      # SQL（connectionを受け取り、transactionは持たない）
│   ├── services/          # 業務規則とtransaction境界
│   ├── routers/           # HTTP API と画面のroute
│   └── legacy/            # 旧BrewLog / Evaluation（移行の最終段階で撤去）
├── templates/
├── static/
├── tests/
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
└── .github/workflows/tests.yml
```

層の責務:

- router：HTTPの入出力だけを扱い、serviceを呼ぶ
- service：存在確認・更新可否などの業務規則と、transactionの範囲を決める。HTTPに依存せず、`NotFoundError` などの業務エラーを送出する
- repository：SQLだけを持つ。PATCHで更新できる列は許可リストで限定する
- `errors.py`：業務エラーを404・400などへ変換する。応答形式は `{"detail": "..."}`

`app/legacy/` の旧BrewLog / Evaluationは移行前の構造のまま残しており、新しい層の規約には従っていません。

## Out of Scope

再設計後も次は対象外です。

- authentication / multi-user
- AIによる改善提案・自動最適化
- 測定器との自動連携
- 統計的仮説検定による「効果あり」の判定
- React / Next.js、PostgreSQL、Docker、cloud deployment

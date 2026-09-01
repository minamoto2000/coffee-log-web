# coffee-log-web

ハンドドリップの抽出条件、評価、改善提案を構造化して扱うWebアプリです。

## READMEの読み方

このREADMEでは、次の3つを分離して扱います。

1. `Current MVP Target`：現在完成させるMVPの目標仕様
2. `Implementation status`：実装済み判定に関するルール
3. `Post-MVP Product Direction`：MVP完成後の未実装構想

重要：READMEに書かれたTarget SpecificationやPost-MVP構想を、そのまま実装済みとは扱いません。

実装済み判定の正本は、このリポジトリの実コード、テスト、テンプレート、ディレクトリ構成です。

MVP範囲の正本は `career-management-private/01b_Portfolio_MVP_Spec.md` です。

---

# Current MVP Target

## 1. MVPの目的

### Core Vertical Slice

```text
用具セット登録
→ 抽出ログ登録
→ 評価登録
→ 改善提案を1つ表示
```

### Additional MVP feature

```text
ExternalBenchmarkを記録
→ 同一尺度のscore trendを表示
```

ExternalBenchmarkはCore Vertical Sliceとは独立したMVP機能です。

Current MVPの主目的は、FastAPI / Pydantic / SQLite / CRUD / validation / Recommendationを一貫した設計として実装し、説明・テストできる状態にすることです。

Post-MVPの差別化機能を理由にCurrent MVPを広げません。

## 2. MVPで扱うもの

- EquipmentSetの登録・一覧・編集・非表示化
- BrewLog + Evaluationの登録
- BrewLogの一覧・詳細・編集・削除
- Evaluationの取得・編集
- 指定ログまたは直近ログに対するRecommendation
- ExternalBenchmarkの登録・一覧・削除
- ExternalBenchmarkのscore trend
- DB制約、validation、HTTPエラー
- Acceptance Criteriaを検証するテスト
- ローカル実行手順と設計説明

## 3. MVPで扱わないもの

- 認証、多ユーザー対応
- AI推薦、AI提案履歴
- 豆マスタ
- レシピテンプレート
- Experimentテーブル
- 前回ログ複製
- Automatic diff
- confounder判定
- Experiment chain
- relative_result
- Brew Mode
- 複数ログを使った高度分析
- 複雑なグラフ
- React / Next.js化
- PostgreSQL
- Docker
- デプロイ

---

## 4. データモデル

### EquipmentSet

よく使う用具の組み合わせを保存し、BrewLog作成時に再利用します。

```text
EquipmentSet
- id
- name
- brewer_label
- filter_label
- grinder_label
- grind_setting_unit
- note
- is_active
- created_at
- updated_at
```

`DELETE` は物理削除ではなく `is_active=false` とするsoft deleteです。

EquipmentSetを後から編集・非表示化しても、過去BrewLogのsnapshotは変更しません。

### BrewLog

```text
BrewLog
- id
- brewed_at
- equipment_set_id
- equipment_set_name_snapshot
- brewer_label_snapshot
- filter_label_snapshot
- grinder_label_snapshot
- grind_setting_unit_snapshot
- bean_label
- dose_g
- water_g
- water_temp_c
- grind_setting_value
- bloom_time_s
- agitation_level
- pours
- finish_pouring_s
- brew_end_s
- note
- created_at
- updated_at
```

EquipmentSetは参照IDだけでなく、保存時点の情報をsnapshotとしてBrewLogへコピーします。

### Evaluation

```text
BrewLog 1 - 1 Evaluation
```

DBでも1:1を保証します。

```sql
UNIQUE (brew_log_id)
```

```text
Evaluation
- id
- brew_log_id
- confidence
- overall_score
- taste_defect
- aroma_defect
- aftertaste_defect
- texture_defect
- memo
- created_at
- updated_at
```

`taste_defect` はMVPでは「primary taste defect」として扱います。

```text
none
thin
sour
bitter
not_sweet
```

複数の味欠点を感じた場合も、改善時に最優先したい欠点を1つ選びます。

### ExternalBenchmark

```text
ExternalBenchmark
- id
- consumed_at
- source_type
- product_name
- overall_score
- note
- created_at
- updated_at
```

`ExternalBenchmark.overall_score` は `Evaluation.overall_score` と同じ1〜10尺度を使用します。

ExternalBenchmarkはRecommendationの入力には使いません。

---

## 5. poursの仕様

`pours[].grams` は「その投で追加した湯量」です。スケール上の累積重量ではありません。

```json
[
  {"grams": 60, "at_s": 0},
  {"grams": 60, "at_s": 45},
  {"grams": 60, "at_s": 90},
  {"grams": 60, "at_s": 135}
]
```

- `grams`：その投で追加した湯量[g]
- `at_s`：抽出開始から、その投を開始した時刻[秒]

MVPではJSONとしてBrewLogへ保存します。

---

## 6. Validation

### EquipmentSet

- name：必須、trim後に空文字不可
- brewer_label：必須、trim後に空文字不可
- filter_label：必須、trim後に空文字不可
- grinder_label：必須、trim後に空文字不可
- grind_setting_unit：`click / step / number / other`

### BrewLog

```text
brewed_at は必須かつtimezone offset付き
equipment_set_id >= 1
dose_g > 0
water_g > 0
0 < water_temp_c <= 100
grind_setting_value >= 0  // 入力時
bloom_time_s >= 0
0 <= agitation_level <= 3
pours.length >= 1
pours[].grams > 0
pours[].at_s >= 0
```

- bean_label：必須、trim後に空文字不可

さらに次を満たします。

```text
pours[].at_s は配列順に狭義単調増加
abs(sum(pours[].grams) - water_g) <= 0.5g
finish_pouring_s >= 最後のpours[].at_s
brew_end_s >= finish_pouring_s
```

### Evaluation

```text
1 <= confidence <= 3
1 <= overall_score <= 10  // 入力時
```

- confidence = 1：overall_scoreは任意
- confidence = 2 or 3：overall_score必須
- taste_defect：定義済みenumのみ
- aroma_defect / aftertaste_defect / texture_defect：boolean

### ExternalBenchmark

- consumed_at：必須date
- source_type：`cafe / convenience_store / other`
- product_name：必須、trim後に空文字不可
- overall_score：`1..10`

---

## 7. API Request / Response Schema

### EquipmentSetCreate

```text
EquipmentSetCreate
- name: str
- brewer_label: str
- filter_label: str
- grinder_label: str
- grind_setting_unit: click | step | number | other
- note: str | null
```

### EquipmentSetUpdate

```text
EquipmentSetUpdate
- name?
- brewer_label?
- filter_label?
- grinder_label?
- grind_setting_unit?
- note?
```

### EquipmentSetResponse

```text
EquipmentSetResponse
- EquipmentSetの全保存項目
```

### PourItem

```text
PourItem
- grams: float
- at_s: int
```

### BrewLogCreate

```text
BrewLogCreate
- brewed_at: datetime
- equipment_set_id: int
- bean_label: str
- dose_g: float
- water_g: float
- water_temp_c: float
- grind_setting_value: float | null
- bloom_time_s: int
- agitation_level: int
- pours: list[PourItem]
- finish_pouring_s: int
- brew_end_s: int
- note: str | null
```

`brewed_at` は実際に抽出した日時を表すドメインデータであり必須です。API受信時刻で補完せず、timezone offset付きdatetimeを要求します。

### EvaluationCreate

```text
EvaluationCreate
- confidence: int
- overall_score: int | null
- taste_defect: enum
- aroma_defect: bool
- aftertaste_defect: bool
- texture_defect: bool
- memo: str | null
```

### BrewLogCreateRequest

`POST /logs` はnested requestを受け取ります。

```json
{
  "brew_log": {
    "brewed_at": "2026-09-01T03:00:00+09:00",
    "equipment_set_id": 1,
    "bean_label": "Ethiopia Guji",
    "dose_g": 15,
    "water_g": 240,
    "water_temp_c": 92,
    "grind_setting_value": 20,
    "bloom_time_s": 45,
    "agitation_level": 1,
    "pours": [
      {"grams": 60, "at_s": 0},
      {"grams": 60, "at_s": 45},
      {"grams": 60, "at_s": 90},
      {"grams": 60, "at_s": 135}
    ],
    "finish_pouring_s": 160,
    "brew_end_s": 210,
    "note": null
  },
  "evaluation": {
    "confidence": 3,
    "overall_score": 8,
    "taste_defect": "none",
    "aroma_defect": false,
    "aftertaste_defect": false,
    "texture_defect": false,
    "memo": null
  }
}
```

BrewLogとEvaluationは1トランザクションで保存します。

### BrewLogCreateResponse

`POST /logs` は作成した2resourceをnested responseで返します。

```text
BrewLogCreateResponse
- brew_log: BrewLogResponse
- evaluation: EvaluationResponse
```

### BrewLogUpdateRequest

PATCH可能なフィールドは次に限定します。

```text
BrewLogUpdateRequest
- brewed_at?
- bean_label?
- dose_g?
- water_g?
- water_temp_c?
- grind_setting_value?
- bloom_time_s?
- agitation_level?
- pours?
- finish_pouring_s?
- brew_end_s?
- note?
```

`equipment_set_id` とsnapshot fieldsはPATCH対象にしません。

EquipmentSetを変更した別抽出として記録したい場合は、新しいBrewLogを作成します。

### EvaluationUpdateRequest

```text
EvaluationUpdateRequest
- confidence?
- overall_score?
- taste_defect?
- aroma_defect?
- aftertaste_defect?
- texture_defect?
- memo?
```

### ExternalBenchmarkCreate

```text
ExternalBenchmarkCreate
- consumed_at: date
- source_type: cafe | convenience_store | other
- product_name: str
- overall_score: int
- note: str | null
```

### PATCH null semantics

PATCHではfield omittedとfield explicitly set to `null` を区別します。

- field omitted：その値を変更しない
- nullable fieldへ明示的に`null`を指定：その値をクリアする

対象例は `note`、`memo`、`grind_setting_value`、`overall_score` です。merge後の完全resourceがdomain validationに違反する場合は422とします。

### PATCH merge validation

PATCHは送信フィールド単体ではなく、既存値とmergeした後の完全resourceをvalidationします。

```text
existing resource
+ patch fields
→ merged complete resource
→ domain validation
→ save
```

例：

```text
existing water_g = 240
existing pours sum = 240
PATCH water_g = 250
```

merge後は不整合なので `422` です。

Evaluationも同様です。

```text
existing confidence = 1
existing overall_score = null
PATCH confidence = 3
```

merge後に `confidence=3 / overall_score=null` となるため `422` です。

### Response Schema

```text
BrewLogResponse
- BrewLogの全保存項目
- id
- created_at
- updated_at

EvaluationResponse
- Evaluationの全保存項目
- id
- created_at
- updated_at

RecommendationResponse
- target_log_id
- recommendation_mode
- action_type
- direction
- amount
- unit
- message
- reason

ExternalBenchmarkResponse
- ExternalBenchmarkの全保存項目
- id
- created_at
- updated_at

BenchmarkScoreTrendItem
- benchmark_id
- consumed_at
- product_name
- overall_score
```

`GET /benchmarks/trends/score` は `list[BenchmarkScoreTrendItem]` を `consumed_at` 昇順で返します。

---

## 8. Recommendation

### 基本方針

MVPではRecommendationを保存しません。

```text
recommendation = f(brew_log, evaluation)
```

同じBrewLogとEvaluationには同じ結果を返す決定的なルールベース関数です。

入力：

- BrewLog
- Evaluation

入力しないもの：

- 過去ログ
- ExternalBenchmark
- AI出力

返すRecommendationは常に1アクションです。

### Decision Table

優先順位：

```text
1. confidence = 1
2. taste_defect
3. aroma_defect
4. aftertaste_defect
5. texture_defect
6. 欠点なし + high score
7. その他
```

| 条件 | action_type | direction | amount | unit | mode |
| --- | --- | --- | ---: | --- | --- |
| confidence = 1 | keep_same | none | 0 | none | experiment |
| taste_defect = thin | adjust_grind | finer | 1 | selected grind unit | normal* |
| taste_defect = sour | adjust_water_temp | increase | 2 | celsius | normal* |
| taste_defect = bitter | adjust_water_temp | decrease | 2 | celsius | normal* |
| taste_defect = not_sweet | adjust_grind | finer | 1 | selected grind unit | normal* |
| aroma_defect = true | adjust_water_temp | increase | 2 | celsius | normal* |
| aftertaste_defect = true | adjust_grind | coarser | 1 | selected grind unit | normal* |
| texture_defect = true | adjust_agitation | decrease | 1 | level | normal* |
| 欠点なし + overall_score >= 8 | keep_same | none | 0 | none | normal |
| その他 | keep_same | none | 0 | none | experiment |

`normal*` は次をすべて満たす場合だけmodeを `strong` に上書きします。

```text
confidence = 3
overall_score <= 3
何らかの欠点が存在する
```

### Feasibility rules

Decision Tableで候補actionを作成した後、実行可能性を検証します。

- 有効範囲外への変更を提案しない
- `water_temp_c + amount > 100` になるtemperature increaseは提案しない
- `water_temp_c - amount <= 0` になるtemperature decreaseは提案しない
- `agitation_level - amount < 0` になるdecreaseは提案しない
- `agitation_level + amount > 3` になるincreaseは提案しない
- grind_setting_valueが未入力ならadjust_grindを提案しない
- `grind_setting_unit = other` では数値的な±1相当のgrind adjustmentを提案しない

実行不能なら、MVPでは複雑な代替action探索を行わず次へfallbackします。

```text
recommendation_mode = experiment
action_type = keep_same
direction = none
amount = 0
unit = none
```

Recommendationはコーヒー抽出の絶対法則として扱いません。「可能性がある」「次回は1点だけ試す」のように表示し、原因を断定しません。

---

## 9. Target API

ここに書くAPIはCurrent MVPの目標契約です。実装済み判定は実コードを確認してください。

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

`GET /logs` は `brewed_at DESC, id DESC` で返します。

### Evaluation

```text
GET   /logs/{log_id}/evaluation
PATCH /logs/{log_id}/evaluation
```

BrewLog作成時にEvaluationも同時作成するため、別のEvaluation POSTは持ちません。

### Recommendation

Recommendationは保存しないためGETだけです。

```text
GET /recommendations/latest
GET /logs/{log_id}/recommendation
```

`latest BrewLog` は `brewed_at` が最大のBrewLogです。同一 `brewed_at` の場合は `id` が大きい方を優先します。

`POST /logs/{log_id}/recommendation` は定義しません。

### ExternalBenchmark

```text
GET    /benchmarks
POST   /benchmarks
GET    /benchmarks/{benchmark_id}
DELETE /benchmarks/{benchmark_id}
GET    /benchmarks/trends/score
```

`/benchmarks/trends/score` は、動的な `/{benchmark_id}` と衝突しないpath構造にしています。

---

## 10. DB制約と削除規則

### Relation

```text
EquipmentSet 1 - n BrewLog
BrewLog      1 - 1 Evaluation
```

SQLiteではForeign Keyを有効化します。

```sql
PRAGMA foreign_keys = ON;
```

EvaluationはDBでも1:1を保証します。

```sql
UNIQUE (brew_log_id)
```

### Delete policy

- EquipmentSet：soft delete (`is_active=false`)
- BrewLog：Current MVPでは物理削除
- Evaluation：親BrewLog削除時に `ON DELETE CASCADE`
- ExternalBenchmark：物理削除

Post-MVPでExperimentがBrewLogを参照する段階では、BrewLogのsoft delete移行を再検討します。

---

## 11. Datetime

- API datetime：RFC 3339 / ISO 8601
- brewed_at：必須。実際に抽出した日時を表し、API受信時刻で補完しない
- brewed_at：timezone offset付き入力を必須とする
- 内部保存：UTCへ正規化
- created_at / updated_at：UTC
- APIレスポンス：`Z` または `+00:00` 付きUTC
- consumed_at：datetimeではなくdate

SQLiteでTEXT/TIMESTAMPを使う場合も、アプリ層ではtimezone-aware datetimeとして扱います。

---

## 12. HTTPエラー

| 状況 | Status |
| --- | ---: |
| Pydantic / domain validation error | 422 |
| Resource not found | 404 |
| inactive EquipmentSetをログ作成に使用 | 404 |
| PATCH対象フィールドなし | 400 |
| Evaluation重複など予期した競合 | 409 |
| Foreign Key等の予期した競合 | 409 |

予期しない例外を200系へ変換しません。

---

## 13. Acceptance Criteria

### EquipmentSet

- 正常入力で作成できる
- 必須文字列はtrim後に空文字なら422
- activeなものだけ一覧表示される
- 編集しても既存BrewLogのsnapshotが変化しない
- DELETE後は新規ログの選択肢から消える
- DELETE後も過去BrewLogは表示できる

### BrewLog + Evaluation create

- `BrewLogCreateRequest` のnested形式で作成できる
- `POST /logs` は `BrewLogCreateResponse` としてbrew_logとevaluationを返す
- brewed_at省略時は422
- timezone offsetなしbrewed_atは422
- BrewLogとEvaluationが同一トランザクションで保存される
- Evaluation保存失敗時にBrewLogだけ残らない
- inactive / nonexistent EquipmentSetでは作成できない
- snapshotが保存時点のEquipmentSetと一致する
- `UNIQUE(brew_log_id)` により1ログ1評価をDBで保証する
- pours / water / temperature / time validation違反を拒否する

### PATCH

- field omittedとexplicit nullを区別する
- nullable fieldへのexplicit nullは値のクリアを意味する
- BrewLog PATCHは既存値とmerge後の完全resourceをvalidationする
- water_gだけ変更してpours合計と不整合になれば422
- Evaluation PATCHもmerge後にvalidationする
- `confidence=1 / overall_score=null` からconfidenceだけ3へ変更した場合は422
- equipment_set_idとsnapshot fieldsはBrewLog PATCHで変更できない

### Recommendation

- 同じBrewLog + Evaluationには同じ結果を返す
- 常に1アクションだけ返す
- Decision Tableの主要分岐をunit testできる
- confidence=1では `keep_same / experiment`
- strong条件ではmodeだけ `strong` へ変わる
- feasibility違反時は `keep_same / experiment` へfallbackする
- water_temp_c=99かつsourで101℃を提案しない
- agitation_level=0で負値を提案しない
- grind_setting_unit=otherで数値的な±1提案をしない
- ExternalBenchmarkの追加・削除でRecommendationが変化しない
- `/recommendations/latest` は `brewed_at DESC, id DESC` の先頭ログを対象にする
- logが存在しなければ404
- Evaluationがなければ404
- POST recommendation endpointは存在しない

### Integrity

- BrewLog削除時にEvaluationも削除される
- EquipmentSetの非表示化でBrewLogは削除されない
- 孤児Evaluationを作成できない

### Datetime

- timezone offset付きbrewed_atを扱える
- brewed_at省略時は422
- timezone offsetなしbrewed_atは422
- 保存・レスポンスでUTCへ正規化される
- created_at / updated_atをUTCとして解釈できる

### ExternalBenchmark

- 作成・一覧・削除できる
- product_nameはtrim後に空文字なら422
- overall_scoreが1..10以外なら拒否する
- Evaluationと同一の評価尺度を使う
- `/benchmarks/trends/score` が `BenchmarkScoreTrendItem` の配列をconsumed_at昇順で返す
- Recommendationへ影響しない

---

## 14. Test targets

最低限、次をテスト対象にします。

- Pydantic validation
- required string trim validation
- BrewLogCreateRequest
- BrewLogCreateResponse
- BrewLog + Evaluation transaction
- BrewLog PATCH merge validation
- PATCH omitted/null semantics
- Evaluation PATCH merge validation
- Evaluation 1:1 constraint
- EquipmentSet snapshot
- EquipmentSet soft delete
- BrewLog delete cascade
- BrewLog list ordering
- Recommendation latest ordering
- Recommendation Decision Table
- Recommendation feasibility fallback
- strong mode
- ExternalBenchmarkがRecommendationへ影響しないこと
- BenchmarkScoreTrendItem response
- APIの400 / 404 / 409 / 422
- datetime normalization

---

# Implementation status

このREADMEのTarget Specificationと実装状況は別物です。

実装済みかどうかを判断するときは、以下を確認します。

- `main.py`
- `models.py`
- `database.py`
- `recommendation.py`
- `templates/`
- `static/`
- tests

READMEにAPIやモデルが書かれているだけでは、実装済みとは判定しません。

現時点の実装がこのTarget Specificationへ完全同期しているとは限りません。

---

## Local run

依存関係をインストールします。

```bash
pip install -r requirements.txt
```

FastAPIアプリを起動します。

```bash
uvicorn main:app --reload
```

主要オプション：

- `main:app`：`main.py` 内の `app` オブジェクトを起動対象にする
- `--reload`：開発中のファイル変更時に自動再起動する

---

# Post-MVP Product Direction — Not Implemented

> [!IMPORTANT]
> このセクションはMVP完成後の未実装構想です。
> `Experiment`、Automatic diff、Experiment chain、Brew Mode、複数ログ分析、AI補助などはCurrent MVPの完成条件に含めません。

## 1. プロダクトの中心価値

MVP完成後は、単なるコーヒー記録アプリではなく、反復実験を支援するアプリへ発展させます。

> 前回のハンドドリップを基準に1条件だけ変えて抽出し、その変更と味の変化を自動で比較・蓄積することで、自分の好みに合った再現可能な抽出条件を見つける。

専用アプリの価値は次の3点に置きます。

1. 入力摩擦を減らす
2. 抽出条件と評価を一貫した構造で保存する
3. 反復実験の差分と結果を自動比較する

## 2. MVP後の最優先プロダクト検証

Current MVP完成後、最初に検証するVertical Sliceはこれです。

```text
前回のBrewLogを複製
→ 1項目だけ変更
→ 新しいBrewLogを保存
→ baselineとの差分を表示
→ Evaluation結果を比較
```

この段階ではExperimentテーブル、AI、Brew Mode、高度分析は必須にしません。

目的は「1変数ずつ変更する実験体験に価値があるか」を最小追加で検証することです。

## 3. Experiment

将来的には「何を検証した抽出か」を第一級データとして扱います。

```text
Experiment
- baseline_log_id
- target_variable
- before_value
- after_value
- hypothesis
- candidate_log_id
- result
- score_delta
- comparability
```

予定していない条件まで変化した場合はconfounderとして扱い、因果解釈を弱めます。

## 4. 操作変数と観測結果

操作変数の例：

- grind_setting
- water_temp
- dose_g
- water_g
- bloom_time
- agitation
- pour_distribution
- pour_timing

観測結果の例：

- brew_end_s
- drawdown_s
- overall_score
- taste_defect
- aroma
- aftertaste
- texture

## 5. Relative evaluation

絶対点だけでなく、基準抽出に対する相対結果も扱います。

```text
relative_result
- better
- same
- worse
- uncertain
```

## 6. Automatic diff

基準ログとの差分を自動抽出し、変更点・観測結果・評価差を優先表示します。

予定外の変更があればcomparabilityを下げます。

## 7. Experiment chainと再現性

単発の最高点ではなく、探索履歴と再現性を扱います。

```text
candidate
→ promising
→ reproduced
```

アプリのゴールは「最高点を1回出すこと」ではなく「再現可能な勝ちパターンを見つけること」です。

## 8. 分析

価値の中心はグラフ描画ではなく、「比較してよいログを自動的に選ぶこと」に置きます。

可能な限り同じBean / Equipment / Dose / Water / Recipe条件の中から、対象変数だけが異なるログを比較します。

## 9. AIの役割

生成AIそのものと競争することは目的にしません。

アプリ側で管理するもの：

- 構造化データ
- validation
- 数値計算
- 比較対象抽出
- confounder判定
- Recommendationの構造

AIに任せる候補：

- 過去ログの傾向要約
- 仮説候補の整理
- 実験結果の自然言語説明
- Recommendation理由の補足

CSV / JSON / Markdown exportやAPIを通じて、Spreadsheet、ChatGPT、Python、Jupyterなど外部ツールへ持ち出せる構成を目指します。

---

## Specification freeze

Current MVPの仕様精緻化はここで一旦停止します。

MVP完成前の仕様変更は、実装不能な矛盾、テストで判明した仕様欠陥、データ整合性上の問題が見つかった場合を中心に行います。

新しいPost-MVP機能の詳細化より、Current MVPの実装とテストを優先します。

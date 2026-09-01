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

MVPでは、次のVertical Sliceを最小構成で成立させます。

```text
用具セット登録
→ 抽出ログ登録
→ 評価登録
→ 改善提案を1つ表示
→ 外部ベンチマークを記録・表示
```

この段階の主目的は、FastAPI / Pydantic / SQLite / CRUD / validation / recommendationを一貫した設計として実装し、説明・テストできる状態にすることです。

Post-MVPの差別化機能を理由にCurrent MVPを広げません。

## 2. MVPで扱うもの

- EquipmentSetの登録・一覧・編集・非表示化
- BrewLogの登録・一覧・詳細・編集・削除
- Evaluationの登録・取得・編集
- 指定ログまたは直近ログに対するRecommendation
- ExternalBenchmarkの登録・一覧・削除
- ExternalBenchmarkの簡易score trend
- DB制約、validation、HTTPエラー
- 主要Acceptance Criteriaのテスト
- ローカル実行手順と設計説明

## 3. MVPで扱わないもの

以下はCurrent MVPへ入れません。

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

よく使う用具の組み合わせを保存し、ログ入力を補助します。

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

EquipmentSetを後から編集・非表示化しても、過去ログの表示内容は変更しません。

### BrewLog

自宅抽出の条件を履歴として保存します。

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

EquipmentSetは参照IDだけでなく、保存時点の情報をsnapshotとしてBrewLog側にもコピーします。

これにより、EquipmentSetを後から編集しても過去の抽出履歴が変化しません。

### Evaluation

1つのBrewLogにつきEvaluationは1件だけです。

```text
BrewLog 1 - 1 Evaluation
```

DBでも次を保証します。

```sql
UNIQUE (brew_log_id)
```

保存項目：

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

#### taste_defectの意味

MVPではフィールド名を `taste_defect` のまま維持しますが、意味は「primary taste defect」です。

つまり、最も気になる味の欠点を1つ選びます。

```text
none
thin
sour
bitter
not_sweet
```

`thin` と `sour` のように複数感じた場合も、MVPでは改善時に最優先したい欠点を1つ選びます。

複数taste defectの保存はPost-MVPで必要性を再評価します。

### ExternalBenchmark

カフェ、コンビニ、その他のコーヒーを味覚尺度の参考として記録します。

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

ExternalBenchmarkはRecommendationの入力には使いません。

---

## 5. poursの仕様

`pours[].grams` は「その投で追加した湯量」です。

スケール上の累積重量ではありません。

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

- name：必須、空文字不可
- brewer_label：必須、空文字不可
- filter_label：必須、空文字不可
- grinder_label：必須、空文字不可
- grind_setting_unit：`click / step / number / other`

### BrewLog

```text
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

さらに次を満たす必要があります。

```text
pours[].at_s は配列順に単調増加
abs(sum(pours[].grams) - water_g) <= 0.5g
finish_pouring_s >= 最後のpours[].at_s
brew_end_s >= finish_pouring_s
```

`0.5g` の許容差は小数入力時の丸め差を吸収するためです。

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
- product_name：必須、空文字不可
- overall_score：`1..10`

---

## 7. Recommendation

### 基本方針

MVPではRecommendationを保存しません。

```text
recommendation = f(brew_log, evaluation)
```

同じBrewLogとEvaluationには同じ結果を返す、決定的なルールベース関数として扱います。

入力：

- BrewLog
- Evaluation

入力しないもの：

- 過去ログ
- ExternalBenchmark
- AI出力

返すRecommendationは常に1アクションです。

```json
{
  "target_log_id": 1,
  "recommendation_mode": "normal",
  "action_type": "adjust_water_temp",
  "direction": "decrease",
  "amount": 2,
  "unit": "celsius",
  "message": "次回は湯温を2℃下げる",
  "reason": "苦味が出ているため、抽出が強すぎる可能性がある"
}
```

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
| 欠点なし + overall_score < 8 / scoreなし | keep_same | none | 0 | none | experiment |

`normal*` は、次をすべて満たす場合だけmodeを `strong` に上書きします。

```text
confidence = 3
overall_score <= 3
何らかの欠点が存在する
```

strongでもaction自体は変えません。

Recommendationはコーヒー抽出の絶対法則として扱いません。「可能性がある」「次回は1点だけ試す」のように表示し、原因を断定しません。

---

## 8. Target API

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

`POST /logs` はBrewLogとEvaluationを1トランザクションで作成します。

Evaluation保存に失敗した場合、BrewLogだけを残しません。

### Evaluation

BrewLog作成時にEvaluationも同時作成するため、MVPでは別のEvaluation POSTは持ちません。

```text
GET   /logs/{log_id}/evaluation
PATCH /logs/{log_id}/evaluation
```

### Recommendation

Recommendationは保存しないためGETだけです。

```text
GET /logs/latest/recommendation
GET /logs/{log_id}/recommendation
```

`POST /logs/{log_id}/recommendation` はMVPでは定義しません。

### ExternalBenchmark

```text
GET    /benchmarks
POST   /benchmarks
GET    /benchmarks/{benchmark_id}
DELETE /benchmarks/{benchmark_id}
```

### Benchmark score trend

```text
GET /benchmarks/score-trend
```

---

## 9. DB制約と削除規則

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

将来要件だけを理由にCurrent MVPへ先行導入しません。

---

## 10. Datetime

日時は曖昧なローカル時刻として保存しません。

- API datetime：RFC 3339 / ISO 8601
- brewed_at：timezone offset付き入力を受け付ける
- 内部保存：UTCへ正規化
- created_at / updated_at：UTC
- APIレスポンス：`Z` または `+00:00` 付きUTC
- consumed_at：datetimeではなくdate

SQLiteでTEXT/TIMESTAMPを使う場合も、アプリ層ではtimezone-aware datetimeとして扱います。

---

## 11. HTTPエラー

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

## 12. Acceptance Criteria

### EquipmentSet

- 正常入力で作成できる
- activeなものだけ一覧表示される
- 編集しても既存BrewLogのsnapshotが変化しない
- DELETE後は新規ログの選択肢から消える
- DELETE後も過去BrewLogは表示できる

### BrewLog + Evaluation

- 正常入力でBrewLogとEvaluationが同一操作で保存される
- Evaluation保存失敗時にBrewLogだけ残らない
- inactive / nonexistent EquipmentSetでは作成できない
- snapshotが保存時点のEquipmentSetと一致する
- `UNIQUE(brew_log_id)` により1ログ1評価をDBで保証する
- validation違反を拒否する
- `pours[].grams` を各投の増分として保存する
- poursの時刻が昇順でない場合は拒否する
- pours合計とwater_gが許容差を超える場合は拒否する
- `brew_end_s < finish_pouring_s` は拒否する

### Recommendation

- 同じBrewLog + Evaluationには同じ結果を返す
- 常に1アクションだけ返す
- Decision Tableの主要分岐をunit testできる
- confidence=1では `keep_same / experiment`
- strong条件ではmodeだけ `strong` へ変わる
- ExternalBenchmarkの追加・削除でRecommendationが変化しない
- logが存在しなければ404
- Evaluationがなければ404
- POST recommendation endpointは存在しない

### Integrity

- BrewLog削除時にEvaluationも削除される
- EquipmentSetの非表示化でBrewLogは削除されない
- 孤児Evaluationを作成できない

### Datetime

- timezone offset付きbrewed_atを扱える
- 保存・レスポンスでUTCへ正規化される
- created_at / updated_atをUTCとして解釈できる

### ExternalBenchmark

- 作成・一覧・削除できる
- overall_scoreが1..10以外なら拒否する
- score trendを表示できる
- Recommendationへ影響しない

---

## 13. Test targets

最低限、次をテスト対象にします。

- Pydantic validation
- BrewLog + Evaluation transaction
- Evaluation 1:1 constraint
- EquipmentSet snapshot
- EquipmentSet soft delete
- BrewLog delete cascade
- Recommendation Decision Table
- strong mode
- ExternalBenchmarkがRecommendationへ影響しないこと
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

単なる差分だけでなく、予定していた変数以外も変化していないかを確認します。

意図しない変更があればconfounderとして扱い、因果解釈を弱めます。

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

例：

```text
操作
Grind: 22 → 20 click

観測
Drawdown: 35s → 52s

結果
Score: 6 → 8
```

## 5. 入力摩擦の削減

空フォームから毎回入力するのではなく、既存条件の複製を基本にします。

入口候補：

- 最新の抽出から淹れる
- ベスト候補から淹れる
- レシピテンプレートから淹れる

ユーザーは全条件ではなく「今回何を変えるか」に集中できる状態を目指します。

## 6. Brew Mode

抽出中はCRUDフォームではなく専用画面を使う構想です。

```text
00:00
次: 60g
[ POUR ]

00:46
次: 60g
[ POUR ]

...

[ BREW END ]
```

タイマー操作からpoursの時刻を生成し、後から手入力する量を減らします。

Bluetooth対応スケール等との連携はさらに後の候補であり、初期Post-MVPには必須としません。

## 7. Relative evaluation

絶対評価に加え、baselineに対する相対評価を持たせる構想です。

```text
relative_result
- better
- same
- worse
- uncertain
```

絶対スコアの日ごとの揺れを補い、「前回より良かったか」を反復実験の結果として残します。

## 8. Automatic diff

ログ詳細では全項目を並べるだけでなく、baselineとの差分を最優先で表示します。

```text
変更
Grind        22 → 20 click

ほぼ同一
Dose         15g
Water        240g
Temp         92℃

結果
Score        6 → 8
Drawdown     38s → 51s
Thin         yes → no
```

予定外の変更はconfounderとして表示します。

## 9. Experiment chain

ログを単独の記録ではなく、探索の流れとして表示します。

```text
#31  22 click / Score 6 / thin
  ↓ grind finer
#32  20 click / Score 8 / none
  ↓ repeat
#33  20 click / Score 8 / none
  ↓ temp -2℃
#34  20 click / 90℃ / Score 7 / sour
  ↓ revert
#35  20 click / 92℃ / Score 9 / none
```

## 10. 再現可能な成功パターン

単発の最高点をそのままBestとは扱いません。

候補条件：

- overall_score >= 8
- confidence >= 2
- 同一または十分近い抽出条件
- 複数回で良好な結果を再現
- 重大な欠点が継続していない

状態例：

```text
candidate
↓
promising
↓
reproduced
```

目的は最高点を1回出すことではなく、「再現可能な勝ちパターン」を見つけることです。

## 11. 分析

Spreadsheetでも単純なグラフは作れます。

そのため専用アプリでは、グラフ描画そのものではなく「比較してよいログを自動的に選ぶこと」を重視します。

例えば湯温比較では、可能な限り次を揃えます。

- 同じ豆
- 同じ用具セット
- 同じ粉量
- 同じ湯量
- 同じレシピ系統

その上で湯温だけが異なるログを比較します。

## 12. Recommendationの将来優先順位

```text
1. 再現確認
2. 過去の比較可能な実験結果
3. 現在の欠点
4. 一般的なルールベース
5. AIによる補足説明
```

1回改善しただけなら、さらに別条件を変更するより再現確認を優先します。

## 13. AIの役割

生成AIそのものと競争することは目的にしません。

アプリはAIが扱いやすい構造化済み実験データの正本として機能させます。

AIに任せる候補：

- 過去ログの傾向要約
- 仮説候補の整理
- 実験結果の自然言語説明
- Recommendation理由の補足

アプリ側で管理するもの：

- データ正規化
- validation
- 数値計算
- 比較対象抽出
- confounder判定
- action_type / direction / amount / unit

CSV / JSON / Markdown exportやAPIを通じ、Spreadsheet、ChatGPT、Claude、Python、Jupyterなど外部ツールへ持ち出せる構成を目指します。

## 14. 将来データモデル案

```text
EquipmentSet
Bean
RecipeTemplate

Experiment
├─ baseline_log_id
├─ target_variable
├─ target_value
├─ hypothesis
├─ candidate_log_id
└─ status

BrewLog
├─ experiment_id
├─ equipment snapshot
├─ bean snapshot
├─ recipe snapshot
├─ manipulated variables
├─ observed variables
└─ timestamps

BrewPour
├─ brew_log_id
├─ order
├─ target_grams
├─ actual_grams
└─ at_s

Evaluation
├─ overall_score
├─ relative_result
├─ confidence
├─ defects
└─ memo

BrewComparison
├─ changed_variables
├─ confounders
├─ score_delta
├─ observation_delta
└─ comparability

Recommendation
AIRecommendationLog
```

`BrewComparison` は永続化せず、ログとEvaluationから計算する設計も候補です。

## 15. 将来の中心画面

```text
Home
├─ Start Brew
├─ Current Best
└─ Next Experiment

Brew Mode
├─ timer
├─ pour
└─ brew end

Evaluation
├─ better / same / worse
├─ score
└─ defects

Experiment Result
├─ automatic diff
├─ comparability
├─ result
└─ next action

Bean Detail
├─ current best
├─ experiment chain
├─ trends
└─ all logs
```

EquipmentSet、Bean、RecipeTemplateなどのCRUDは中心体験を支える補助機能として扱います。

---

# Technical stack

Current MVPの基本構成：

- Python
- FastAPI
- Pydantic
- SQLite
- Jinja2

Current MVPでは、バックエンド設計、API、DB、validation、テストを優先します。

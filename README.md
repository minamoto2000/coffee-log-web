# coffee-log-web

ハンドドリップ最適化アプリのWeb版MVPです。

## READMEの読み方

このREADMEでは、現在のMVPとMVP後のプロダクト構想を明確に分けて扱います。

- `Current MVP`：現在完成させる対象です。MVPの設計・API・データモデルを記載します。
- `Post-MVP Product Direction`：MVP完成後の未実装構想です。現在のMVP完成条件には含めません。

重要：READMEに記載されている設計案を、そのまま実装済みとは扱いません。実装済み判定は、このリポジトリの実コード、テスト、テンプレート、ディレクトリ構成を正本とします。

---

# Current MVP

## MVP設計メモ

この節は、現行の `logs` CRUD を前提に、Web版MVPで `equipment_sets` / `brew_logs` / `evaluations` / `recommendation` へ設計を分けるための下書きです。

ここに書くAPIとモデルは、MVP実装前の設計案です。実装が進んだら、実装済みAPI・DB・Pydanticモデルに合わせて更新します。

### AI連携を見据えた設計

このアプリは、MVP段階ではアプリ内部にLLMを組み込まない方針です。

代わりに、抽出ログ、評価、改善提案を構造化データとして保存し、ChatGPTなどの対話型AIに渡しやすい形にすることを重視します。

生成AIに自由文で抽出記録を管理させることもできますが、条件比較、再現性確認、改善提案の検証には、粉量、湯量、湯温、挽き目、注湯配分、評価、自信度などを一定の形式で保存する必要があります。

そのため、MVPではまずFastAPI、Pydantic、SQLiteを使って、AIに依存しない正本データを作ります。

将来的には、ログ詳細からAI相談用のMarkdown/JSONを出力したり、読み取り専用APIやMCP serverを通じて、外部の対話型AIが抽出履歴を参照できる構成を検討します。

ただし、保存データの正規化、入力バリデーション、recommendの基本ロジックはアプリ側で制御します。

### API一覧案

#### equipment_sets

| Method | Path | 内容 |
| --- | --- | --- |
| GET | /equipment-sets | 用具セット一覧を取得 |
| POST | /equipment-sets | 用具セットを作成 |
| GET | /equipment-sets/{equipment_set_id} | 用具セットを1件取得 |
| PATCH | /equipment-sets/{equipment_set_id} | 用具セットを更新 |
| DELETE | /equipment-sets/{equipment_set_id} | 用具セットを非表示化 |

`DELETE /equipment-sets/{equipment_set_id}` は物理削除ではなく、`is_active = false` にする想定です。

#### brew_logs

APIパスは利用者にとって短く自然な `/logs` を維持します。一方で、DBテーブル名と内部モデル名は `brew_logs` / `BrewLog` とし、保存対象が自宅抽出ログであることを明確にします。

| Method | Path | 内容 |
| --- | --- | --- |
| GET | /logs | 抽出ログ一覧を取得 |
| POST | /logs | 抽出ログを作成 |
| GET | /logs/{log_id} | 抽出ログを1件取得 |
| PATCH | /logs/{log_id} | 抽出ログを更新 |
| DELETE | /logs/{log_id} | 抽出ログを削除 |

#### evaluations

| Method | Path | 内容 |
| --- | --- | --- |
| POST | /logs/{log_id}/evaluation | 指定ログの評価を作成 |
| GET | /logs/{log_id}/evaluation | 指定ログの評価を取得 |
| PATCH | /logs/{log_id}/evaluation | 指定ログの評価を更新 |

#### recommendation

| Method | Path | 内容 |
| --- | --- | --- |
| GET | /logs/latest/recommendation | 直近ログの改善提案を取得 |
| GET | /logs/{log_id}/recommendation | 指定ログの改善提案を取得 |
| POST | /logs/{log_id}/recommendation | 指定ログの改善提案を生成 |

### DBテーブル案

#### equipment_sets

| Column | Type | Note |
| --- | --- | --- |
| id | INTEGER | Primary key |
| name | TEXT | 用具セット名 |
| brewer_label | TEXT | ドリッパー名 |
| filter_label | TEXT | フィルター名 |
| grinder_label | TEXT | ミル名 |
| grind_setting_unit | TEXT | click / step / number / other |
| note | TEXT | 補足メモ |
| is_active | BOOLEAN | 選択肢に表示するか |
| created_at | TEXT | 作成日時 |
| updated_at | TEXT | 更新日時 |

#### brew_logs

| Column | Type | Note |
| --- | --- | --- |
| id | INTEGER | Primary key |
| brewed_at | TEXT | 抽出日時 |
| equipment_set_id | INTEGER | equipment_sets.id への参照 |
| equipment_set_name_snapshot | TEXT | 保存時点の用具セット名 |
| brewer_label_snapshot | TEXT | 保存時点のドリッパー名 |
| filter_label_snapshot | TEXT | 保存時点のフィルター名 |
| grinder_label_snapshot | TEXT | 保存時点のミル名 |
| grind_setting_unit_snapshot | TEXT | 保存時点の挽き目単位 |
| bean_label | TEXT | 豆名・商品名・識別名 |
| dose_g | REAL | 粉量g |
| water_g | REAL | 湯量g |
| water_temp_c | REAL | 湯温℃ |
| grind_setting_value | REAL | 挽き目の値 |
| bloom_time_s | INTEGER | 蒸らし時間秒 |
| agitation_level | INTEGER | 攪拌レベル 0〜3 |
| pours | TEXT | JSON文字列として保存 |
| finish_pouring_s | INTEGER | 最後の注湯完了秒 |
| brew_end_s | INTEGER | 抽出終了秒 |
| note | TEXT | 補足メモ |
| created_at | TEXT | 作成日時 |
| updated_at | TEXT | 更新日時 |

`equipment_set_id` だけでなく、保存時点の用具情報を snapshot カラムにコピーします。用具セットを後から編集しても、過去ログの表示内容を変えないためです。

#### evaluations

| Column | Type | Note |
| --- | --- | --- |
| id | INTEGER | Primary key |
| brew_log_id | INTEGER | brew_logs.id への参照 |
| confidence | INTEGER | 評価の自信度 1〜3 |
| overall_score | INTEGER | 総合点 1〜10。confidence により任意または必須 |
| taste_defect | TEXT | none / thin / sour / bitter / not_sweet |
| aroma_defect | BOOLEAN | 香りに欠点があるか |
| aftertaste_defect | BOOLEAN | 後味に欠点があるか |
| texture_defect | BOOLEAN | 質感に欠点があるか |
| memo | TEXT | 評価メモ |
| created_at | TEXT | 作成日時 |
| updated_at | TEXT | 更新日時 |

#### recommendations

MVPでは `recommendations` テーブルは作りません。

recommend結果は `brew_log` と `evaluation` からルールベースで都度計算し、APIレスポンスとして返します。提案履歴の保存はMVP後の拡張候補とします。

### Pydanticモデル案

#### equipment_sets

```text
EquipmentSetCreate
- name
- brewer_label
- filter_label
- grinder_label
- grind_setting_unit
- note

EquipmentSetUpdate
- name
- brewer_label
- filter_label
- grinder_label
- grind_setting_unit
- note
- is_active

EquipmentSetRead
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

#### brew_logs

```text
PourItem
- grams
- at_s

BrewLogCreate
- brewed_at
- equipment_set_id
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

BrewLogUpdate
- brewed_at
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

BrewLogRead
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

#### evaluations

```text
EvaluationCreate
- confidence
- overall_score
- taste_defect
- aroma_defect
- aftertaste_defect
- texture_defect
- memo

EvaluationUpdate
- confidence
- overall_score
- taste_defect
- aroma_defect
- aftertaste_defect
- texture_defect
- memo

EvaluationRead
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

`confidence = 1` の場合、`overall_score` は任意にします。

`confidence = 2` または `confidence = 3` の場合、`overall_score` は必須にします。

#### recommendation

```text
RecommendationRead
- target_log_id
- recommendation_mode
- action_type
- direction
- amount
- unit
- message
- reason
```

recommendationは保存用モデルではなく、レスポンス用モデルとして扱います。

---

# Post-MVP Product Direction — Not Implemented

> [!IMPORTANT]
> このセクションはMVP完成後のプロダクト構想です。以下の `Experiment`、Brew Mode、Automatic diff、Experiment chain、複数ログ分析、AI補助などは、現時点のMVP完成条件にも実装済み機能にも含めません。
>
> このセクションの存在を理由に、Current MVPのDB・API・画面へ将来機能を先行実装しません。

MVP完成後は、単なる「コーヒー記録アプリ」ではなく、以下を中心とする反復実験支援アプリへ発展させます。

> 前回のハンドドリップを基準に1条件だけ変えて抽出し、その変更と味の変化を自動で比較・蓄積することで、自分の好みに合った再現可能な抽出条件を見つける。

この方向性では、記録そのものではなく、次の3点を専用アプリの価値とします。

1. 入力摩擦を減らす
2. 抽出条件と評価を一貫した構造で保存する
3. 反復実験の差分と結果を自動比較する

### 1. Core workflow

理想的な利用フローは次です。

```text
前回またはベストの抽出条件を複製
↓
次回変える条件を1つ選ぶ
↓
抽出を実行
↓
抽出中の時刻や注湯イベントを可能な範囲で自動記録
↓
味を評価
↓
前回との差分と結果を自動比較
↓
再現確認または次の1変更を提案
```

ユーザーに毎回すべての条件を再入力させず、「前回から何を変えるか」だけを意識できる体験を優先します。

### 2. Experimentを第一級データとして扱う

将来的には、単独の `BrewLog` だけでなく「何を検証した抽出か」を表す `Experiment` を導入します。

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

例：

```text
baseline: BrewLog #38
target_variable: grind_setting
before: 22 click
after: 20 click
hypothesis: 挽き目を細かくすると薄さが改善する
candidate: BrewLog #39
result: better
score_delta: +2
```

重要なのは、単に前回との差分を表示するだけではなく、「予定していた変更以外の条件も変わっていないか」を判定することです。

複数条件が同時に変わっている場合は、改善や悪化を特定の操作だけの効果として解釈しないよう警告します。

### 3. 操作変数と観測結果を分離する

抽出条件を次の2種類に分けて扱います。

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

これにより、次のような実験履歴を構造化して残します。

```text
操作
Grind: 22 → 20 click

観測
Drawdown: 35s → 52s

結果
Score: 6 → 8
```

### 4. 入力摩擦を減らす

ログ作成は空のフォーム入力ではなく、原則として既存条件の複製から始めます。

主な入口：

- 最新の抽出から淹れる
- ベスト候補から淹れる
- レシピテンプレートから淹れる

用具、豆、粉量、湯量、湯温、レシピ、注湯配分などを自動入力し、ユーザーは必要な変更点だけ編集します。

### 5. Brew Mode

通常のCRUDフォームとは別に、抽出中に使用する専用画面を検討します。

Brew Modeではタイマーを開始し、注湯開始や抽出終了の操作から時刻を記録します。

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

これにより、例えば以下の `pours` を後から手入力するのではなく、抽出操作から生成できるようにします。

```json
[
  {"grams": 60, "at_s": 0},
  {"grams": 60, "at_s": 46},
  {"grams": 60, "at_s": 91},
  {"grams": 60, "at_s": 136}
]
```

将来的なBluetooth対応スケール等との連携余地は残しますが、初期実装では必須としません。

### 6. Relative evaluation

絶対評価だけでなく、基準となる抽出に対する相対評価を持たせます。

```text
relative_result
- better
- same
- worse
- uncertain
```

`overall_score` は引き続き保持しますが、反復実験では「前回より良かったか」を明示的に保存することで、評価尺度の日ごとの揺れを補います。

### 7. Automatic diff

ログ詳細では、全項目を並べるだけではなく、基準ログとの差分を最優先で表示します。

```text
変更
Grind        22 → 20 click

ほぼ同一
Dose         15g
Water        240g
Temp         92℃
Equipment    V60 + C40

結果
Score        6 → 8       +2
Drawdown     38s → 51s   +13s
Thin         yes → no
```

予定していない条件まで変化している場合は、confounderとして表示し、比較可能性を下げます。

### 8. Experiment chain

抽出ログは単独の履歴だけでなく、同じ豆や目的に対する探索の流れとして表示します。

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

これにより、「何を試し、何が良くなり、何を戻したか」を追跡できるようにします。

### 9. 再現可能な成功パターン

単発の最高点をそのままベストとは扱いません。

成功パターン候補は、例えば次の条件で判定します。

- overall_score >= 8
- confidence >= 2
- 同一または十分近い抽出条件
- 複数回で良好な結果を再現
- 重大な欠点が継続していない

状態は次のように段階化できます。

```text
candidate
↓
promising
↓
reproduced
```

アプリのゴールは、最高点を1回出すことではなく、「再現可能な勝ちパターン」を見つけることです。

### 10. 分析の方針

単にグラフを描くことはSpreadsheetでも可能です。

そのため専用アプリでは、「比較してよいログを自動的に選ぶ」ことを重視します。

例えば湯温と評価を比較する場合でも、可能な限り次の条件を揃えます。

- 同じ豆
- 同じ用具セット
- 同じ粉量
- 同じ湯量
- 同じレシピ系統

その上で、湯温だけが異なる比較可能なログを抽出します。

```text
Comparable experiments: 6

90℃  avg 6.5
92℃  avg 8.2
94℃  avg 7.1
```

価値の中心はグラフ描画ではなく、比較条件の自動整理に置きます。

### 11. Recommendationの優先順位

将来のrecommendationは、一般的な抽出ルールだけでなく、ユーザー自身の実験履歴を優先します。

優先順位の例：

```text
1. 再現確認
2. 過去の比較可能な実験結果
3. 現在の欠点
4. 一般的なルールベース
5. AIによる補足説明
```

1回改善しただけなら次の条件変更へ進まず、まず同じ条件で再現確認を提案します。

### 12. AIの役割

生成AIそのものと競争することは目的にしません。

このアプリは、AIが扱いやすい構造化済みの実験データを作る正本として機能します。

AIに任せる候補：

- 過去ログの傾向要約
- 仮説候補の整理
- 実験結果の自然言語説明
- recommendation理由の補足

アプリ側で管理するもの：

- データの正規化
- 入力バリデーション
- 数値計算
- 比較対象の抽出
- confounder判定
- action_type / direction / amount / unit の構造

CSV / JSON / Markdown exportやAPIを通じて、Spreadsheet、ChatGPT、Claude、Python、Jupyterなど外部ツールへ持ち出せる構成を目指します。

### 13. 将来データモデル案

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

`BrewComparison` は必ずしも永続化せず、ログと評価から計算する設計も検討します。

### 14. 将来の中心画面

将来的には、管理画面を並列に増やすより、次の体験を中心にします。

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

EquipmentSet、Bean、RecipeTemplateなどのCRUDは、これらの中心体験を支える補助機能として扱います。

### 15. MVPとの関係

この節はMVP完成条件を変更するものではありません。

現行MVPでは、まず以下のVertical Sliceを完成させます。

```text
用具セット登録
→ 抽出ログ登録
→ 評価登録
→ 改善提案を1つ表示
```

MVP完成後の優先順位は次を想定します。

1. 前回を複製 → 1変数変更 → automatic diff
2. Experiment chain → 再現確認
3. Brew Mode
4. 比較可能なログを使った分析
5. AI補助

長期仕様を理由にMVP範囲を広げず、Vertical Sliceの完成を優先します。
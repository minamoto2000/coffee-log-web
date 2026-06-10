# coffee-log-web

ハンドドリップ最適化アプリのWeb版MVPです。

## MVP設計メモ

この節は、現行の `logs` CRUD を前提に、Web版MVPで `equipment_sets` / `brew_logs` / `evaluations` / `recommendation` へ設計を分けるための下書きです。

ここに書くAPIとモデルは、MVP実装前の設計案です。実装が進んだら、実装済みAPI・DB・Pydanticモデルに合わせて更新します。

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

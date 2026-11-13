# coffee-log-web 作業指示（AIエージェント向け）

## このリポジトリの役割

このリポジトリは、Web版ポートフォリオ `coffee-log-web` の実装状況に関する正本である。

実装済みかどうかは、実際の以下の内容から判断すること。

- ソースコード
- tests
- README
- templates
- ディレクトリ構成
- 必要に応じて実際のGit履歴・CI結果

管理ファイルに書かれているという理由だけで、機能が実装済みだと判断してはいけない。

`coffee-log-api` の完成を、Web版MVPの完成として扱ってはいけない。

## 現在の目的

`coffee-log-web` を、第三者が起動・確認でき、READMEと実装とテストが一致した提出品質に保つ。

2026-11-04に開発目的を「実験・測定・検証アプリ」へ変更し、2026-11-05に移行（PR1〜PR9）を終えた。

- 移行前の版はタグ `legacy-v1-recommendation` で参照する。旧Recommendation・ExternalBenchmark・BrewLogを復活させない
- MVP仕様に含まれない機能を先行実装しない
- 変更はPR単位で行い、各PRはテスト（E2Eを含む）が通る状態で閉じる

機能追加よりも以下を優先する。

- correctness
- reproducibility
- READMEと実装の一致
- tests
- Core Vertical Slice

## 関連する管理リポジトリ

MVP仕様・全体ルール・進め方は、非公開の管理リポジトリ `minamoto2000/career-management-private` にある。

- MVP仕様：`01b_Portfolio_MVP_Spec.md`
- ポートフォリオ全体のルール：`01_Portfolio_Master.md`
- 実装判断の背景：`01c_Portfolio_Status.md`（実装状況の正本ではない）
- 完成形仕様：`01a_Portfolio_Final_Spec.md`（将来方針との整合確認にだけ使う。MVP範囲を広げる根拠にしない）
- 学習・演習の進め方と記録：同リポジトリの規則に従う。このリポジトリには置かない

管理リポジトリまたは必要なファイルへアクセスできない場合は、確認不能であることを明記すること。未確認の内容を推測してはいけない。

## 正本の優先順位

| 対象 | 正本 |
|---|---|
| 実装状況 | このリポジトリ |
| MVP仕様 | `career-management-private/01b_Portfolio_MVP_Spec.md` |
| ポートフォリオ全体のルール | `career-management-private/01_Portfolio_Master.md` |

## 実装判断ルール

MVP範囲に関係する実装判断を行う場合は、`01b_Portfolio_MVP_Spec.md` を確認する。

設計がきれいになるという理由だけでPost-MVP機能を追加してはいけない。

現在の仕様に明示されていない限り、以下のような領域へ不用意に範囲を広げない。

- 認証
- React / Next.js
- Docker
- PostgreSQL
- その他の不要な新機能

Core Vertical Sliceが動く状態を優先して維持する。

## コードレビューの優先順位

1. 仕様との差分
2. 動作上の誤り
3. データ整合性
4. validation責務
5. transaction
6. error pathとHTTP status
7. test coverage
8. 不要な複雑性

## DB・transactionのルール

別テーブルにある別レコードを「1つのレコード」として扱わない。

以下を明確に区別する。

- primary key
- foreign key
- transaction境界
- commit
- rollback
- failure時のDB状態

DB動作を変更した場合は、正常系だけでなく失敗時の挙動も確認する。

## テストルール

実装変更が発生した場合は、

- 関連するfocused testを実行する
- 必要に応じて全体test suiteも実行する
- 実際に得られた結果だけを報告する

実行していないtestをpassedと報告してはいけない。

test件数を推測してはいけない。

test自体が誤っていると確認できない限り、testを通すためだけにtestを削除・弱体化してはいけない。

## Gitルール

commit SHAを推測してはいけない。

実際に存在するcommit SHAのみ報告する。

実際にcommitまたはpushしていない変更を、commit済み・push済みと報告してはいけない。

実装変更のcommitは `coffee-log-web` に保存する。管理情報は `career-management-private` に保存する。

## リポジトリ衛生

公開リポジトリには、アプリを理解・実行・レビュー・継続開発するために必要な情報だけを置く。

個人的な学習記録・習熟度の判定・自己評価上の弱点は、この公開リポジトリへ保存しない。

READMEは目標backlogではなく、実際に完成・検証された挙動を説明する。

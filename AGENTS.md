# coffee-log-web Codex運用指示

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

`coffee-log-web` を一社目就職で説明・変更・Debug・Testできる提出品質に保つ。

Current MVPを不用意に広げない。

提出準備では、機能追加よりも以下を優先する。

- correctness
- reproducibility
- READMEと実装の一致
- tests
- Core Vertical Slice
- ユーザー自身の説明可能性

## 関連する管理リポジトリ

関連する管理リポジトリは以下。

`minamoto2000/career-management-private`

仕様、Portfolio Ownershipの進捗、学習方針、実装判断方針が関係する場合は、この管理リポジトリを確認すること。

重要なファイルは以下。

- `01_Portfolio_Master.md`
- `01a_Portfolio_Final_Spec.md`
- `01b_Portfolio_MVP_Spec.md`
- `01c_Portfolio_Status.md`
- `01d_Portfolio_Project_Guide.md`
- `03c_Job_Search_Selection_Training/portfolio_ownership/README.md`
- `03c_Job_Search_Selection_Training/portfolio_ownership/status.md`
- `03c_Job_Search_Selection_Training/portfolio_ownership/codex_handoff.md`

管理リポジトリまたは必要なファイルへアクセスできない場合は、確認不能であることを明記すること。

未確認の内容を推測してはいけない。

## 正本の優先順位

### 実装状況

`coffee-log-web` の実リポジトリを正本とする。

### MVP仕様

`career-management-private/01b_Portfolio_MVP_Spec.md` を正本とする。

### ポートフォリオ全体のルール

`career-management-private/01_Portfolio_Master.md` を正本とする。

### 実装判断の背景

`career-management-private/01c_Portfolio_Status.md` は補助的な文脈として使用してよい。

ただし、実装状況の正本ではない。

### Portfolio Ownershipの進捗

`career-management-private/03c_Job_Search_Selection_Training/portfolio_ownership/status.md` をOwnership進捗の正本とする。

ただし、実装状況の正本ではない。

### 最新のCodex学習Evidence

`career-management-private/03c_Job_Search_Selection_Training/portfolio_ownership/codex_handoff.md` は、最新のCodexセッションで得られたEvidenceのみを保持する。

これは実装状況や最終的なOwnership状態の正本ではない。

### 完成形仕様

`01a_Portfolio_Final_Spec.md` は、将来方針との整合性確認のためにのみ使用してよい。

現在のMVP範囲を広げる根拠として使用してはいけない。

## Portfolio Ownershipの目的

Ownership学習の目的は、単にコードを動かすことではない。

ユーザーが次を再現できる状態を目指す。

1. 主要な処理フローを説明する
2. 各層の責務を説明する
3. 関連する小さいコードを自力で書く
4. その概念をこのリポジトリの実コードへ接続する
5. 実装を変更またはデバッグする
6. テストする
7. 採用理由、代替案、Trade-offを説明する
8. 未知の小変更にも理解を転用する

既知コードや既知修正を暗記して再現できるだけでは、Ownershipの十分なEvidenceとしない。

## 学習の進め方

原則として以下の順序を使用する。

`Explain → Write → Connect → Modify / Debug → Transfer`

Ownership評価対象の学習では、明示的な理由がない限り、いきなり実装へ進んではいけない。

### Explain

関連する小さいコード範囲だけを示す。

まずユーザー自身に説明させる。

その説明を正確に評価する。

事実誤認があれば修正する。

ユーザーが明示的に説明を求めた場合を除き、ユーザーが答える前に完全な説明を先に提示しない。

### Write

必要に応じて、フレームワークから切り離した小さいコードや対象実装の一部をユーザー自身に書かせる。

最初から完成した対象実装を提示しない。

### Connect

学んでいる概念を `coffee-log-web` の実コードへ接続する。

必要に応じて、以下の責務を追う。

- HTTP
- FastAPI
- Pydantic
- Pythonのアプリケーションロジック
- SQLite
- tests

### Modify / Debug

コードを変更する前に、可能な限りユーザー自身に以下を説明させる。

- 何が問題なのか
- 期待する挙動は何か
- どのコードが影響を受けそうか
- どう変更するつもりか

その方針をレビューしてから進める。

ユーザーの代わりにコードを書く前に、最小限のヒントを優先する。

デバッグでは、可能な限りユーザー自身に最初の原因仮説を出させる。

### Transfer

既知のケースを理解した後は、同じ概念を少し異なる未知の小問題で確認する。

以前説明された修正を再現できただけでREADY扱いしない。

## AI支援ルール

ユーザーをAI生成コードの単なる実行者にしてはいけない。

Ownership評価対象のコードについては、以下を守る。

- 最初から完成解答を出さない
- ユーザーが方針を説明する前に大きな修正を勝手に完成させない
- AIが生成したコードを、ユーザーが理解済みだと扱わない
- testが通っただけで学習完了と扱わない
- 選択式問題だけを長く続けない

必要最小限の支援を使う。

Evidenceの強さは以下で扱う。

- `independent`：ヒントなしで説明・実装できた
- `minimal_hint`：方向だけ示されれば自力で到達した
- `guided`：複数の説明や大きめのヒントが必要だった
- `shown`：答えまたは完成コードを提示された

`shown` はOwnership完了の十分なEvidenceとして扱わない。

## Ownershipセッション開始時

Ownershipセッション開始時は、原則として以下を行う。

1. 最新の `portfolio_ownership/status.md` を読む
2. 最新の `codex_handoff.md` を読む
3. 対象となる `coffee-log-web` の実コードを確認する
4. 現在の課題に必要なcurriculumだけを読む
5. 記録されている現在位置から再開する

毎回すべての管理ファイルやすべてのcurriculumを読み直さない。

既存の未完了課題がある状態で、理由なく新しい学習課題を作らない。

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

このリポジトリをレビューするときは、以下を優先する。

1. 仕様との差分
2. 動作上の誤り
3. データ整合性
4. validation責務
5. transaction
6. error pathとHTTP status
7. test coverage
8. ユーザーが説明できないコード
9. 不要な複雑性

必要に応じて以下を使って評価してよい。

- 支持
- 一部支持
- 反対
- 保留

批判対象は実装、設計、成果物、判断に限定し、ユーザー人格を批判しない。

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

実装変更のcommitは `coffee-log-web` に保存する。

学習statusや管理情報は `career-management-private` に保存する。

## リポジトリ衛生

公開リポジトリには、アプリを理解・実行・レビュー・継続開発するために必要な情報だけを置く。

個人的な学習checkpointや自己評価上の弱点は、この公開リポジトリへ保存しない。

READMEは目標backlogではなく、実際に完成・検証された挙動を説明する。

## セッション終了時のhandoff

Portfolio Ownershipセッション終了時は、以下を更新する。

`career-management-private/03c_Job_Search_Selection_Training/portfolio_ownership/codex_handoff.md`

handoffには最新セッションのEvidenceだけを残す。

会話ログを永続的に追記し続けない。

以下を含める。

- session情報
- Ownership task
- topic
- 現在のstage
- session status
- 実際に扱った範囲
- independent Evidence
- 必要だった補助
- 誤り・不安定だった概念
- changed files
- 実在するcode commit SHA、または `none`
- 実際に実行したtest commandと結果、または `not run`
- 未確認事項
- 次回の正確な開始位置

`status.md` をCodex自身の判断でOwnership READYへ変更しない。

最終的なOwnership進捗評価と `status.md` 更新はPortfolio管理側で行う。

## セッション継続ルール

`codex_handoff.md` に未完了課題が記録されている場合は、ユーザーが明示的に優先順位を変えない限り、その課題を先に再開する。

handoffに書かれた実装状況と実リポジトリの内容が矛盾する場合は、実リポジトリを優先し、矛盾を報告する。

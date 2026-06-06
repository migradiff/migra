# MigraDiff

<div align="center">

**言語を選択:**  
[English](README.md) | 
[हिन्दी](README.hi.md) | 
[中文](README.zh.md) | 
[日本語](README.ja.md) | 
[Français](README.fr.md) | 
[Deutsch](README.de.md) | 
[עברית](README.he.md)

</div>

---

# migra — PostgreSQL スキーマ差分ツール

[![PyPI version](https://img.shields.io/pypi/v/migradiff)](https://pypi.org/project/migradiff/)
[![Python versions](https://img.shields.io/pypi/pyversions/migradiff)](https://pypi.org/project/migradiff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**これは [djrobstep/migra](https://github.com/djrobstep/migra) のアクティブにメンテナンスされているフォークです。**

migra は 2 つの PostgreSQL データベーススキーマを比較し、一方を他方に変換するために必要な SQL マイグレーションスクリプトを生成します。CI パイプラインに組み込んで、手動で `ALTER TABLE` を書く必要をなくしましょう。

---

## このフォークの理由

オリジナルの `migra` は 2024 年に正式に非推奨となりました。このフォークはその続きを引き継ぎ — 既知の問題の修正、Python 3.12+ のサポート追加、高度な PostgreSQL 機能のカバレッジ拡張を行っています。

`djrobstep/migra` を使用していた場合、これはドロップインでの継続利用が可能です。ツールの動作方法は何も変わっていません。ただ維持を続け、改善を加えているだけです。

**命名についての注意:** これは独立したコミュニティフォークです。CLI コマンドは既存のスクリプトやパイプラインとの下位互換性のために `migra` のままです。パッケージ名は `migradiff` で、非推奨のアップストリームと区別しています。オリジナルの djrobstep/migra をお探しの場合は、https://github.com/djrobstep/migra にアーカイブされています。

---

## クイックスタート

### インストール

```bash
pip install migradiff
```

Python 3.10+ と動作中の PostgreSQL インスタンス（12+）が必要です。

ソースからインストールする場合：

```bash
git clone https://github.com/migradiff/migra
cd migra
pip install -e .
```

### 基本的な使い方

migra を 2 つのデータベース接続に向けると、一方から他方へのマイグレーションに必要な DDL が出力されます：

```bash
migra \
  postgresql://user:pass@localhost/db_production \
  postgresql://user:pass@localhost/db_branch \
  --unsafe
```

出力はプレーンな SQL です — パイプで渡し、レビューし、適用できます：

```bash
migra postgres://db_a postgres://db_b > migration.sql
psql postgres://db_production < migration.sql
```

### スキーマダンプ（ライブ接続不要）

migra をライブデータベースに向けられない、または向けたくない場合は、`pg_dump -s` を使用してスキーマダンプを生成し、それを比較できます：

```bash
pg_dump -s postgres://db_production > schema_a.sql
pg_dump -s postgres://db_branch     > schema_b.sql
migra --from-file schema_a.sql schema_b.sql
```

これは CI パイプラインやセキュリティ重視の環境に推奨される方法です — 本番環境の認証情報は不要です。

### マイグレーションディレクトリ（ライブブランチデータベース不要）

対象の状態がマイグレーションファイルのフォルダで定義されている場合：

```bash
migra --from-migrations-dir ./migrations postgres://db_production
```

MigraDiff はマイグレーションを一時的なデータベースに適用し、結果を比較します。Supabase、Flyway、および標準的な数値命名規則に対応しています。

### スキーマを指定

```bash
# 単一スキーマ
migra --schema myschema postgres://db_a postgres://db_b

# 複数スキーマ（カンマ区切り）
migra --schema public,reporting postgres://db_a postgres://db_b
```

### JSON 出力

プログラムでの利用や CI パイプライン向け：

```bash
migra --output json postgres://db_a postgres://db_b
```

出力にはステートメントごとのリスク分類（`safe`、`warning`、`destructive`）と、全体的なリスクレベルのサマリーが含まれます。

---

## AI を活用した説明（オプション）

MigraDiff はあらゆるマイグレーションを平易な言葉で説明できます — 各変更の内容、リスク、破壊的操作のより安全な代替案を提示します。

    migra --explain postgres://db_a postgres://db_b

出力：

    --- Migration SQL ---
    ALTER TABLE public.users ADD COLUMN email text;
    DROP TABLE public.legacy_sessions;

    --- AI Explanation ---
    This migration makes 2 changes to your database:

    1. SAFE: Adds an email column (text) to the users table.
       No existing data is affected.

    2. ⚠ DESTRUCTIVE: Drops the legacy_sessions table entirely.
       All data in this table will be permanently lost.
       Consider archiving before dropping.

    Overall risk: HIGH

Claude（Anthropic）を利用しています。API キーはご自身でご用意ください — MigraDiff サーバーにデータが送信されることはありません。

### セットアップ

AI エクストラをインストール：

    pip install migradiff[ai]

API キーを一度設定：

    migra --setup-ai

または環境変数を設定：

    export ANTHROPIC_API_KEY=sk-ant-...

https://console.anthropic.com で API キーを取得してください。

### AI ロールバック生成（--rollback）

正確な逆マイグレーションを生成 — 任意のマイグレーションを取り消すために必要な SQL：

    migra --rollback migration.sql
    migra --rollback postgres://db_a postgres://db_b

MigraDiff はソーススキーマのコンテキストを使用して、DROP TABLE および DROP COLUMN の取り消しを正確に再構築します。元に戻せない操作（TRUNCATE、一括 DELETE）は明示的にフラグ付けされます。

--explain と組み合わせて全体像を把握：

    migra --explain --rollback postgres://db_a postgres://db_b

`pip install migradiff[ai]` と Anthropic API キーが必要です。

### AI パフォーマンスアドバイザー（--advise）

マイグレーションを適用する前に、パフォーマンスリスク評価を取得 — ロック動作、テーブル書き換えリスク、ダウンタイムゼロの代替案：

    migra --advise postgres://db_a postgres://db_b
    migra --advise migration.sql

MigraDiff は各ステートメントを PostgreSQL 固有のリスクについて分析します：テーブルロック、完全書き換え、不可逆的なデータ損失。ライブ接続が提供されると、実際のデータ規模でのロック時間を見積もるためにテーブルの行数が使用されます。

3 つの AI 機能すべてを組み合わせて全体像を把握：

    migra --explain --advise --rollback postgres://db_a postgres://db_b

pip install migradiff[ai] と Anthropic API キーが必要です。

### AI マイグレーションジェネレーター（--generate）

やりたいことを平易な言葉で説明するだけで — MigraDiff が実際のスキーマに基づいたマイグレーション SQL を生成：

    migra --generate "add email verification to users table" \
      postgres://db_production

一般的な AI ツールとは異なり、MigraDiff は実際のテーブル名、カラム型、制約を認識しています — 幻のカラム名や誤った型は生成されません。

生成してすぐにリスクを確認：

    migra --generate "add index on orders.user_id" \
      --advise postgres://db_production

pip install migradiff[ai] と Anthropic API キーが必要です。

---

## 開発環境のセットアップ

テストスイートには動作中の PostgreSQL インスタンスが必要です。最も簡単な方法は Docker Compose を使用することです：

```bash
docker compose up -d
```

これにより、trust 認証を使用する Postgres 16 コンテナが localhost:5432 で起動します。パスワードは不要です。

停止するには：

```bash
docker compose down
```

データは `migradiff-pgdata` ボリュームにより再起動後も保持されます。完全にリセットするには：

```bash
docker compose down -v
```

---

## Docker

Python 環境がありませんか？公式イメージを使用してください：

```bash
docker run --rm ghcr.io/migradiff/migra \
  postgres://db_a postgres://db_b
```

---

## GitHub Actions

プルリクエストワークフローにスキーマ差分を追加：

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
```

破壊的操作が検出された場合に自動的にビルドを失敗させる：

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
    fail_on_destructive: "true"
```

ライブ接続の代わりにスキーマダンプファイルを使用：

```yaml
- uses: migradiff/migra@v1
  with:
    base_file: schema_production.sql
    head_file: schema_branch.sql
```

完全な設定オプションは [docs/action-usage.md](docs/action-usage.md) を参照してください。

---

## Pre-commit フック

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/migradiff/migra
    rev: v1.1.0
    hooks:
      - id: migra
```

完全な設定オプションはリポジトリルートの `pre-commit-config.example.yaml` を参照してください。

---

## migra が対応しているもの

- テーブル、カラム、制約、インデックス
- ビューおよびマテリアライズドビュー
- 関数およびストアドプロシージャ
- シーケンス
- 列挙型、複合型、ドメイン
- 行レベルセキュリティ（RLS）ポリシー
- 外部データラッパー
- カラムレベルの権限
- パーティションテーブル
- オブジェクトコメント（`COMMENT ON`）

---

## アップストリームからの改善点

| 分野 | アップストリーム（非推奨） | このフォーク |
|---|---|---|
| Python 3.12+ | 非推奨警告 | クリーン — 警告なし |
| RLS ポリシー | 部分的、等価性バグあり | 完全な CREATE/DROP、パーティション対応 |
| エラーメッセージ | 未サポート型で意味不明 | オブジェクト名と問題リンク付きで実用的 |
| --schema フラグ | マルチスキーマDBでエッジケース | カンマ区切り、クロススキーマ依存性解決済み |
| pg_dump 入力 | 未サポート | 第一級の `--from-file` モード |
| JSON 出力 | 未サポート | `--output json` リスク分類付き |
| Docker イメージ | なし | `ghcr.io/migradiff/migra` |
| GitHub Action | なし | `migradiff/migra-action` |
| Pre-commit フック | なし | `.pre-commit-hooks.yaml` |
| 開発環境 | 手動 Docker コマンド | `docker compose up -d` |
| AI 説明 | なし | Claude を使用した `--explain` フラグ — 平易な言葉での差分説明、リスク分析、安全な代替案 |
| COMMENT ON 差分 | 未サポート | 全オブジェクトタイプでの完全差分 — 追加/変更/削除 |

完全な修正履歴は [CHANGELOG.md](CHANGELOG.md) を参照してください。

---

## 既知の制限事項

migra は SQL 差分を生成します — 適用はしません。本番環境で実行する前に、生成されたスクリプトを毎回レビューしてください。破壊的操作（`DROP TABLE`、`DROP COLUMN`）は JSON 出力モードではフラグ付けされますが、プレーン SQL モードではブロックされません。

migra はスキーマを調査するためにライブの PostgreSQL 接続、または `--from-file` によるスキーマダンプファイルを必要とします。生の DDL テキストは解析しません。

---

## コントリビューションに関するお知らせ

このプロジェクトにご関心をお寄せいただきありがとうございます。現在、外部からのコード貢献、プルリクエスト、バグ修正、機能提案は受け付けておりません。

開かれたプルリクエストはレビューなしで自動的にクローズされます。

---

## ライセンス

MigraDiff は MIT ライセンスの下で**無料かつオープンソース**です。

**すべての機能はすべての人が利用できます。** ペイウォールもコード制限もゲートキーピングもありません。

### 簡単な経緯

私は Philips で 8 年以上エンジニアとして働き、患者の安全を守る病院 IT システムを支えてきました。私たちの部門を買収した VC に解雇されたとき、私は 50 歳以上で、年齢が重要視される市場にいました。別の仕事を見つけることはほぼ不可能になりました。それでも家族を支え、食卓に食べ物を並べる必要があります。

それが MigraDiff が存在する理由です。私はあなたを助けるツールを構築しています。これが私が雇用され続ける方法だからです。

### お願い

**学生、趣味、またはオープンソースプロジェクトの場合：** MIT ライセンス、永久無料。契約は不要です。

**MigraDiff を使用する営利企業の場合：** ビジネスライセンス契約に署名してください。これはコードを閉じるためではありません—すべての機能は無料のままで、ローカルで実行され、技術的に何も変わりません。公平さの問題です：私のツールがあなたの収入に貢献しているなら、私の家族の食卓を支えてください。

あなたは依然としてすべてを所有します。データを管理し、すべての機能にアクセスできます。私たちは開発を持続する方法について透明性を確保しているだけです。

慈善を求めているのではありません。公平さを求めています。

[ビジネスライセンスを取得](https://lateos.ai/license) | [MIT ライセンスを表示](LICENSE)

---

## 謝辞

このプロジェクトは Robert Lechte によって作成・保守された [djrobstep/migra](https://github.com/djrobstep/migra) のフォークです。コアの差分エンジンは彼の成果です。深く感謝します。

# eda.py コード解説

## ファイル概要

このスクリプトは、ノーベル賞データの探索的データ分析（EDA: Exploratory Data Analysis）と、基本的なKuzuグラフデータベースの構築を行います。`create_nobel_api_graph.py`の簡易版として、基本的なグラフ構造のみを作成します。

## 主要インポート

```python
import marimo as mo
import kuzu
import polars as pl
from pathlib import Path
from datetime import datetime
```

## 処理フロー

### 1. データ読み込みと前処理（行18-42）

```python
# JSONファイルの読み込み
filepath = "data/nobel.json"
df = pl.read_json(filepath).explode("prizes").unnest("prizes")

# 不正な日付の修正
laureates_df = df.with_columns(
    pl.col("birthDate").str.replace("-00-00", "-01-01").str.to_date()
)
```

- `explode("prizes")`: 配列を展開して各賞を個別の行に
- `unnest("prizes")`: ネストされた構造をフラット化
- 日付データのクレンジング

### 2. インタラクティブなデータ探索機能

#### 賞金額フィルター（行52-73）
```python
range_slider = mo.ui.range_slider(
    start=100_000,
    stop=50_000_000,
    step=100_000,
    value=(1_000_000, 50_000_000),
)
```

スライダーで賞金額の範囲を動的に調整

#### 生年月日フィルター（行82-98）
```python
max_birth_date = mo.ui.date(value="1945-01-01", full_width=True)
```

カレンダーピッカーで生年月日の上限を設定

### 3. フィルタリングされたデータの表示（行107-116）

```python
laureates_df.filter(
    (pl.col("prizeAmount") > range_slider.value[0])
    & (pl.col("prizeAmount") < range_slider.value[1])
    & (pl.col("birthDate") < max_birth_date.value)
).select(
    "knownName", "category", "birthDate", "prizeAmount", "prizeAmountAdjusted"
).head(10)
```

インタラクティブコントロールの値に基づいてデータをフィルタリング

### 4. Kuzuデータベースの初期化（行130-145）

```python
db_name = "nobel.kuzu"
Path(db_name).unlink(missing_ok=True)  # 既存DBを削除
Path(db_name + ".wal").unlink(missing_ok=True)  # WALファイルも削除

# 新規データベース作成
db = kuzu.Database(db_name)
conn = kuzu.Connection(db)
```

### 5. 基本的なグラフスキーマ定義（行154-198）

このスクリプトでは、シンプルなスキーマのみを定義：

#### ノードテーブル
- **Scholar**: 学者の基本情報
- **Prize**: 賞の情報  
- **City**: 都市
- **Country**: 国
- **Continent**: 大陸
- **Institution**: 機関

#### リレーションシップテーブル
- **WON**: Scholar → Prize（受賞関係）のみ

`create_nobel_api_graph.py`と比較すると、以下のリレーションが省略されています：
- BORN_IN
- DIED_IN
- IS_CITY_IN
- IS_LOCATED_IN
- AFFILIATED_WITH
- IS_COUNTRY_IN

### 6. データ投入（行207-296）

#### Scholarノード（行207-227）
```python
res = conn.execute("""
    LOAD FROM $df
    WITH DISTINCT CAST(id AS INT64) AS id, knownName, fullName, gender, birthDate, deathDate
    MERGE (s:Scholar {id: id})
    SET s.scholar_type = 'laureate',
        s.fullName = fullName,
        s.knownName = knownName,
        s.gender = gender,
        s.birthDate = birthDate,
        s.deathDate = deathDate
    RETURN count(s) AS num_laureates
""", parameters={"df": laureates_df})
```

#### Prizeノード（行230-279）
賞データの前処理とデータベースへの投入

#### WON関係（行282-296）
学者と賞の受賞関係のみを作成

### 7. サンプルクエリ（行310-323）

```python
res4 = conn.execute("""
    MATCH (s:Scholar)-[r:WON]->(p:Prize)
    WHERE s.knownName CONTAINS $name
    RETURN s.*, p.*
""", parameters={"name": "Curie"})
```

シンプルなクエリで、"Curie"を含む学者とその受賞情報を取得

## create_nobel_api_graph.pyとの主な違い

1. **スキーマの簡略化**: 基本的なノードとWON関係のみ
2. **データ投入の削減**: 地理情報や機関との関係を省略
3. **クエリの簡略化**: 複雑なJOINを含まないシンプルなクエリ

## 用途

- データの初期探索
- Kuzuグラフデータベースの基本的な使い方の学習
- 最小限のグラフ構造でのプロトタイピング

## 実行方法

```bash
# スクリプトとして実行
uv run eda.py

# marimoノートブックとして実行
uv run marimo edit eda.py

# アプリモードで実行
uv run marimo run eda.py
```

## 出力例

```
726 laureate nodes ingested
399 prize nodes ingested
739 laureate prize awards ingested
```
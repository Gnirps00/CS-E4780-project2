# create_nobel_api_graph.py コード解説

## ファイル概要

このスクリプトは、ノーベル賞受賞者のJSONデータを読み込み、Kuzuグラフデータベースに変換して格納するETL（Extract, Transform, Load）パイプラインを実装しています。marimoノートブック形式で記述されており、インタラクティブな実行が可能です。

## 主要インポート

```python
import marimo as mo
import kuzu
import polars as pl
from pathlib import Path
from datetime import datetime
```

## 処理フロー

### 1. データ読み込み（行86-90）

```python
filepath = "./data/nobel.json"
df = pl.read_json(filepath).explode("prizes").unnest("prizes")
```

- JSONファイルからデータを読み込み
- `prizes`配列を展開して、各受賞情報を個別の行に変換

### 2. データクレンジング（行105-110）

```python
laureates_df = df.with_columns(
    pl.col("birthDate").str.replace("-00-00", "-01-01").str.to_date()
)
```

- 不正な日付フォーマット（`1943-00-00`など）を修正
- 文字列型から日付型への変換

### 3. インタラクティブフィルタリング機能

#### 賞金額フィルター（行113-135）
```python
range_slider = mo.ui.range_slider(
    start=100_000,
    stop=50_000_000,
    step=100_000,
    value=(1_000_000, 50_000_000),
)
```

#### 生年月日フィルター（行139-154）
```python
max_birth_date = mo.ui.date(value="1945-01-01", full_width=True)
```

### 4. Kuzuデータベース初期化（行187-201）

```python
db_name = "nobel.kuzu"
Path(db_name).unlink(missing_ok=True)  # 既存DBを削除
db = kuzu.Database(db_name)
conn = kuzu.Connection(db)
```

### 5. グラフスキーマ定義（行211-250）

#### ノードテーブル
- **Scholar**: 学者（ID、氏名、性別、生年月日、没年月日）
- **Prize**: 賞（賞ID、受賞年、カテゴリ、動機、賞金額）
- **City**: 都市（名前、州）
- **Country**: 国（名前）
- **Continent**: 大陸（名前）
- **Institution**: 機関（名前）

#### リレーションシップテーブル
- **WON**: Scholar → Prize（受賞関係）
- **BORN_IN**: Scholar → City（出生地）
- **DIED_IN**: Scholar → City（死亡地）
- **AFFILIATED_WITH**: Scholar → Institution（所属関係）
- **IS_LOCATED_IN**: Institution → City（機関所在地）
- **IS_CITY_IN**: City → Country（都市-国関係）
- **IS_COUNTRY_IN**: Country → Continent（国-大陸関係）

### 6. データ投入

#### Scholarノード投入（行260-278）
```python
conn.execute("""
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

#### Prizeノード投入（行281-332）
- 賞データの前処理（カテゴリ名の正規化、prize_IDの生成）
- データベースへの投入

#### 関係データ投入（行335-543）
各種リレーションシップの作成：
- Scholar-Prize関係（WON）
- Scholar-City関係（BORN_IN）
- Scholar-Institution関係（AFFILIATED_WITH）
- Institution-City関係（IS_LOCATED_IN）
- City-Country関係（IS_CITY_IN）
- Country-Continent関係（IS_COUNTRY_IN）

### 7. サンプルクエリ実行（行558-578）

```python
res_a = conn.execute("""
    MATCH (s:Scholar)-[x:WON]->(p:Prize),
          (s)-[y:AFFILIATED_WITH]->(i:Institution),
          (s)-[z:BORN_IN]->(c:City)
    WHERE s.knownName CONTAINS $name
    RETURN s.knownName AS knownName,
           p.category AS category,
           p.awardYear AS awardYear,
           p.prizeAmount AS prizeAmount,
           p.prizeAmountAdjusted AS prizeAmountAdjusted,
           c.name AS birthPlaceCity,
           i.name AS institutionName
""", parameters={"name": "Curie"})
```

"Curie"という名前を含む学者の受賞情報、所属機関、出生地を取得

## 技術的特徴

1. **Polarsの活用**: 高速なデータ処理
2. **marimoのインタラクティブ機能**: スライダーやカレンダーによる動的フィルタリング
3. **Cypherクエリ**: グラフデータベース操作
4. **MERGE操作**: 重複を避けながらのデータ投入

## 実行方法

```bash
# スクリプトとして実行
uv run create_nobel_api_graph.py

# marimoノートブックとして実行
uv run marimo edit create_nobel_api_graph.py
```
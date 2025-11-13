# demo_workflow.py コード解説

## ファイル概要

このスクリプトは、Graph RAG（Retrieval-Augmented Generation）ワークフローの完全な実装例を示しています。DSPyを使用して、自然言語の質問をCypherクエリに変換し、Kuzuデータベースから情報を取得して、自然言語で回答を生成します。

## 主要インポート

```python
import os
import marimo as mo
import kuzu
import dspy
from typing import Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv
```

## Graph RAGワークフローの5つのステップ

### 1. データベース接続（行37-42）

```python
db_name = "nobel.kuzu"
db = kuzu.Database(db_name, read_only=True)
conn = kuzu.Connection(db)
```

読み込み専用モードでデータベースに接続

### 2. グラフスキーマの取得（行57-90）

```python
def get_schema_dict(conn:kuzu.Connection) -> dict[str, list[dict]]:
    # ノードテーブルの取得
    response = conn.execute("CALL SHOW_TABLES() WHERE type = 'NODE' RETURN *;")
    nodes = [row[1] for row in response]
    
    # リレーションシップテーブルの取得
    response = conn.execute("CALL SHOW_TABLES() WHERE type = 'REL' RETURN *;")
    rel_tables = [row[1] for row in response]
    
    # スキーマの詳細情報を構築
    # ノードのプロパティ情報
    # エッジの接続情報とプロパティ情報
```

データベースのスキーマ（ノード、エッジ、プロパティ）を動的に取得

### 3. データモデル定義（行147-169）

```python
class Query(BaseModel):
    query: str = Field(description="Valid Cypher query with no newlines")

class Property(BaseModel):
    name: str
    type: str = Field(description="Data type of the property")

class Node(BaseModel):
    label: str
    properties: list[Property] | None

class Edge(BaseModel):
    label: str = Field(description="Relationship label")
    from_: Node = Field(alias="from", description="Source node label")
    to: Node = Field(alias="from", description="Target node label")
    properties: list[Property] | None

class GraphSchema(BaseModel):
    nodes: list[Node]
    edges: list[Edge]
```

Pydanticを使用した型安全なデータモデル

### 4. DSPy Signatures

#### スキーマプルーニング（行186-201）

```python
class PruneSchema(dspy.Signature):
    """
    ユーザーの質問に関連するスキーマの部分だけを返す
    - 質問に関連するノード、エッジ、プロパティのみを抽出
    - 不要な情報を除外してLLMの精度向上
    """
    question: str = dspy.InputField()
    input_schema: str = dspy.InputField()
    pruned_schema: GraphSchema = dspy.OutputField()
```

#### Text2Cypher変換（行273-302）

```python
class Text2Cypher(dspy.Signature):
    """
    自然言語の質問を有効なCypherクエリに変換
    
    構文ルール:
    - ScholarはknownNameプロパティで検索
    - 文字列比較はCONTAINS演算子を使用
    - APOCは使用不可
    
    結果返却ルール:
    - プロパティ値を返す（ノード全体ではない）
    - 整数は整数型として返す
    """
    question: str = dspy.InputField()
    input_schema: str = dspy.InputField()
    query: Query = dspy.OutputField()
```

#### 回答生成（行370-383）

```python
class AnswerQuestion(dspy.Signature):
    """
    クエリ結果を基に自然言語で回答を生成
    - コンテキストが空の場合は情報不足を明示
    """
    question: str = dspy.InputField()
    cypher_query: str = dspy.InputField()
    context: str = dspy.InputField()
    response: str = dspy.OutputField()
```

### 5. パイプライン実行

#### LLM設定（行119-133）

```python
lm = dspy.LM(
    model="openrouter/google/gemini-2.0-flash-001",
    api_base="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
dspy.configure(lm=lm)
```

#### スキーマプルーニング実行（行238-250）

```python
prune = dspy.Predict(PruneSchema)
r = prune(question=sample_question, input_schema=input_schema)
pruned_schema = r.pruned_schema.model_dump()
```

#### クエリ生成と実行（行337-354）

```python
def run_query(conn: kuzu.Connection, question: str, input_schema: str):
    # Text2Cypherでクエリ生成
    text2cypher_result = text2cypher(question=question, input_schema=input_schema)
    query = text2cypher_result.query.query
    
    try:
        # データベースでクエリ実行
        result = conn.execute(query)
        results = [item for row in result for item in row]
    except RuntimeError as e:
        print(f"Error running query: {e}")
        results = None
    return query, results
```

#### 最終回答生成（行386-398）

```python
answer_generator = dspy.ChainOfThought(AnswerQuestion)

answer = answer_generator(
    question=sample_question, 
    cypher_query=query, 
    context=str(context)
)
```

## 技術的特徴

1. **DSPyの活用**
   - `Predict`: シンプルな予測
   - `ChainOfThought`: 推論過程を含む予測

2. **エラーハンドリング**
   - Cypherクエリ実行エラーのキャッチ
   - 空の結果に対する適切な処理

3. **モジュラー設計**
   - 各ステップが独立した関数・クラスとして実装
   - 再利用可能な構造

4. **インタラクティブUI**
   - marimoテキスト入力による質問の変更
   - リアルタイムでの結果表示

## サンプル質問

```
"Which scholars won prizes in Physics and were affiliated with University of Cambridge?"
```

この質問に対して：
1. 物理学賞とケンブリッジ大学に関連するスキーマを抽出
2. 適切なCypherクエリを生成
3. データベースから結果を取得
4. 自然言語で回答を生成

## 実行方法

```bash
# marimoアプリとして実行
uv run marimo run demo_workflow.py

# ノートブックとして編集
uv run marimo edit demo_workflow.py
```
# graph_rag.py コード解説

## ファイル概要

このスクリプトは、Graph RAGシステムの完成形アプリケーションです。自然言語の質問を受け取り、Text2Cypherパイプラインを通じてKuzuデータベースに問い合わせを行い、結果を自然言語で返すWebアプリケーションを提供します。

## 主要インポート

```python
import marimo as mo
import os
from textwrap import dedent
from typing import Any
import dspy
import kuzu
from dotenv import load_dotenv
from dspy.adapters.baml_adapter import BAMLAdapter
from pydantic import BaseModel, Field
```

## アプリケーション構成

### 1. UI要素（行7-30）

```python
# タイトル表示
mo.md(rf"""
# Graph RAG using Text2Cypher

This is a demo app in marimo that allows you to query the Nobel laureate graph...
""")

# テキスト入力フィールド
text_ui = mo.ui.text(
    value="Which scholars won prizes in Physics and were affiliated with University of Cambridge?", 
    full_width=True
)
```

### 2. メイン処理ロジック（行33-45）

```python
db_name = "nobel.kuzu"
db_manager = KuzuDatabaseManager(db_name)

question = text_ui.value

with mo.status.spinner(title="Generating answer...") as _spinner:
    result = run_graph_rag([question], db_manager)[0]

query = result['query']
answer = result['answer'].response
```

処理中はスピナーを表示して、ユーザーに待機状態を伝える

### 3. 結果表示（行48-51）

```python
mo.hstack([
    mo.md(f"""### Query\n```{query}```"""), 
    mo.md(f"""### Answer\n{answer}""")
])
```

生成されたCypherクエリと回答を並列表示

### 4. DSPy Signatureクラス（行55-112）

`demo_workflow.py`と同じSignatureクラスを定義：
- `PruneSchema`: スキーマのプルーニング
- `Text2Cypher`: 自然言語→Cypherクエリ変換
- `AnswerQuestion`: 回答生成

### 5. LLM設定（行116-124）

```python
lm = dspy.LM(
    model="openrouter/google/gemini-2.0-flash-001",
    api_base="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
dspy.configure(lm=lm, adapter=BAMLAdapter())
```

BAMLAdapterを使用してDSPyとLLMを接続

### 6. KuzuDatabaseManagerクラス（行128-169）

```python
class KuzuDatabaseManager:
    """Kuzuデータベース接続とスキーマ取得を管理"""
    
    def __init__(self, db_path: str = "ldbc_1.kuzu"):
        self.db_path = db_path
        self.db = kuzu.Database(db_path, read_only=True)
        self.conn = kuzu.Connection(self.db)
    
    @property
    def get_schema_dict(self) -> dict[str, list[dict]]:
        # ノードとエッジのスキーマを動的に取得
        # プロパティ情報も含めて返却
```

データベース管理を専用クラスでカプセル化

### 7. データモデル（行173-198）

Pydanticモデルでグラフスキーマを定義：
- `Query`: Cypherクエリ
- `Property`: プロパティ情報
- `Node`: ノード情報
- `Edge`: エッジ情報
- `GraphSchema`: 全体スキーマ

### 8. GraphRAGクラス（行202-277）

```python
class GraphRAG(dspy.Module):
    """
    DSPyカスタムモジュール
    Text2Cypherを適用してクエリを生成・実行し、
    自然言語の回答を生成
    """
    
    def __init__(self):
        self.prune = dspy.Predict(PruneSchema)
        self.text2cypher = dspy.ChainOfThought(Text2Cypher)
        self.generate_answer = dspy.ChainOfThought(AnswerQuestion)
    
    def get_cypher_query(self, question: str, input_schema: str) -> Query:
        # スキーマプルーニング → Text2Cypher
    
    def run_query(self, db_manager, question, input_schema):
        # クエリ生成 → データベース実行
    
    def forward(self, db_manager, question, input_schema):
        # 完全なパイプライン実行
    
    async def aforward(self, db_manager, question, input_schema):
        # 非同期版（将来の拡張用）
```

### 9. 実行関数（行279-288）

```python
def run_graph_rag(questions: list[str], db_manager: KuzuDatabaseManager) -> list[Any]:
    schema = str(db_manager.get_schema_dict)
    rag = GraphRAG()
    results = []
    for question in questions:
        response = rag(db_manager=db_manager, question=question, input_schema=schema)
        results.append(response)
    return results
```

複数の質問をバッチ処理可能な設計

## 技術的特徴

1. **marimoアプリケーション**
   - リアクティブなUI
   - 自動更新される結果表示

2. **エラーハンドリング**
   - クエリ実行エラーの適切な処理
   - 空の結果への対応

3. **モジュラー設計**
   - データベース管理の分離
   - DSPyモジュールの再利用可能な構造

4. **非同期対応**
   - `aforward`メソッドで将来の非同期処理に対応

## 実行方法

```bash
# アプリとして実行
uv run marimo run graph_rag.py

# 開発モードで実行
uv run marimo edit graph_rag.py
```

## 使用例

1. テキストフィールドに質問を入力
2. Enterキーまたはフィールド外をクリック
3. スピナーが表示され、処理開始
4. 生成されたCypherクエリと回答が表示

## 拡張可能性

- 複数質問の同時処理
- クエリ履歴の保存
- ベクトル検索との統合
- グラフ可視化機能の追加
- より高度なエラーリカバリ機能
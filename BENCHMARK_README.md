# Graph RAG Benchmark テストスクリプト

このドキュメントは、Graph RAGシステムのベンチマークテストスクリプトの使い方を説明します。

## 概要

実装した機能の精度向上とパフォーマンス改善を自動的にテストするスクリプトセットです。

### 実装済みの機能

#### 精度向上機能
- **Exemplar Store**: 類似した過去の質問/クエリペアをLLMに提示
- **Post-processor**: 文字列比較に自動的にLOWER()を適用
- **Retry Loop**: クエリがエラーの場合に最大5回リトライ

#### パフォーマンス改善機能
- **LRU Cache**: 同じ質問+スキーマの組み合わせをキャッシュ

## ファイル構成

```
.
├── test_questions.py           # 9個のテスト質問と正解Cypherクエリ
├── graph_rag_core.py          # GraphRAGのコアロジック（marimo非依存）
├── benchmark.py               # フルベンチマークスクリプト
└── BENCHMARK_README.md
```

## テスト構成

### テスト質問（9問）

難易度別に分類された10個の質問：

**簡単（3問）**
- ID 1: 特定年のPhysics受賞者
- ID 2: Chemistry受賞者の数
- ID 3: 女性受賞者リスト

**中程度（4問）**
- ID 4: Cambridge所属のPhysics受賞者
- ID 5: 2000年以降の日本人受賞者
- ID 6: 受賞者数が最も多い機関
- ID 7: ヨーロッパ出身のChemistry受賞者

**難しい（3問）**
- ID 8: 複数回受賞者
- ID 9: アメリカの機関所属のMedicine受賞者

## 使い方

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. テスト質問の確認

```bash
uv run python test_questions.py
```

出力例：
```
================================================================================
TEST QUESTIONS FOR GRAPH RAG BENCHMARK
================================================================================

EASY QUESTIONS (3):
--------------------------------------------------------------------------------

ID: 1
Question: Who won the Nobel Prize in Physics in 2020?
Description: Simple filter with year and category
Cypher:
MATCH (s:Scholar)-[:WON]->(p:Prize)
WHERE p.awardYear = '2020' AND LOWER(p.category) = 'physics'
RETURN DISTINCT s.knownName AS scholar_name
...
```

### 4. ベンチマーク

9問 × 2パターンで動作確認：

```bash
uv run python benchmark.py
```

実行時間: 約30秒

出力例：
```
================================================================================
MINI GRAPH RAG BENCHMARK TEST
================================================================================
Start time: 2025-11-25 06:22:00
Test questions: 2
Configurations: 2
Runs per question: 2
================================================================================

Running benchmark: baseline
  [1/2] Who won the Nobel Prize in Physics in 2020?... ✓ 3041ms
  [2/2] How many scholars won prizes in Chemistry?... ✓ 3614ms

Cache Statistics:
  Hit Rate: 50.00%
  Total Requests: 4
  Hits: 2, Misses: 2
```

<!-- ### 5. フルベンチマーク実行

10問 × 6パターン × 3回 = 180回の実行：

```bash
uv run python benchmark.py
```

### 出力ファイル

実行後、以下のファイルが生成されます：

1. **benchmark_results.json** - 詳細なJSON形式の結果
   - すべての実行の詳細データ
   - 生成されたクエリ
   - 実行時間
   - エラーメッセージ

2. **benchmark_summary.csv** - サマリー統計のCSV
   ```csv
   config_name,success_rate,avg_execution_time_ms,cache_hit_rate,avg_retry_count,avg_query_similarity
   baseline,90.0%,1234.5,0.0%,0.50,45.2%
   exemplars_only,95.0%,1156.3,0.0%,0.30,52.1%
   cache_only,90.0%,234.2,66.7%,0.50,45.2%
   retry_only,97.0%,1345.1,0.0%,0.20,48.3%
   postprocess_only,93.0%,1198.4,0.0%,0.40,46.7%
   full_features,100.0%,189.3,66.7%,0.10,58.9%
   ```

3. **benchmark_charts.png** - 可視化グラフ
   - 平均実行時間の比較（棒グラフ）
   - 成功率の比較（棒グラフ）
   - キャッシュヒット率（棒グラフ）
   - クエリ類似度（棒グラフ）

## 測定メトリクス

### パフォーマンスメトリクス

- **実行時間**: 各質問の実行時間（ミリ秒）
- **平均実行時間**: 設定パターンごとの平均
- **中央値実行時間**: 外れ値の影響を除いた代表値
- **キャッシュヒット率**: キャッシュが有効だった割合

### 精度メトリクス

- **成功率**: クエリが正常に実行された割合
- **クエリ類似度**: 生成クエリと正解クエリの文字レベル類似度
- **平均リトライ回数**: エラー発生時の再試行回数
- **エラー率**: 実行失敗の割合

## カスタマイズ

### テスト質問の追加・変更

[test_questions.py](test_questions.py)を編集：

```python
TestQuestion(
    id=11,
    question="Your custom question here",
    cypher="MATCH ... RETURN ...",
    difficulty="medium",
    description="Description of what this tests"
)
```

### テストパターンの変更

[benchmark.py](benchmark.py)の`BENCHMARK_CONFIGS`を編集：

```python
BENCHMARK_CONFIGS = [
    BenchmarkConfig("custom_config", True, False, True, False, num_runs=5),
    # ... add more configs
]
```

### 実行回数の変更

各質問の実行回数を変更する場合：

```python
BenchmarkConfig("test", True, True, True, True, num_runs=5)  # 5回実行
``` -->

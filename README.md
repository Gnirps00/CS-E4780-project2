# Graph RAG with Kuzu, DSPy and marimo

Source code for course project to build a Graph RAG with Kuzu, [DSPy](https://dspy.ai/) and [marimo](https://docs.marimo.io/) (open source, reactive notebooks for Python).


## Project Structure

```
.
├── graph_rag.py                 # Main Graph RAG marimo app
├── graph_rag_core.py           # Standalone Graph RAG module (for benchmarking)
├── exemplar_store.py           # Similarity-based example retrieval
├── lru_cache.py                # Query caching system
├── cypher_post_processor.py    # Rule-based query correction
├── test_questions.py           # Benchmark test questions
├── benchmark.py                # Benchmark testing script
├── benchmark_org.py            # Original benchmark implementation
├── demo_workflow.py            # Step-by-step workflow demo
├── eda.py                      # Initial data exploration
├── create_nobel_api_graph.py   # Graph creation script
└── README.md                   # This file
```

## Setup

We recommend using the `uv` package manager
to manage dependencies.

```bash
# Uses the local pyproject.toml to add dependencies
uv sync
# Or, add them manually
uv add marimo dspy kuzu polars pyarrow
# Don't forget to source virtual env
source .venv/bin/activate
```

### Start Kuzu Database
```bash
docker compose up
```
Go to `localhost:8000` you can check the UI of the database

### Create basic graph
marimo simultaneously serves three functions. You can run Python code as a script, a notebook, or as an app!

#### Run as a notebook

You can manually activate the local uv virtual environment and run marimo as follows:
```bash
# Open a marimo notebook in edit mode
marimo edit eda.py
```
Or, you can simply use uv to run marimo:
```bash
uv run marimo edit eda.py
```

#### Run as an app

To run marimo in app mode, use the `run` command.

```bash
uv run marimo run eda.py
```

#### Run as a script

Each cell block in a marimo notebook is encapsulated into functions, so you can reuse them in other
parts of your codebase. You can also run the marimo file (which is a `*.py` Python file) as you
would any other script:

```bash
uv run eda.py
```
Returns:
```
726 laureate nodes ingested
399 prize nodes ingested
739 laureate prize awards ingested
```

Depending on the stage of your project and who is consuming your code and data, each mode can be
useful in its own right. Have fun using marimo and Kuzu!

### Enrich the graph 
Create the required graph in Kuzu using the following script:

```bash
uv run create_nobel_api_graph.py
```

Alternatively, you can open/edit the script as a marimo notebook and run each cell individually to
go through the entire workflow step by step.

```bash
uv run marimo edit create_nobel_api_graph.py
```

### Run the Graph RAG pipeline as a notebook

To iterate on your ideas and experiment with your approach, you can work through the Graph RAG
notebook in the following marimo file:

```bash
uv run marimo run demo_workflow.py
```

The purpose of this file is to demonstrate the workflow in distinct stages, making it easier to
understand and modify each part of the process in marimo.

### Run the Graph RAG app

A demo app is provided in `graph_rag.py` for reference. It's very basic (just question-answering), but the
idea is general and this can be extended to include advanced retrieval workflows (vector + graph),
interactive graph visualizations via anywidget, and more. More on this in future tutorials!

```bash
uv run marimo run graph_rag.py
```

## Features

This Graph RAG system includes several features to improve both accuracy and performance of natural language to Cypher query translation.

### Accuracy Improvement Features

#### 1. Exemplar Store ([exemplar_store.py](exemplar_store.py))

Uses semantic similarity search to retrieve relevant question-Cypher pairs as examples for the LLM, improving query generation accuracy by providing concrete examples and reducing errors in complex graph patterns.

**How it works:**
- Stores a collection of example questions with their corresponding Cypher queries
- When a user asks a question, finds the top-k most similar examples using sentence-transformers
- Provides these examples as context to guide the LLM in generating correct Cypher queries

#### 2. Post-processor ([cypher_post_processor.py](cypher_post_processor.py))

Applies rule-based corrections to generated Cypher queries to fix common LLM mistakes, ensuring consistent case-insensitive string comparisons and reducing query execution errors.

**Current features:**
- **Automatic LOWER() enforcement**: Ensures all string comparisons use lowercase conversion for case-insensitive matching
- Follows the pattern: `LOWER(property) CONTAINS 'value'` or `LOWER(property) = 'value'`

**Example transformation:**
```cypher
# Before post-processing
WHERE s.name CONTAINS 'John'

# After post-processing
WHERE LOWER(s.name) CONTAINS 'john'
```

#### 3. Retry Loop with Error Feedback ([graph_rag_core.py](graph_rag_core.py))

Automatically retries query generation when execution fails, providing error context to the LLM for self-correction, significantly improving success rate on difficult questions by recovering from syntax errors and invalid queries.

**How it works:**
- Attempts to execute the generated Cypher query
- If execution fails (RuntimeError), captures the error message
- Sends question, failed query, and error message back to LLM
- LLM generates a corrected query based on the error feedback
- Retries up to 5 times before giving up

### Performance Improvement Features

#### 4. LRU Cache ([lru_cache.py](lru_cache.py))

Caches generated Cypher queries for identical question-schema pairs to avoid redundant LLM calls, dramatically reducing response time for repeated questions and API costs.

**How it works:**
- Uses question text + pruned schema as cache key
- Stores previously generated queries in an LRU (Least Recently Used) cache
- Returns cached query immediately if found, bypassing LLM entirely
- Evicts least recently used entries when cache is full

### Feature Configuration

All features can be enabled/disabled via boolean flags in the GraphRAG class:

```python
from graph_rag_core import GraphRAG

# Enable all features (recommended)
rag = GraphRAG(
    use_exemplars=True,      # Exemplar Store
    use_cache=True,          # LRU Cache
    use_loop=True,           # Retry Loop
    use_post_process=True    # Post-processor
)

# Baseline configuration (no features)
rag_baseline = GraphRAG(
    use_exemplars=False,
    use_cache=False,
    use_loop=False,
    use_post_process=False
)
```

## Benchmark Testing

A comprehensive benchmark system is provided to evaluate the effectiveness of each feature.

### Test Dataset

The benchmark uses 9 diverse test questions ([test_questions.py](test_questions.py)).

### Running Benchmarks
#### Run Full Benchmark

```bash
uv run python benchmark.py
```

Tests all 9 questions with three configurations:
- **baseline**: All features disabled
- **full_features**: All features enabled
- **only_cache**: Only cache enabled

Each question is run twice to test cache effectiveness.

### Measured Metrics

**Performance Metrics:**
- **Execution time**: Time to generate and execute each query (milliseconds)
- **Query generation time**: Time spent in LLM calls for query creation
- **Query execution time**: Time spent running query on database
- **Cache hit rate**: Percentage of queries served from cache

**Accuracy Metrics:**
- **Success rate**: Percentage of queries that executed successfully
- **Error analysis**: Types of errors encountered
- **Query correctness**: Comparison with ground truth Cypher (manual inspection)
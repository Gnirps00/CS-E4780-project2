#!/usr/bin/env python3
"""
Mini benchmark script to test with a subset of data.
Tests 2 questions with 2 configurations.
"""

import os
import sys
import time
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

import dspy
from dspy.adapters.baml_adapter import BAMLAdapter

# Import project modules
from test_questions import TEST_QUESTIONS
from graph_rag_core import GraphRAG, KuzuDatabaseManager


# Use only 2 questions and 2 configs for quick testing
# TEST_QUESTIONS_MINI = TEST_QUESTIONS[:2]  # First 2 questions


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run."""
    name: str
    use_exemplars: bool
    use_cache: bool
    use_loop: bool
    use_post_process: bool
    num_runs: int = 2  # Run each question 2 times


# Test only 2 configurations
BENCHMARK_CONFIGS_MINI = [
    # BenchmarkConfig("baseline", False, False, False, False),
    BenchmarkConfig("full_features", True, True, True, True),
    # BenchmarkConfig("only_cache", False, True, False, False),
]


# ============================================================================
# LLM Setup
# ============================================================================

load_dotenv()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found in environment variables")

lm = dspy.LM(
    model="openrouter/google/gemini-2.0-flash-001",
    api_base="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
dspy.configure(lm=lm, adapter=BAMLAdapter())


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main benchmark execution."""
    print("=" * 80)
    print("MINI GRAPH RAG BENCHMARK TEST")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test questions: {len(TEST_QUESTIONS)}")
    print(f"Configurations: {len(BENCHMARK_CONFIGS_MINI)}")
    print(f"Runs per question: {BENCHMARK_CONFIGS_MINI[0].num_runs}")
    print("=" * 80)

    # Initialize database
    db_manager = KuzuDatabaseManager("nobel.kuzu")
    schema = str(db_manager.get_schema_dict)

    execution_times = [[] for _ in BENCHMARK_CONFIGS_MINI]

    for idx, config in enumerate(BENCHMARK_CONFIGS_MINI):
        print(f"\n{'='*80}")
        print(f"Running benchmark: {config.name}")
        print(f"  Exemplars: {config.use_exemplars}, Cache: {config.use_cache}, "
              f"Retry: {config.use_loop}, PostProcess: {config.use_post_process}")
        print(f"{'='*80}\n")

        # Create GraphRAG instance with config
        rag = GraphRAG(
            use_exemplars=config.use_exemplars,
            use_cache=config.use_cache,
            use_loop=config.use_loop,
            use_post_process=config.use_post_process,
        )

        # Run all questions multiple times
        for run_number in range(1, config.num_runs + 1):
            print(f"\nRun {run_number}/{config.num_runs}:")
            for i, question in enumerate(TEST_QUESTIONS, 1):
                print(f"\n  [{i}/{len(TEST_QUESTIONS)}] Question: {question.question}")
                print(f"      Expected Cypher: {question.cypher}")

                start_time = time.perf_counter()
                try:
                    result = rag(
                        db_manager=db_manager,
                        question=question.question,
                        input_schema=schema
                    )

                    end_time = time.perf_counter()
                    execution_time_ms = (end_time - start_time) * 1000

                    execution_times[idx].append(execution_time_ms)

                    if result and 'query' in result and result['query']:
                        cache_indicator = ""
                        if config.use_cache and hasattr(rag, 'cache') and rag.cache:
                            stats = rag.cache.get_stats()
                            if stats['hits'] > 0:
                                cache_indicator = " (cache)"

                        print(f"      ✓ Status: Success {execution_time_ms:.0f}ms{cache_indicator}")
                        print(f"      Generated Cypher: {result['query']}")

                        if 'answer' in result and result['answer']:
                            answer_text = result['answer'].response[:100] if hasattr(result['answer'], 'response') else str(result['answer'])[:100]
                            print(f"      Answer: {answer_text}...")

                        if 'create_query_time_ms' in result and 'query_time_ms' in result:
                            print(f"      Query Creation Time: {result['create_query_time_ms']:.0f}ms")
                            print(f"      Query Execution Time: {result['query_time_ms']:.0f}ms")
                    else:
                        print(f"      ✗ Status: Empty result ({execution_time_ms:.0f}ms)")

                except Exception as e:
                    end_time = time.perf_counter()
                    execution_time_ms = (end_time - start_time) * 1000
                    execution_times[idx].append(execution_time_ms)
                    print(f"      ✗ Status: Error ({execution_time_ms:.0f}ms)")
                    print(f"      Error: {str(e)[:100]}")

        # Print cache statistics if cache is enabled
        if config.use_cache and hasattr(rag, 'cache') and rag.cache:
            cache_stats = rag.cache.get_stats()
            print(f"\nCache Statistics:")
            print(f"  Hit Rate: {cache_stats['hit_rate']:.2%}")
            print(f"  Total Requests: {cache_stats['total_requests']}")
            print(f"  Hits: {cache_stats['hits']}, Misses: {cache_stats['misses']}")

    for idx, config in enumerate(BENCHMARK_CONFIGS_MINI):
        times = execution_times[idx]
        if times:
            avg_time = sum(times) / len(times)
            print(f"\nAverage execution time for config '{config.name}': {avg_time:.0f}ms over {len(times)} runs")
        else:
            print(f"\nNo execution times recorded for config '{config.name}'")

    print("\n" + "=" * 80)
    print("MINI BENCHMARK COMPLETE")
    print("=" * 80)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

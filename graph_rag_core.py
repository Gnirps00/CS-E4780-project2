#!/usr/bin/env python3
"""
Core classes and signatures extracted from graph_rag.py for use in benchmark scripts.
This module contains all the necessary components without marimo dependencies.
"""

import time
from typing import Any
import dspy
import kuzu
from pydantic import BaseModel, Field

from exemplar_store import ExemplarStore
from lru_cache import Text2CypherCache
from cypher_post_processor import CypherPostProcessor


# ============================================================================
# Pydantic Models
# ============================================================================

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
    to: Node = Field(alias="to", description="Target node label")
    properties: list[Property] | None


class GraphSchema(BaseModel):
    nodes: list[Node]
    edges: list[Edge]


# ============================================================================
# DSPy Signatures
# ============================================================================

class PruneSchema(dspy.Signature):
    """
    Understand the given labelled property graph schema and the given user question. Your task
    is to return ONLY the subset of the schema (node labels, edge labels and properties) that is
    relevant to the question.
        - The schema is a list of nodes and edges in a property graph.
        - The nodes are the entities in the graph.
        - The edges are the relationships between the nodes.
        - Properties of nodes and edges are their attributes, which helps answer the question.
    """

    question: str = dspy.InputField()
    input_schema: str = dspy.InputField()
    pruned_schema: GraphSchema = dspy.OutputField()


class Text2Cypher(dspy.Signature):
    """
    Translate the question into a valid Cypher query that respects the graph schema.

    <SYNTAX>
    - When matching on Scholar names, ALWAYS match on the `knownName` property
    - For countries, cities, continents and institutions, you can match on the `name` property
    - Use short, concise alphanumeric strings as names of variable bindings (e.g., `a1`, `r1`, etc.)
    - Always strive to respect the relationship direction (FROM/TO) using the schema information.
    - When comparing string properties, ALWAYS do the following:
        - Lowercase the property values before comparison
        - Use the WHERE clause
        - Use the CONTAINS operator to check for presence of one substring in the other
    - DO NOT use APOC as the database does not support it.
    </SYNTAX>

    <RETURN_RESULTS>
    - If the result is an integer, return it as an integer (not a string).
    - When returning results, return property values rather than the entire node or relationship.
    - Do not attempt to coerce data types to number formats (e.g., integer, float) in your results.
    - NO Cypher keywords should be returned by your query.
    </RETURN_RESULTS>
    """

    question: str = dspy.InputField()
    input_schema: str = dspy.InputField()
    query: Query = dspy.OutputField()


class Text2CypherWithExemplars(dspy.Signature):
    """
    Translate the question into a valid Cypher query that respects the graph schema by using the provided examples as reference.

    EXAMPLES:
    {exemplars}

    <SYNTAX>
    - When matching on Scholar names, ALWAYS match on the `knownName` property
    - For countries, cities, continents and institutions, you can match on the `name` property
    - Use short, concise alphanumeric strings as names of variable bindings (e.g., `a1`, `r1`, etc.)
    - Always strive to respect the relationship direction (FROM/TO) using the schema information.
    - When comparing string properties, ALWAYS do the following:
        - Lowercase the property values before comparison
        - Use the WHERE clause
        - Use the CONTAINS operator to check for presence of one substring in the other
    - DO NOT use APOC as the database does not support it.
    </SYNTAX>

    <RETURN_RESULTS>
    - If the result is an integer, return it as an integer (not a string).
    - When returning results, return property values rather than the entire node or relationship.
    - Do not attempt to coerce data types to number formats (e.g., integer, float) in your results.
    - NO Cypher keywords should be returned by your query.
    </RETURN_RESULTS>
    """

    question: str = dspy.InputField()
    input_schema: str = dspy.InputField()
    exemplars: str = dspy.InputField()
    query: Query = dspy.OutputField()


class Text2CypherWithSelfRefinementLoop(dspy.Signature):
    """
    Translate the question into a valid Cypher query.
    Does the validation and loops again to create valid query if query is not valid.
    Sends LLM the triple containing past questions, queries and error messages

    <SYNTAX>
    - When matching on Scholar names, ALWAYS match on the `knownName` property
    - For countries, cities, continents and institutions, you can match on the `name` property
    - Use short, concise alphanumeric strings as names of variable bindings (e.g., `a1`, `r1`, etc.)
    - Always strive to respect the relationship direction (FROM/TO) using the schema information.
    - When comparing string properties, ALWAYS do the following:
        - Lowercase the property values before comparison
        - Use the WHERE clause
        - Use the CONTAINS operator to check for presence of one substring in the other
    - DO NOT use APOC as the database does not support it.
    </SYNTAX>

    <RETURN_RESULTS>
    - If the result is an integer, return it as an integer (not a string).
    - When returning results, return property values rather than the entire node or relationship.
    - Do not attempt to coerce data types to number formats (e.g., integer, float) in your results.
    - NO Cypher keywords should be returned by your query.
    </RETURN_RESULTS>
    """

    question: str = dspy.InputField()
    input_schema: str = dspy.InputField()
    exemplars: str = dspy.InputField()
    triples: str = dspy.InputField()
    query: Query = dspy.OutputField()


class AnswerQuestion(dspy.Signature):
    """
    - Use the provided question, the generated Cypher query and the context to answer the question.
    - If the context is empty, state that you don't have enough information to answer the question.
    - When dealing with dates, mention the month in full.
    """

    question: str = dspy.InputField()
    cypher_query: str = dspy.InputField()
    context: str = dspy.InputField()
    response: str = dspy.OutputField()


# ============================================================================
# Database Manager
# ============================================================================

class KuzuDatabaseManager:
    """Manages Kuzu database connection and schema retrieval."""

    def __init__(self, db_path: str = "ldbc_1.kuzu"):
        self.db_path = db_path
        self.db = kuzu.Database(db_path, read_only=True)
        self.conn = kuzu.Connection(self.db)

    @property
    def get_schema_dict(self) -> dict[str, list[dict]]:
        dict_start_time = time.perf_counter()
        response = self.conn.execute("CALL SHOW_TABLES() WHERE type = 'NODE' RETURN *;")
        nodes = [row[1] for row in response]  # type: ignore
        response = self.conn.execute("CALL SHOW_TABLES() WHERE type = 'REL' RETURN *;")
        rel_tables = [row[1] for row in response]  # type: ignore
        relationships = []
        for tbl_name in rel_tables:
            response = self.conn.execute(f"CALL SHOW_CONNECTION('{tbl_name}') RETURN *;")
            for row in response:
                relationships.append({"name": tbl_name, "from": row[0], "to": row[1]})  # type: ignore
        schema = {"nodes": [], "edges": []}

        for node in nodes:
            node_schema = {"label": node, "properties": []}
            node_properties = self.conn.execute(f"CALL TABLE_INFO('{node}') RETURN *;")
            for row in node_properties:  # type: ignore
                node_schema["properties"].append({"name": row[1], "type": row[2]})  # type: ignore
            schema["nodes"].append(node_schema)

        for rel in relationships:
            edge = {
                "label": rel["name"],
                "from": rel["from"],
                "to": rel["to"],
                "properties": [],
            }
            rel_properties = self.conn.execute(f"""CALL TABLE_INFO('{rel["name"]}') RETURN *;""")
            for row in rel_properties:  # type: ignore
                edge["properties"].append({"name": row[1], "type": row[2]})  # type: ignore
            schema["edges"].append(edge)
        dict_end_time = time.perf_counter()
        dict_time = (dict_end_time - dict_start_time) * 1000

        # Suppress print for benchmark (optional)
        # print(f"================================Process Start==================================")
        # print(f"Time taken to get schema as dict: {dict_time:.2f} milliseconds")
        return schema


# ============================================================================
# GraphRAG Module
# ============================================================================

class GraphRAG(dspy.Module):
    """
    DSPy custom module that applies Text2Cypher to generate a query and run it
    on the Kuzu database, to generate a natural language response.
    """

    def __init__(self, use_exemplars: bool = True, use_cache: bool = True, use_loop: bool = True, use_post_process: bool = True):
        self.prune = dspy.Predict(PruneSchema)
        self.use_exemplars = use_exemplars
        self.use_loop = use_loop
        self.use_post_process = use_post_process
        self.triples = []

        if use_exemplars:
            self.exemplar_store = ExemplarStore()
            if use_loop:
                self.text2cypher = dspy.ChainOfThought(Text2CypherWithSelfRefinementLoop)
            else:
                self.text2cypher = dspy.ChainOfThought(Text2CypherWithExemplars)
        else:
            self.text2cypher = dspy.ChainOfThought(Text2Cypher)

        if use_cache:
            self.cache = Text2CypherCache()
        else:
            self.cache = None

        if use_post_process:
            self.post_processor = CypherPostProcessor()
        else:
            self.post_processor = None

        self.generate_answer = dspy.ChainOfThought(AnswerQuestion)

    def _format_exemplars(self, exemplars: list[dict]) -> str:
        """Format exemplars into readable format"""
        formatted = []
        for i, ex in enumerate(exemplars, 1):
            formatted.append(f"""Example {i} (similarity: {ex['similarity']:.2f}):Question: {ex['question']} Cypher: {ex['cypher']}""")
        return "\n".join(formatted)

    def _format_triples(self, triples: list[dict]) -> str:
        """
        Format a list of triples (question, query, error) into a readable block format
        for use inside DSPy signature inputs.
        """
        blocks = []
        for i, t in enumerate(triples, 1):
            block = f"""=== TRIPLE {i} ===
                QUESTION: {t['question']}
                QUERY: {t['query']}
                ERROR: {t['error']}
                """
            blocks.append(block)
        return "\n".join(blocks)

    def get_cypher_query(self, question: str, input_schema: str) -> tuple[Query, Any]:
        prune_start = time.perf_counter()
        prune_result = self.prune(question=question, input_schema=input_schema)
        prune_end = time.perf_counter()
        prune_time = (prune_end - prune_start) * 1000
        # print(f"Time taken for pruning schema: {prune_time:.2f} milliseconds")
        schema = prune_result.pruned_schema

        create_query_start = time.perf_counter()
        # キャッシュをチェック
        if hasattr(self, 'cache') and self.cache:
            cache_result = self.cache.get(question, str(schema))
            if cache_result:
                # print(f"Cache hit \n Stats: {self.cache.get_stats()}")
                create_query_end = time.perf_counter()
                create_query_time = (create_query_end - create_query_start) * 1000
                # print(f"Time taken for creating query with cache: {create_query_time:.2f} milliseconds")
                return cache_result['query']
        # キャッシュヒットしない場合はクエリ生成
        if self.use_exemplars:
            # 類似した例を取得
            similar_examples = self.exemplar_store.get_similar_exemplars(question, k=3)
            exemplars_text = self._format_exemplars(similar_examples)
            # Text2Cypherに例を渡す、ループがオンなら追加で過去の質問、クエリとエラーメッセージを渡す
            if self.use_loop:
                triples_text = self._format_triples(self.triples)
                text2cypher_result = self.text2cypher(
                    question=question,
                    input_schema=schema,
                    exemplars=exemplars_text,
                    triples=triples_text
                )
            else:
                text2cypher_result = self.text2cypher(
                    question=question,
                    input_schema=schema,
                    exemplars=exemplars_text
                )
        else:
            text2cypher_result = self.text2cypher(question=question, input_schema=schema)
        cypher_query = text2cypher_result.query

        # post_processorにてルールベースでクエリを修正(現在Lowercase強制のみ実装)
        if self.post_processor:
            original_query = cypher_query.query
            processed_query = self.post_processor.post_process(original_query)
            cypher_query.query = processed_query

        create_query_end = time.perf_counter()
        create_query_time = (create_query_end - create_query_start) * 1000
        # print(f"Time taken for creating query without cache: {create_query_time:.2f} milliseconds")
        return cypher_query, schema

    def run_query(
        self, db_manager: KuzuDatabaseManager, question: str, input_schema: str
    ) -> tuple[str, list[Any] | None]:
        """
        Run a query synchronously on the database.
        """
        # ループがオンならエラー出なくなるまでexecuteし続ける
        result = None
        query = ""

        max_tries = 5 if self.use_loop else 1
        tries = 0

        query_start = time.perf_counter()
        while True:
            try:
                tries += 1
                cypher_query, schema = self.get_cypher_query(question=question, input_schema=input_schema)
                query = cypher_query.query
                # Run the query on the database
                result = db_manager.conn.execute(query)

                # キャッシュに追加
                if hasattr(self, 'cache') and self.cache:
                    self.cache.set(question, str(schema), cypher_query)
                
                results = [item for row in result for item in row]
                break
            except RuntimeError as e:
                if tries >= max_tries:
                    # print(f"Maximum number of error running query passed, giving up")
                    results = None
                    break
                newTriple = {
                    "question": question,
                    "query": query,
                    "errorMessage": str(e)
                }
                # print(f"Error running query, new triple added: {newTriple}")
                self.triples.append(newTriple)

        query_end = time.perf_counter()
        query_time = (query_end - query_start) * 1000
        # print(f"Time taken for running query: {query_time:.2f} milliseconds")
        return query, results

    def forward(self, db_manager: KuzuDatabaseManager, question: str, input_schema: str):
        final_query, final_context = self.run_query(db_manager, question, input_schema)
        if final_context is None:
            # print("Empty results obtained from the graph database. Please retry with a different question.")
            return {}
        else:
            answer = self.generate_answer(
                question=question, cypher_query=final_query, context=str(final_context)
            )
            response = {
                "question": question,
                "query": final_query,
                "answer": answer,
            }
            return response

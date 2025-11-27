#!/usr/bin/env python3
"""
Test questions for Graph RAG benchmark.
Contains 10 diverse questions with correct Cypher queries for accuracy evaluation.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class TestQuestion:
    """A test question with its expected Cypher query."""
    id: int
    question: str
    cypher: str
    difficulty: str  # "easy", "medium", "hard"
    description: str


# Test questions dataset
TEST_QUESTIONS: List[TestQuestion] = [
    # Easy questions (1-3)
    TestQuestion(
        id=1,
        question="Who won the Nobel Prize in Physics in 2020?",
        cypher="""MATCH (s:Scholar)-[:WON]->(p:Prize)
WHERE p.awardYear = '2020' AND LOWER(p.category) = 'physics'
RETURN DISTINCT s.knownName AS scholar_name""",
        difficulty="easy",
        description="Simple filter with year and category"
    ),

    TestQuestion(
        id=2,
        question="How many scholars won prizes in Chemistry?",
        cypher="""MATCH (s:Scholar)-[:WON]->(p:Prize)
WHERE LOWER(p.category) = 'chemistry'
RETURN COUNT(DISTINCT s) AS scholar_count""",
        difficulty="easy",
        description="Simple count with category filter"
    ),

    TestQuestion(
        id=3,
        question="List all female Nobel Prize winners",
        cypher="""MATCH (s:Scholar)-[:WON]->(p:Prize)
WHERE LOWER(s.gender) = 'female'
RETURN DISTINCT s.knownName AS scholar_name, p.category AS category, p.awardYear AS year
ORDER BY year""",
        difficulty="easy",
        description="Simple filter by gender with sorting"
    ),

    # Medium questions (4-7)
    TestQuestion(
        id=4,
        question="Which scholars affiliated with Cambridge won Physics prizes?",
        cypher="""MATCH (s:Scholar)-[:AFFILIATED_WITH]->(i:Institution)
WHERE LOWER(i.name) CONTAINS 'cambridge'
MATCH (s)-[:WON]->(p:Prize)
WHERE LOWER(p.category) = 'physics'
RETURN DISTINCT s.knownName AS scholar_name, p.awardYear AS year, i.name AS institution""",
        difficulty="medium",
        description="Multi-node join with institution filter"
    ),

#     TestQuestion(
#         id=5,
#         question="Find Japanese scholars who won prizes after 2000",
#         cypher="""MATCH (s:Scholar)-[:BORN_IN]->(c:City)-[:IS_CITY_IN]->(co:Country)
# WHERE LOWER(co.name) CONTAINS 'japan'
# MATCH (s)-[:WON]->(p:Prize)
# WHERE p.awardYear > '2000'
# RETURN DISTINCT s.knownName AS scholar_name, p.category AS category, p.awardYear AS year
# ORDER BY year""",
#         difficulty="medium",
#         description="Geographic filter with time range"
#     ),

    TestQuestion(
        id=6,
        question="Which institutions have the most Nobel Prize winners?",
        cypher="""MATCH (s:Scholar)-[:AFFILIATED_WITH]->(i:Institution)
MATCH (s)-[:WON]->(p:Prize)
WITH i.name AS institution, COUNT(DISTINCT s) AS winner_count
RETURN institution, winner_count
ORDER BY winner_count DESC
LIMIT 10""",
        difficulty="medium",
        description="Aggregation with grouping and sorting"
    ),

    TestQuestion(
        id=7,
        question="Find scholars born in Europe who won Chemistry prizes",
        cypher="""MATCH (s:Scholar)-[:BORN_IN]->(c:City)-[:IS_CITY_IN]->(co:Country)-[:IS_COUNTRY_IN]->(cont:Continent)
WHERE LOWER(cont.name) = 'europe'
MATCH (s)-[:WON]->(p:Prize)
WHERE LOWER(p.category) = 'chemistry'
RETURN DISTINCT s.knownName AS scholar_name, co.name AS country, p.awardYear AS year""",
        difficulty="medium",
        description="Deep hierarchy with continent-level filter"
    ),

    # Hard questions (8-10)
    TestQuestion(
        id=8,
        question="Who won multiple Nobel prizes? Show their categories and years",
        cypher="""MATCH (s:Scholar)-[:WON]->(p:Prize)
WITH s, COUNT(DISTINCT p) AS prize_count
WHERE prize_count > 1
MATCH (s)-[:WON]->(p2:Prize)
RETURN s.knownName AS scholar_name,
       COLLECT(DISTINCT p2.category) AS categories,
       COLLECT(DISTINCT p2.awardYear) AS years,
       prize_count
ORDER BY prize_count DESC""",
        difficulty="hard",
        description="Complex aggregation with filtering and collection"
    ),

#     TestQuestion(
#         id=9,
#         question="Find scholars affiliated with institutions in the United States who won prizes in Medicine",
#         cypher="""MATCH (s:Scholar)-[:AFFILIATED_WITH]->(i:Institution)-[:IS_LOCATED_IN]->(c:City)-[:IS_CITY_IN]->(co:Country)
# WHERE LOWER(co.name) CONTAINS 'united states' OR LOWER(co.name) = 'usa'
# MATCH (s)-[:WON]->(p:Prize)
# WHERE LOWER(p.category) CONTAINS 'medicine'
# RETURN DISTINCT s.knownName AS scholar_name, i.name AS institution, c.name AS city, p.awardYear AS year
# ORDER BY year DESC""",
#         difficulty="hard",
#         description="Deep institution hierarchy with multiple name variations"
#     ),
]


def get_questions_by_difficulty(difficulty: str) -> List[TestQuestion]:
    """Get all questions of a specific difficulty level."""
    return [q for q in TEST_QUESTIONS if q.difficulty == difficulty]


def get_question_by_id(question_id: int) -> TestQuestion:
    """Get a specific question by ID."""
    for q in TEST_QUESTIONS:
        if q.id == question_id:
            return q
    raise ValueError(f"Question with ID {question_id} not found")


if __name__ == "__main__":
    # Print all test questions for verification
    print("=" * 80)
    print("TEST QUESTIONS FOR GRAPH RAG BENCHMARK")
    print("=" * 80)

    for difficulty in ["easy", "medium", "hard"]:
        questions = get_questions_by_difficulty(difficulty)
        print(f"\n{difficulty.upper()} QUESTIONS ({len(questions)}):")
        print("-" * 80)
        for q in questions:
            print(f"\nID: {q.id}")
            print(f"Question: {q.question}")
            print(f"Description: {q.description}")
            print(f"Cypher:\n{q.cypher}")

    print("\n" + "=" * 80)
    print(f"Total: {len(TEST_QUESTIONS)} questions")

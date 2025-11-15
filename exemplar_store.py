from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Tuple
import json

class ExemplarStore:
    def __init__(self, embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        self.encoder = SentenceTransformer(embedding_model)
        self.exemplars = []
        self.embeddings = None
        self.load_default_exemplars()

    def add_exemplar(self, question: str, cypher: str, schema_context: str = ""):
        exemplar = {
            "question": question,
            "cypher": cypher,
            "schema_context": schema_context
        }
        self.exemplars.append(exemplar)
        # 埋め込み更新
        self._update_embeddings()
    
    def _update_embeddings(self):
        questions = [ex["question"] for ex in self.exemplars]
        self.embeddings = self.encoder.encode(questions)
    
    def get_similar_exemplars(self, question: str, k:int = 3) -> List[Dict]:
        if not self.exemplars:
            return []
        
        # 入力質問の埋め込み
        query_embedding = self.encoder.encode([question])

        # コサイン類似度を計算
        similarities = np.dot(self.embeddings, query_embedding.T).squeeze()

        # top kのインデックス取得
        top_k_indices = np.argsort(similarities)[::-1][:k]

        # 類似度スコア付きで返す
        results = []
        for idx in top_k_indices:
            results.append({
                **self.exemplars[idx],
                "similarity": float(similarities[idx])
            })
        
        return results
    
    def load_default_exemplars(self):
        default_exemplars = [
          # 例1: カテゴリーでフィルタする基本的なクエリ
          {
              "question": "Which scholars won prizes in Physics?",
              "cypher": "MATCH (s:Scholar)-[:WON]->(p:Prize) WHERE LOWER(p.category) CONTAINS 'physics' RETURN DISTINCT s.knownName AS scholar_name, p.awardYear AS year",
              "schema_context": "Scholar nodes have knownName property, Prize nodes have category (lowercase) and awardYear properties, connected by WON relationship"
          },
          # 例2: 機関でフィルタ
          {
              "question": "Find scholars affiliated with Harvard who won prizes",
              "cypher": "MATCH (s:Scholar)-[:AFFILIATED_WITH]->(i:Institution) WHERE LOWER(i.name) CONTAINS 'harvard' MATCH (s)-[:WON]->(p:Prize) RETURN DISTINCT s.knownName AS scholar_name, p.category AS category, p.awardYear AS year",
              "schema_context": "Scholar->AFFILIATED_WITH->Institution (name property), Scholar->WON->Prize pattern"
          },
          # 例3: 国別の受賞者検索
          {
              "question": "Which Japanese scholars won Nobel prizes?",
              "cypher": "MATCH (s:Scholar)-[:BORN_IN]->(c:City)-[:IS_CITY_IN]->(co:Country) WHERE LOWER(co.name) CONTAINS 'japan' MATCH (s)-[:WON]->(p:Prize) RETURN DISTINCT s.knownName AS scholar_name, p.category AS category, p.awardYear AS year",
              "schema_context": "Scholar->BORN_IN->City->IS_CITY_IN->Country chain, Country has name property"
          },
          # 例4: 複数受賞者の検索
          {
              "question": "Who won multiple Nobel prizes?",
              "cypher": "MATCH (s:Scholar)-[:WON]->(p:Prize) WITH s, COUNT(DISTINCT p) AS prize_count WHERE prize_count > 1 MATCH (s)-[:WON]->(p2:Prize) RETURN s.knownName AS scholar_name, COLLECT(DISTINCT p2.category) AS categories, COLLECT(DISTINCT p2.awardYear) AS years",
              "schema_context": "Use WITH clause for aggregation, COUNT for counting prizes per scholar"
          },
          # 例5: 特定年の受賞者検索
          {
              "question": "Who won the Nobel Prize in 2020?",
              "cypher": "MATCH (s:Scholar)-[:WON]->(p:Prize) WHERE p.awardYear = 2020 RETURN DISTINCT s.knownName AS scholar_name, p.category AS category",
              "schema_context": "Prize nodes have awardYear property (integer), use = for exact year match"
          }
        ]
        for exemplar in default_exemplars:
            self.exemplars.append(exemplar)
        self._update_embeddings()
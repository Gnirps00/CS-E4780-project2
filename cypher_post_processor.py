
from typing import Tuple, List
import re

class CypherPostProcessor:
    def __init__(self):
        # 文字列比較が必要なプロパティ
        self.non_string_properties = [
            # int
            'prizeAmount', 
            'prizeAmountAdjusted',
            # 文字列だが日付なので不要
            'birthDate',
            'deathDate', 
            'dateAwarded',
            'awardYear',
        ]
    
    def post_process(self, query: str) -> Tuple[str, List[str]]:
        # lowercaseを
        query, modified_queries = self._enforce_lowercase_comparison(query)

        if modified_queries == []:
            print("No modified queries")
        else:
            print(f"modified queries:{modified_queries}")
        # Todo: ルール追加

        return query
    
    def _enforce_lowercase_comparison(self, query: str) -> Tuple[str, bool]:
        """
        文字列プロパティの比較で自動的にLOWER()を適用
        
        対応パターン:
        1. WHERE x.property = 'value'
        2. WHERE x.property CONTAINS 'value'
        3. AND/OR 句内の比較
        """
        modified_queries = []
        original_query = query
        
        # パターン1: property = 'value' (すでにLOWER()がない場合)
        # 例: WHERE s.knownName = 'Einstein' -> WHERE LOWER(s.knownName) = LOWER('Einstein')
        pattern_equals = r'(\w+)\.(\w+)\s*=\s*["\']([^"\']+)["\']'
        
        def replace_equals(match):
            var_name = match.group(1)
            prop_name = match.group(2)
            value = match.group(3)
            
            # 文字列プロパティかつまだLOWER()で囲まれていない場合
            if prop_name not in self.non_string_properties:
                # 既にLOWER()で囲まれているかチェック
                start_pos = match.start()
                # 前方にLOWER(があるかチェック
                check_prefix = query[max(0, start_pos-10):start_pos]
                if 'LOWER(' not in check_prefix.upper():
                    modified_queries.append(f"Applied LOWER() to {var_name}.{prop_name} = comparison")
                    return f"LOWER({var_name}.{prop_name}) = LOWER('{value}')"
            
            return match.group(0)  # 変更なし
        
        query = re.sub(pattern_equals, replace_equals, query, flags=re.IGNORECASE)
        
        # パターン2: property CONTAINS 'value'
        # 例: WHERE i.name CONTAINS 'Harvard' -> WHERE LOWER(i.name) CONTAINS LOWER('harvard')
        pattern_contains = r'(\w+)\.(\w+)\s+CONTAINS\s+["\']([^"\']+)["\']'
        
        def replace_contains(match):
            var_name = match.group(1)
            prop_name = match.group(2)
            value = match.group(3)
            
            if prop_name not in self.non_string_properties:
                check_prefix = query[max(0, match.start()-10):match.start()]
                if 'LOWER(' not in check_prefix.upper():
                    modified_queries.append(f"Applied LOWER() to {var_name}.{prop_name} CONTAINS comparison")
                    # CONTAINSの場合は検索文字列も小文字化
                    return f"LOWER({var_name}.{prop_name}) CONTAINS '{value.lower()}'"
            
            return match.group(0)
        
        query = re.sub(pattern_contains, replace_contains, query, flags=re.IGNORECASE)
        
        return query, modified_queries

# テスト実行方法:python3 cypher_post_processor.py
# def test_post_processor():
#     """簡易テスト関数"""
#     processor = CypherPostProcessor()
    
#     test_queries = [
#         # Test 1: knownName comparison
#         "MATCH (s:Scholar) WHERE s.knownName = 'Einstein' RETURN s.knownName",
        
#         # Test 2: Institution name with CONTAINS
#         "MATCH (i:Institution) WHERE i.name CONTAINS 'Harvard' RETURN i.name",
        
#         # Test 3: Multiple properties
#         "MATCH (s:Scholar)-[:WON]->(p:Prize) WHERE s.knownName = 'Curie' AND p.category = 'Physics' RETURN s.knownName, p.category",        
#     ]
    
#     print("=" * 80)
#     print("POST-PROCESSOR TEST RESULTS")
#     print("=" * 80)
    
#     for i, query in enumerate(test_queries, 1):
#         print(f"\n--- Test {i} ---")
#         print(f"Original: {query}")
#         processed = processor.post_process(query)
#         print(f"Processed: {processed}")

#     print("\n" + "=" * 80)


# if __name__ == "__main__":
#     test_post_processor()


from typing import Tuple, List

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
        query, rule_applied = self._enforce_lowercase_comparison(query)
        # Todo: ルール追加
    
    

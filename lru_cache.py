# 仕様
#1. 同じ質問とスキーマの組み合わせ → 同じハッシュキー → キャッシュヒット
#2. 異なる質問またはスキーマ → 異なるハッシュキー → キャッシュミス
#3. キャッシュが満杯（100エントリ）になると、最も古いエントリを自動削除
import hashlib
import time
from collections import OrderedDict
from typing import Dict, Tuple, Optional, Any, List
import json

class Text2CypherCache:
    def __init__(self, maxsize: int = 100):
        self.maxsize = maxsize
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.total_requests = 0
    
    def _generate_key(self, question: str, schema: str) -> str:
        combined = f"{question}{schema}"
        # consistent hash
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def get(self, question: str, schema: str) -> Optional[Dict[str, Any]]:
        self.total_requests += 1
        key = self._generate_key(question, schema)

        if key in self.cache:
            # Move to end to mark as recently used
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        
        self.misses += 1
        return None
    
    def set(self, question: str, schema: str, query: Any) -> None:
        key = self._generate_key(question, schema)

        if len(self.cache) >= self.maxsize:
            # Remove
            self.cache.popitem(last=False)
        self.cache[key] = {
            'query': query,
            'timestamp': time.time()
        }
    
    def clear(self) -> None:
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        self.total_requests = 0
    
    def get_stats(self) -> Dict[str, Any]:
        hit_rate = self.hits / self.total_requests if self.total_requests > 0 else 0
        return {
            'size': len(self.cache),
            'maxsize': self.maxsize,
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': self.total_requests,
            'hit_rate': hit_rate,
            'miss_rate': 1 - hit_rate
        }
    
    def get_cached_entries(self) -> List[Dict[str, Any]]:
        entries = []
        for key, value in self.cache.items():
            entries.append({
                'key': key[:16] + '...',
                'timestamp': value['timestamp'],
                'age_seconds': time.time() - value['timestamp']
            })
"""
API基类 - 统一接口规范
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import json
import os
from datetime import datetime


class BaseAPI(ABC):
    """API基类，提供通用功能"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or '/tmp/bobquant_cache'
        os.makedirs(self.cache_dir, exist_ok=True)
        self._cache = {}
    
    def _get_cache_key(self, *args) -> str:
        """生成缓存键"""
        return '_'.join(str(a) for a in args)
    
    def _get_from_cache(self, key: str, max_age: int = 5) -> Optional[Any]:
        """从缓存获取数据（默认5秒）"""
        if key not in self._cache:
            return None
        
        data, timestamp = self._cache[key]
        if (datetime.now() - timestamp).seconds > max_age:
            del self._cache[key]
            return None
        
        return data
    
    def _set_cache(self, key: str, data: Any):
        """设置缓存"""
        self._cache[key] = (data, datetime.now())
    
    def _clear_cache(self):
        """清空缓存"""
        self._cache.clear()
    
    def _load_json(self, filepath: str) -> Optional[Dict]:
        """安全加载JSON文件"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[Error] 加载JSON失败 {filepath}: {e}")
        return None
    
    def _save_json(self, filepath: str, data: Dict):
        """安全保存JSON文件"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[Error] 保存JSON失败 {filepath}: {e}")
            return False
    
    @abstractmethod
    def get(self, **kwargs) -> Optional[Dict]:
        """获取数据 - 子类必须实现"""
        pass

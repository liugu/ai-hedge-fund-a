"""
增强版数据缓存模块
支持内存缓存和Redis缓存
"""

import os
import time
import json
import logging
import threading
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0


class CacheBackend(ABC):
    """缓存后端抽象基类"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        pass


class MemoryCache(CacheBackend):
    """内存缓存后端"""

    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        """
        初始化内存缓存

        参数:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self._cache: Dict[str, Dict] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None

            entry = self._cache[key]
            if entry['expires_at'] and time.time() > entry['expires_at']:
                del self._cache[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                return None

            self._stats.hits += 1
            return entry['value']

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        with self._lock:
            # 检查是否需要淘汰
            if len(self._cache) >= self._max_size:
                self._evict()

            expires_at = time.time() + (ttl or self._default_ttl)
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': time.time()
            }
            self._stats.sets += 1

    def delete(self, key: str) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.deletes += 1

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def exists(self, key: str) -> bool:
        with self._lock:
            if key not in self._cache:
                return False
            entry = self._cache[key]
            if entry['expires_at'] and time.time() > entry['expires_at']:
                del self._cache[key]
                return False
            return True

    def _evict(self) -> None:
        """淘汰过期或最旧的条目"""
        now = time.time()

        # 先删除过期的
        expired = [k for k, v in self._cache.items() if v['expires_at'] and v['expires_at'] < now]
        for k in expired:
            del self._cache[k]
            self._stats.evictions += 1

        # 如果还是满的，删除最旧的
        if len(self._cache) >= self._max_size:
            oldest = min(self._cache.items(), key=lambda x: x[1]['created_at'])
            del self._cache[oldest[0]]
            self._stats.evictions += 1

    @property
    def stats(self) -> CacheStats:
        return self._stats

    @property
    def size(self) -> int:
        return len(self._cache)


class RedisCache(CacheBackend):
    """Redis缓存后端"""

    def __init__(self, host: str = 'localhost', port: int = 6379,
                 db: int = 0, password: str = None, default_ttl: int = 3600):
        """
        初始化Redis缓存

        参数:
            host: Redis主机
            port: Redis端口
            db: 数据库编号
            password: 密码
            default_ttl: 默认过期时间（秒）
        """
        self._redis = None
        self._default_ttl = default_ttl
        self._stats = CacheStats()

        try:
            import redis
            self._redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )
            # 测试连接
            self._redis.ping()
            logger.info(f"Redis缓存连接成功: {host}:{port}")
        except ImportError:
            logger.warning("Redis未安装，请运行: pip install redis")
        except Exception as e:
            logger.warning(f"Redis连接失败: {e}")

    @property
    def is_available(self) -> bool:
        return self._redis is not None

    def get(self, key: str) -> Optional[Any]:
        if not self.is_available:
            self._stats.misses += 1
            return None

        try:
            value = self._redis.get(key)
            if value is None:
                self._stats.misses += 1
                return None

            self._stats.hits += 1
            return json.loads(value)
        except Exception as e:
            logger.error(f"Redis获取失败: {e}")
            self._stats.misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        if not self.is_available:
            return

        try:
            serialized = json.dumps(value, ensure_ascii=False)
            self._redis.setex(key, ttl or self._default_ttl, serialized)
            self._stats.sets += 1
        except Exception as e:
            logger.error(f"Redis设置失败: {e}")

    def delete(self, key: str) -> None:
        if not self.is_available:
            return

        try:
            self._redis.delete(key)
            self._stats.deletes += 1
        except Exception as e:
            logger.error(f"Redis删除失败: {e}")

    def clear(self) -> None:
        if not self.is_available:
            return

        try:
            self._redis.flushdb()
        except Exception as e:
            logger.error(f"Redis清空失败: {e}")

    def exists(self, key: str) -> bool:
        if not self.is_available:
            return False

        try:
            return self._redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis检查失败: {e}")
            return False

    @property
    def stats(self) -> CacheStats:
        return self._stats


class DataCache:
    """
    数据缓存管理器
    支持多级缓存（L1内存 + L2 Redis）
    """

    def __init__(self, use_redis: bool = False, default_ttl: int = 3600):
        """
        初始化数据缓存

        参数:
            use_redis: 是否使用Redis
            default_ttl: 默认过期时间（秒）
        """
        self._l1 = MemoryCache(default_ttl=default_ttl)
        self._l2 = None

        if use_redis:
            redis_host = os.environ.get('REDIS_HOST', 'localhost')
            redis_port = int(os.environ.get('REDIS_PORT', 6379))
            redis_password = os.environ.get('REDIS_PASSWORD')
            self._l2 = RedisCache(host=redis_host, port=redis_port, password=redis_password, default_ttl=default_ttl)

        logger.info(f"数据缓存初始化完成 (Redis: {self._l2 is not None and self._l2.is_available})")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        # 先查L1
        value = self._l1.get(key)
        if value is not None:
            return value

        # 再查L2
        if self._l2:
            value = self._l2.get(key)
            if value is not None:
                # 回填L1
                self._l1.set(key, value)
                return value

        return None

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """设置缓存数据"""
        self._l1.set(key, value, ttl)
        if self._l2:
            self._l2.set(key, value, ttl)

    def delete(self, key: str) -> None:
        """删除缓存数据"""
        self._l1.delete(key)
        if self._l2:
            self._l2.delete(key)

    def clear(self) -> None:
        """清空缓存"""
        self._l1.clear()
        if self._l2:
            self._l2.clear()

    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        return self._l1.exists(key) or (self._l2 and self._l2.exists(key))

    def get_or_set(self, key: str, factory: callable, ttl: int = None) -> Any:
        """
        获取或设置缓存

        参数:
            key: 缓存键
            factory: 数据工厂函数
            ttl: 过期时间
        """
        value = self.get(key)
        if value is not None:
            return value

        value = factory()
        if value is not None:
            self.set(key, value, ttl)

        return value

    @property
    def stats(self) -> Dict[str, CacheStats]:
        """获取缓存统计"""
        result = {'l1': self._l1.stats}
        if self._l2:
            result['l2'] = self._l2.stats
        return result

    def print_stats(self) -> None:
        """打印缓存统计"""
        print("\n缓存统计:")
        print(f"  L1 (内存): 命中率 {self._l1.stats.hit_rate:.2%}, 大小 {self._l1.size}")
        if self._l2:
            print(f"  L2 (Redis): 命中率 {self._l2.stats.hit_rate:.2%}")


# 全局缓存实例
_global_cache = None


def get_cache(use_redis: bool = False) -> DataCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = DataCache(use_redis=use_redis)
    return _global_cache


if __name__ == "__main__":
    # 测试缓存
    cache = DataCache(use_redis=False)

    # 设置数据
    cache.set("test_key", {"name": "测试", "value": 123})
    print(f"设置数据: test_key")

    # 获取数据
    data = cache.get("test_key")
    print(f"获取数据: {data}")

    # 使用工厂函数
    data2 = cache.get_or_set("test_key2", lambda: {"generated": True})
    print(f"工厂函数: {data2}")

    # 打印统计
    cache.print_stats()

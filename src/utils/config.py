"""
A股分析系统配置管理
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class AStockConfig:
    """A股分析系统配置"""

    # 数据源配置
    primary_data_source: str = "akshare"  # akshare/tushare/tencent
    tushare_api_key: Optional[str] = None

    # 缓存配置
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 默认缓存1小时
    redis_enabled: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None

    # 分析配置
    default_analysis_days: int = 60
    technical_indicators: Dict[str, Any] = field(default_factory=lambda: {
        "macd": {"fast": 12, "slow": 26, "signal": 9},
        "kdj": {"n": 9, "m1": 3, "m2": 3},
        "rsi": {"periods": [6, 12, 24]},
        "boll": {"period": 20, "std_dev": 2.0},
        "ma": {"periods": [5, 10, 20, 60]}
    })

    # 评分权重
    scoring_weights: Dict[str, float] = field(default_factory=lambda: {
        "technical": 0.30,
        "fundamental": 0.25,
        "fund_flow": 0.25,
        "sentiment": 0.20
    })

    # 信号阈值
    bullish_threshold: int = 65
    bearish_threshold: int = 40

    # API配置
    api_host: str = "0.0.0.0"
    api_port: int = 5001
    api_debug: bool = False

    # 调度器配置
    scheduler_enabled: bool = False
    quote_update_interval: int = 60  # 秒
    northbound_update_interval: int = 300  # 秒
    analysis_interval: int = 3600  # 秒

    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None

    @classmethod
    def from_env(cls) -> 'AStockConfig':
        """从环境变量加载配置"""
        config = cls()

        # 数据源
        config.primary_data_source = os.getenv('A_STOCK_DATA_SOURCE', config.primary_data_source)
        config.tushare_api_key = os.getenv('TUSHARE_API_KEY')

        # 缓存
        config.cache_enabled = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
        config.cache_ttl = int(os.getenv('CACHE_TTL', config.cache_ttl))
        config.redis_enabled = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'
        config.redis_host = os.getenv('REDIS_HOST', config.redis_host)
        config.redis_port = int(os.getenv('REDIS_PORT', config.redis_port))
        config.redis_password = os.getenv('REDIS_PASSWORD')

        # API
        config.api_host = os.getenv('API_HOST', config.api_host)
        config.api_port = int(os.getenv('API_PORT', config.api_port))
        config.api_debug = os.getenv('API_DEBUG', 'false').lower() == 'true'

        # 调度器
        config.scheduler_enabled = os.getenv('SCHEDULER_ENABLED', 'false').lower() == 'true'

        # 日志
        config.log_level = os.getenv('LOG_LEVEL', config.log_level)
        config.log_file = os.getenv('LOG_FILE')

        return config

    @classmethod
    def from_file(cls, filepath: str) -> 'AStockConfig':
        """从配置文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return config

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "primary_data_source": self.primary_data_source,
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
            "redis_enabled": self.redis_enabled,
            "default_analysis_days": self.default_analysis_days,
            "scoring_weights": self.scoring_weights,
            "bullish_threshold": self.bullish_threshold,
            "bearish_threshold": self.bearish_threshold,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "scheduler_enabled": self.scheduler_enabled,
            "log_level": self.log_level,
        }

    def save_to_file(self, filepath: str):
        """保存到配置文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


# 全局配置实例
_config: Optional[AStockConfig] = None


def get_config() -> AStockConfig:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = AStockConfig.from_env()
    return _config


def init_config(config: AStockConfig):
    """初始化配置"""
    global _config
    _config = config

    # 设置日志级别
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=config.log_file
    )

    logger.info(f"配置已初始化: {config.to_dict()}")


if __name__ == "__main__":
    # 测试配置
    config = AStockConfig.from_env()
    print("当前配置:")
    print(json.dumps(config.to_dict(), indent=2, ensure_ascii=False))

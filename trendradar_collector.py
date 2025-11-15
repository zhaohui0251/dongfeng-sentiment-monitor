"""
TrendRadar平台采集器
基于开源项目 https://github.com/sansan0/TrendRadar
"""
import time
import random
from datetime import datetime
from typing import List, Optional

import requests

from .base_collector import BaseCollector, Article
from ..utils.logger import logger


class TrendRadarCollector(BaseCollector):
    """TrendRadar采集器"""
    
    # API基础URL
    API_BASE = "https://api.vvhan.com/api/hotlist"
    
    # 支持的平台映射
    PLATFORMS = {
        'toutiao': '今日头条',
        'baidu': '百度热搜',
        'zhihu': '知乎热榜',
        'weibo': '微博热搜',
        'bilibili': 'B站热榜',
        'douyin': '抖音热点',
        'wallstreetcn-hot': '华尔街见闻',
        'thepaper': '澎湃新闻',
        'cls': '财联社',
        'weread': '微信读书',
        'sspai': '少数派'
    }
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.platforms = [p for p in config if p.get('enabled', True)]
    
    def collect(self, keywords: List[str]) -> List[Article]:
        """
        采集TrendRadar平台热点
        
        Args:
            keywords: 关键词列表（用于后续过滤）
            
        Returns:
            文章列表
        """
        articles = []
        
        for platform_config in self.platforms:
            platform_id = platform_config['id']
            platform_name = platform_config.get('name', self.PLATFORMS.get(platform_id, platform_id))
            
            try:
                logger.info(f"[TrendRadar] 开始采集: {platform_name}")
                platform_articles = self._fetch_platform(platform_id, platform_name)
                articles.extend(platform_articles)
                
                # 随机延迟
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                logger.error(f"[TrendRadar] 采集失败 {platform_name}: {e}")
        
        logger.info(f"[TrendRadar] 共采集 {len(articles)} 条")
        return articles
    
    def _fetch_platform(self, platform_id: str, platform_name: str) -> List[Article]:
        """获取单个平台的热点"""
        articles = []
        
        try:
            # 构造API请求
            url = f"{self.API_BASE}?type={platform_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查响应状态
            if not data.get('success', False):
                logger.warning(f"[TrendRadar] API返回失败: {platform_name}")
                return articles
            
            # 解析数据
            items = data.get('data', [])
            
            for item in items:
                article = self._parse_item(item, platform_name)
                if article:
                    articles.append(article)
            
        except Exception as e:
            logger.error(f"[TrendRadar] 请求失败 {platform_name}: {e}")
        
        return articles
    
    def _parse_item(self, item: dict, platform_name: str) -> Optional[Article]:
        """解析热点项"""
        try:
            title = item.get('title', '').strip()
            url = item.get('url', '')
            
            if not title:
                return None
            
            # 尝试获取热度值
            hot = item.get('hot', item.get('hotValue', ''))
            
            return Article(
                title=title,
                url=url,
                source=platform_name,
                publish_time=datetime.now(),  # TrendRadar热点通常是最新的
                content=hot if hot else None  # 热度值存入content字段
            )
            
        except Exception as e:
            logger.debug(f"[TrendRadar] 解析项失败: {e}")
            return None

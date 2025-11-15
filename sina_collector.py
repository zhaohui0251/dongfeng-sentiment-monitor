"""
新浪搜索采集器
"""
import re
import time
import random
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from .base_collector import BaseCollector, Article
from ..utils.logger import logger


class SinaCollector(BaseCollector):
    """新浪搜索采集器"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://search.sina.com.cn')
        self.max_results = config.get('max_results_per_keyword', 5)
        self.headers = {
            'User-Agent': config.get('user_agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
        }
    
    def collect(self, keywords: List[str]) -> List[Article]:
        """
        采集新浪搜索结果
        
        Args:
            keywords: 关键词列表
            
        Returns:
            文章列表
        """
        articles = []
        
        for keyword in keywords:
            try:
                logger.info(f"[新浪搜索] 开始搜索: {keyword}")
                keyword_articles = self._search_keyword(keyword)
                articles.extend(keyword_articles)
                
                # 随机延迟
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logger.error(f"[新浪搜索] 搜索失败 {keyword}: {e}")
        
        logger.info(f"[新浪搜索] 共采集 {len(articles)} 条")
        return articles
    
    def _search_keyword(self, keyword: str) -> List[Article]:
        """搜索单个关键词"""
        articles = []
        
        # 构造搜索URL
        search_url = f"{self.base_url}/?q={quote(keyword)}&range=all&c=news&sort=time"
        
        try:
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 解析搜索结果
            result_items = soup.find_all('div', class_='box-result')
            
            for item in result_items[:self.max_results]:
                article = self._parse_result_item(item, keyword)
                if article:
                    articles.append(article)
            
        except Exception as e:
            logger.error(f"[新浪搜索] 请求失败: {e}")
        
        return articles
    
    def _parse_result_item(self, item, keyword: str) -> Optional[Article]:
        """解析搜索结果项"""
        try:
            # 提取标题和链接
            title_elem = item.find('h2')
            if not title_elem or not title_elem.find('a'):
                return None
            
            title = title_elem.get_text(strip=True)
            url = title_elem.find('a').get('href', '')
            
            # 提取来源
            source_elem = item.find('span', class_='fgray_time')
            source = source_elem.get_text(strip=True) if source_elem else '新浪新闻'
            
            # 提取时间
            time_elem = item.find('span', class_='fgray_time')
            publish_time = self._parse_time(time_elem.get_text(strip=True) if time_elem else '')
            
            return Article(
                title=title,
                url=url,
                source=source,
                publish_time=publish_time,
                matched_keywords=[keyword]
            )
            
        except Exception as e:
            logger.debug(f"[新浪搜索] 解析结果项失败: {e}")
            return None
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """
        解析时间字符串
        支持格式：
        - X小时前
        - X天前
        - 2024年11月15日
        - 2024-11-15
        """
        now = datetime.now()
        
        # X小时前
        hour_match = re.search(r'(\d+)\s*小时前', time_str)
        if hour_match:
            hours = int(hour_match.group(1))
            return now - timedelta(hours=hours)
        
        # X天前
        day_match = re.search(r'(\d+)\s*天前', time_str)
        if day_match:
            days = int(day_match.group(1))
            return now - timedelta(days=days)
        
        # YYYY年MM月DD日
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', time_str)
        if date_match:
            year, month, day = map(int, date_match.groups())
            return datetime(year, month, day)
        
        # YYYY-MM-DD
        date_match2 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', time_str)
        if date_match2:
            year, month, day = map(int, date_match2.groups())
            return datetime(year, month, day)
        
        return None

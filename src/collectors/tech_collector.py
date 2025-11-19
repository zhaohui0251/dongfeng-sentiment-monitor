"""
科技媒体采集器 (IT之家/36氪)
"""
import time
import random
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from .base_collector import BaseCollector, Article
from ..utils.logger import logger


class TechCollector(BaseCollector):
    """科技媒体采集器"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.media_configs = [m for m in config if m.get('enabled', True)]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def collect(self, keywords: List[str]) -> List[Article]:
        """
        采集科技媒体文章
        
        Args:
            keywords: 关键词列表
            
        Returns:
            文章列表
        """
        articles = []
        
        for media in self.media_configs:
            media_name = media['name']
            
            try:
                logger.info(f"[科技媒体] 开始采集: {media_name}")
                
                if media_name == 'IT之家':
                    media_articles = self._collect_ithome(media)
                elif media_name == '36氪':
                    media_articles = self._collect_36kr(media)
                else:
                    logger.warning(f"[科技媒体] 不支持的媒体: {media_name}")
                    continue
                
                articles.extend(media_articles)
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                logger.error(f"[科技媒体] 采集失败 {media_name}: {e}")
        
        logger.info(f"[科技媒体] 共采集 {len(articles)} 条")
        return articles
    
    def _collect_ithome(self, config: dict) -> List[Article]:
        """采集IT之家"""
        articles = []
        
        try:
            # IT之家RSS订阅
            rss_url = config.get('rss_feed', 'https://www.ithome.com/rss/')
            
            response = requests.get(rss_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')
            
            for item in items[:20]:  # 只取前20条
                try:
                    title = item.find('title').get_text(strip=True)
                    url = item.find('link').get_text(strip=True)
                    pub_date_str = item.find('pubDate').get_text(strip=True)
                    
                    # 解析时间：Mon, 15 Nov 2024 10:30:00 GMT
                    pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %Z')
                    
                    articles.append(Article(
                        title=title,
                        url=url,
                        source='IT之家',
                        publish_time=pub_date
                    ))
                    
                except Exception as e:
                    logger.debug(f"[IT之家] 解析RSS项失败: {e}")
            
        except Exception as e:
            logger.error(f"[IT之家] RSS采集失败: {e}")
        
        return articles
    
    def _collect_36kr(self, config: dict) -> List[Article]:
        """采集36氪"""
        articles = []
        
        try:
            # 36氪快讯API
            api_url = config.get('api_endpoint', 'https://36kr.com/api/newsflash')
            
            response = requests.get(
                api_url,
                headers=self.headers,
                params={'per_page': 20},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            items = data.get('data', {}).get('items', [])
            
            for item in items:
                try:
                    title = item.get('title', '').strip()
                    item_id = item.get('id', '')
                    url = f"https://36kr.com/newsflashes/{item_id}"
                    
                    # 时间戳转datetime
                    published_at = item.get('published_at', 0)
                    pub_date = datetime.fromtimestamp(published_at) if published_at else datetime.now()
                    
                    articles.append(Article(
                        title=title,
                        url=url,
                        source='36氪',
                        publish_time=pub_date
                    ))
                    
                except Exception as e:
                    logger.debug(f"[36氪] 解析API项失败: {e}")
            
        except Exception as e:
            logger.error(f"[36氪] API采集失败: {e}")
        
        return articles

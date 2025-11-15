"""
文章过滤器 - 6层过滤逻辑
"""
import re
from datetime import datetime, timedelta
from typing import List, Dict, Set
from difflib import SequenceMatcher

from ..collectors.base_collector import Article
from ..utils.logger import logger


class ArticleFilter:
    """文章过滤器"""
    
    def __init__(self, config: dict, models_config: dict):
        """
        初始化过滤器
        
        Args:
            config: 过滤配置
            models_config: 车型配置
        """
        self.config = config
        self.models_config = models_config
        
        # 提取配置参数
        self.time_window_hours = config.get('time_window_hours', 48)
        self.min_title_length = config.get('min_title_length', 10)
        self.max_title_length = config.get('max_title_length', 100)
        self.similarity_threshold = config.get('similarity_threshold', 0.8)
        
        # 车型关键词映射
        self.car_keywords = self._build_car_keywords()
        
        # 黑名单
        self.global_blacklist = set(models_config.get('global_blacklist', []))
        self.special_blacklist = self._build_special_blacklist()
        
        # 汽车领域白名单
        self.automotive_keywords = set(models_config.get('automotive_keywords', []))
        
        # 已处理标题集合（去重）
        self.processed_titles: Set[str] = set()
    
    def _build_car_keywords(self) -> Dict[str, List[str]]:
        """构建车型关键词映射"""
        keywords_map = {}
        
        for car in self.models_config.get('car_models', []):
            car_name = car['name']
            keywords = car.get('keywords', []) + car.get('aliases', [])
            keywords_map[car_name] = list(set(keywords))  # 去重
        
        return keywords_map
    
    def _build_special_blacklist(self) -> Dict[str, Set[str]]:
        """构建车型专属黑名单"""
        blacklist_map = {}
        
        for car in self.models_config.get('car_models', []):
            car_name = car['name']
            special = car.get('special_blacklist', [])
            if special:
                blacklist_map[car_name] = set(special)
        
        return blacklist_map
    
    def filter(self, articles: List[Article]) -> List[Article]:
        """
        执行6层过滤
        
        Args:
            articles: 原始文章列表
            
        Returns:
            过滤后的文章列表
        """
        logger.info(f"开始过滤: 原始数量 {len(articles)}")
        
        # 统计信息
        stats = {
            'original': len(articles),
            'after_keyword': 0,
            'after_length': 0,
            'after_time': 0,
            'after_blacklist': 0,
            'after_automotive': 0,
            'after_dedup': 0
        }
        
        # 第1层：车型关键词匹配
        articles = self._filter_by_keywords(articles)
        stats['after_keyword'] = len(articles)
        logger.info(f"第1层(关键词匹配): 剩余 {len(articles)} 条")
        
        # 第2层：标题长度验证
        articles = self._filter_by_length(articles)
        stats['after_length'] = len(articles)
        logger.info(f"第2层(标题长度): 剩余 {len(articles)} 条")
        
        # 第3层：时间窗口过滤
        articles = self._filter_by_time(articles)
        stats['after_time'] = len(articles)
        logger.info(f"第3层(时间窗口): 剩余 {len(articles)} 条")
        
        # 第4层：黑名单过滤
        articles = self._filter_by_blacklist(articles)
        stats['after_blacklist'] = len(articles)
        logger.info(f"第4层(黑名单): 剩余 {len(articles)} 条")
        
        # 第5层：汽车领域关键词验证
        articles = self._filter_by_automotive_keywords(articles)
        stats['after_automotive'] = len(articles)
        logger.info(f"第5层(汽车关键词): 剩余 {len(articles)} 条")
        
        # 第6层：去重
        articles = self._filter_by_dedup(articles)
        stats['after_dedup'] = len(articles)
        logger.info(f"第6层(去重): 剩余 {len(articles)} 条")
        
        logger.info(f"过滤完成: {stats}")
        
        return articles
    
    def _filter_by_keywords(self, articles: List[Article]) -> List[Article]:
        """第1层：车型关键词匹配"""
        filtered = []
        
        for article in articles:
            matched_cars = []
            
            # 检查标题是否包含任何车型关键词
            for car_name, keywords in self.car_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in article.title.lower():
                        matched_cars.append(car_name)
                        article.matched_keywords.append(keyword)
                        break
            
            if matched_cars:
                article.category = ','.join(set(matched_cars))
                filtered.append(article)
        
        return filtered
    
    def _filter_by_length(self, articles: List[Article]) -> List[Article]:
        """第2层：标题长度验证"""
        return [
            a for a in articles
            if self.min_title_length <= len(a.title) <= self.max_title_length
        ]
    
    def _filter_by_time(self, articles: List[Article]) -> List[Article]:
        """第3层：48小时时间窗口"""
        cutoff_time = datetime.now() - timedelta(hours=self.time_window_hours)
        
        filtered = []
        for article in articles:
            if article.publish_time is None:
                # 无法解析时间的，保守处理：保留
                filtered.append(article)
            elif article.publish_time >= cutoff_time:
                filtered.append(article)
        
        return filtered
    
    def _filter_by_blacklist(self, articles: List[Article]) -> List[Article]:
        """第4层：黑名单过滤"""
        filtered = []
        
        for article in articles:
            # 通用黑名单
            if any(word in article.title for word in self.global_blacklist):
                continue
            
            # 车型专属黑名单
            skip = False
            if article.category:
                for car_name in article.category.split(','):
                    special_blacklist = self.special_blacklist.get(car_name, set())
                    if any(word in article.title for word in special_blacklist):
                        skip = True
                        break
            
            if not skip:
                filtered.append(article)
        
        return filtered
    
    def _filter_by_automotive_keywords(self, articles: List[Article]) -> List[Article]:
        """第5层：汽车领域关键词验证"""
        filtered = []
        
        for article in articles:
            # 标题必须包含至少一个汽车相关关键词
            if any(keyword in article.title for keyword in self.automotive_keywords):
                filtered.append(article)
        
        return filtered
    
    def _filter_by_dedup(self, articles: List[Article]) -> List[Article]:
        """第6层：去重"""
        filtered = []
        
        for article in articles:
            # 检查是否已处理过
            if article.title in self.processed_titles:
                continue
            
            # 检查相似度
            is_duplicate = False
            for existing_title in self.processed_titles:
                similarity = SequenceMatcher(None, article.title, existing_title).ratio()
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                self.processed_titles.add(article.title)
                filtered.append(article)
        
        return filtered
    
    def get_own_brand_articles(self, articles: List[Article]) -> List[Article]:
        """
        筛选本品车型文章
        
        Args:
            articles: 文章列表
            
        Returns:
            本品车型文章
        """
        own_brands = {car['name'] for car in self.models_config.get('car_models', []) if car.get('is_own', False)}
        
        return [
            a for a in articles
            if a.category and any(brand in a.category for brand in own_brands)
        ]
    
    def get_competitor_articles(self, articles: List[Article]) -> List[Article]:
        """
        筛选竞品文章
        
        Args:
            articles: 文章列表
            
        Returns:
            竞品文章
        """
        own_brands = {car['name'] for car in self.models_config.get('car_models', []) if car.get('is_own', False)}
        
        return [
            a for a in articles
            if a.category and not any(brand in a.category for brand in own_brands)
        ]

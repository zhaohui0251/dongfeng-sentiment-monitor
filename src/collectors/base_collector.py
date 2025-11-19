"""
基础采集器类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Article:
    """文章数据结构"""
    title: str
    url: str
    source: str
    publish_time: Optional[datetime] = None
    content: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    matched_keywords: List[str] = None
    
    def __post_init__(self):
        if self.matched_keywords is None:
            self.matched_keywords = []
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'title': self.title,
            'url': self.url,
            'source': self.source,
            'publish_time': self.publish_time.isoformat() if self.publish_time else None,
            'content': self.content,
            'author': self.author,
            'category': self.category,
            'matched_keywords': self.matched_keywords
        }


class BaseCollector(ABC):
    """采集器基类"""
    
    def __init__(self, config: dict):
        """
        初始化采集器
        
        Args:
            config: 配置字典
        """
        self.config = config
    
    @abstractmethod
    def collect(self, keywords: List[str]) -> List[Article]:
        """
        采集数据
        
        Args:
            keywords: 关键词列表
            
        Returns:
            文章列表
        """
        pass
    
    def get_name(self) -> str:
        """获取采集器名称"""
        return self.__class__.__name__

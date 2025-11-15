"""
缓存模块 - 用于去重
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .logger import logger


class DedupCache:
    """去重缓存类"""
    
    def __init__(self, db_path: str = "data/dedup.db", expire_days: int = 7):
        """
        初始化缓存
        
        Args:
            db_path: 数据库路径
            expire_days: 缓存过期天数
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.expire_days = expire_days
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS article_cache (
                hash TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"缓存数据库初始化完成: {self.db_path}")
    
    def _generate_hash(self, text: str) -> str:
        """生成文本哈希值"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def exists(self, title: str) -> bool:
        """
        检查标题是否已存在
        
        Args:
            title: 文章标题
            
        Returns:
            是否存在
        """
        hash_value = self._generate_hash(title)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT COUNT(*) FROM article_cache WHERE hash = ?',
            (hash_value,)
        )
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def add(self, title: str, url: Optional[str] = None):
        """
        添加标题到缓存
        
        Args:
            title: 文章标题
            url: 文章链接
        """
        hash_value = self._generate_hash(title)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'INSERT OR REPLACE INTO article_cache (hash, title, url) VALUES (?, ?, ?)',
                (hash_value, title, url)
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"缓存添加失败: {e}")
        finally:
            conn.close()
    
    def clean_expired(self):
        """清理过期缓存"""
        expire_date = datetime.now() - timedelta(days=self.expire_days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'DELETE FROM article_cache WHERE timestamp < ?',
            (expire_date.isoformat(),)
        )
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted > 0:
            logger.info(f"清理过期缓存: {deleted} 条")
    
    def get_stats(self) -> dict:
        """
        获取缓存统计信息
        
        Returns:
            统计字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM article_cache')
        total = cursor.fetchone()[0]
        
        cursor.execute(
            'SELECT COUNT(*) FROM article_cache WHERE timestamp > ?',
            ((datetime.now() - timedelta(days=1)).isoformat(),)
        )
        today = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_cached': total,
            'cached_today': today,
            'expire_days': self.expire_days
        }

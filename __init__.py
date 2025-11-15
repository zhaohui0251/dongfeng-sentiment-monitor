"""
工具模块
"""
from .logger import logger, setup_logger
from .cache import DedupCache

__all__ = ['logger', 'setup_logger', 'DedupCache']

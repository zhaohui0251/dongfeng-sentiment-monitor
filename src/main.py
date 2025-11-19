"""
东风舆情监测日报系统 - 主程序
"""
import os
import sys
import yaml
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors import SinaCollector, TrendRadarCollector, TechCollector
from src.filters.article_filter import ArticleFilter
from src.analyzer.sentiment_analyzer import SentimentAnalyzer
from src.reporter.dingtalk_pusher import DingTalkPusher
from src.utils import logger, DedupCache


def load_config(config_dir: Path) -> dict:
    """加载配置文件"""
    configs = {}
    
    # 加载车型配置
    with open(config_dir / 'models.yaml', 'r', encoding='utf-8') as f:
        configs['models'] = yaml.safe_load(f)
    
    # 加载关键词配置
    with open(config_dir / 'keywords.yaml', 'r', encoding='utf-8') as f:
        configs['keywords'] = yaml.safe_load(f)
    
    # 加载数据源配置
    with open(config_dir / 'sources.yaml', 'r', encoding='utf-8') as f:
        configs['sources'] = yaml.safe_load(f)
    
    return configs


def extract_car_keywords(models_config: dict) -> list:
    """提取所有车型关键词"""
    keywords = []
    
    for car in models_config.get('car_models', []):
        keywords.extend(car.get('keywords', []))
        keywords.extend(car.get('aliases', []))
    
    return list(set(keywords))  # 去重


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='东风舆情监测日报系统')
    parser.add_argument('--config-dir', type=str, default='config', help='配置文件目录')
    parser.add_argument('--mode', type=str, default='full', 
                       choices=['collect', 'analyze', 'push', 'full'],
                       help='运行模式: collect(仅采集) analyze(仅分析) push(仅推送) full(完整流程)')
    args = parser.parse_args()
    
    # 记录开始时间
    start_time = datetime.now()
    logger.info(f"{'='*60}")
    logger.info(f"东风舆情监测日报系统启动")
    logger.info(f"运行模式: {args.mode}")
    logger.info(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*60}")
    
    # 加载配置
    config_dir = Path(__file__).parent.parent / args.config_dir
    logger.info(f"加载配置文件: {config_dir}")
    configs = load_config(config_dir)
    
    # 初始化去重缓存
    cache = DedupCache()
    cache.clean_expired()
    
    # 提取车型关键词
    car_keywords = extract_car_keywords(configs['models'])
    logger.info(f"监测车型关键词: {len(car_keywords)} 个")
    
    # ========== 第一阶段：数据采集 ==========
    all_articles = []
    
    if args.mode in ['collect', 'full']:
        logger.info("\n" + "="*60)
        logger.info("阶段1: 数据采集")
        logger.info("="*60)
        
        # 1. TrendRadar采集器（主力）
        logger.info("\n[1/3] TrendRadar平台采集...")
        trendradar_collector = TrendRadarCollector(
            configs['sources']['trendradar_platforms']
        )
        trendradar_articles = trendradar_collector.collect(car_keywords)
        all_articles.extend(trendradar_articles)
        
        # 2. 新浪搜索采集器（补充）
        logger.info("\n[2/3] 新浪搜索采集...")
        sina_collector = SinaCollector(configs['sources']['sina_search'])
        sina_articles = sina_collector.collect(car_keywords)
        all_articles.extend(sina_articles)
        
        # 3. 科技媒体采集器（边缘补充）
        logger.info("\n[3/3] 科技媒体采集...")
        tech_collector = TechCollector(configs['sources']['tech_media'])
        tech_articles = tech_collector.collect(car_keywords)
        all_articles.extend(tech_articles)
        
        logger.info(f"\n数据采集完成: 共采集 {len(all_articles)} 条原始数据")
    
    # ========== 第二阶段：过滤筛选 ==========
    if args.mode in ['collect', 'analyze', 'full']:
        logger.info("\n" + "="*60)
        logger.info("阶段2: 过滤筛选")
        logger.info("="*60)
        
        # 初始化过滤器
        article_filter = ArticleFilter(
            configs['sources']['filter_config'],
            configs['models']
        )
        
        # 执行6层过滤
        filtered_articles = article_filter.filter(all_articles)
        
        logger.info(f"\n过滤完成: 保留 {len(filtered_articles)} 条有效数据")
        logger.info(f"过滤率: {(1 - len(filtered_articles)/max(len(all_articles), 1))*100:.1f}%")
    
    # ========== 第三阶段：AI分析 ==========
    analyzed_articles = []
    
    if args.mode in ['analyze', 'full']:
        logger.info("\n" + "="*60)
        logger.info("阶段3: AI情感分析")
        logger.info("="*60)
        
        # 初始化情感分析器
        analyzer = SentimentAnalyzer()
        
        # 批量分析
        logger.info("开始AI分析...")
        analyzed_articles = analyzer.analyze_batch(filtered_articles)
        
        # 统计分析结果
        sentiments = {'positive': 0, 'negative': 0, 'neutral': 0}
        own_negatives = 0
        
        for article in analyzed_articles:
            sentiment = article.get('sentiment', 'neutral')
            sentiments[sentiment] += 1
            
            if article.get('is_own_brand_negative', False):
                own_negatives += 1
        
        logger.info(f"\nAI分析完成:")
        logger.info(f"  正面: {sentiments['positive']} 条")
        logger.info(f"  中性: {sentiments['neutral']} 条")
        logger.info(f"  负面: {sentiments['negative']} 条")
        logger.info(f"  本品负面: {own_negatives} 条 {'⚠️' if own_negatives > 0 else '✅'}")
        
        # 更新缓存
        for article in analyzed_articles:
            cache.add(article['title'], article['url'])
    
    # ========== 第四阶段：推送日报 ==========
    if args.mode in ['push', 'full']:
        logger.info("\n" + "="*60)
        logger.info("阶段4: 推送日报")
        logger.info("="*60)
        
        if not analyzed_articles:
            logger.warning("没有可推送的数据")
        else:
            # 初始化钉钉推送器
            pusher = DingTalkPusher()
            
            # 推送日报
            logger.info(f"准备推送 {len(analyzed_articles)} 条舆情信息...")
            success = pusher.push_daily_report(analyzed_articles)
            
            if success:
                logger.info("✅ 日报推送成功")
            else:
                logger.error("❌ 日报推送失败")
    
    # 打印缓存统计
    stats = cache.get_stats()
    logger.info(f"\n缓存统计: 总计 {stats['total_cached']} 条, 今日新增 {stats['cached_today']} 条")
    
    # 记录结束时间
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"系统运行完成")
    logger.info(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"耗时: {duration:.2f} 秒")
    logger.info(f"{'='*60}")


if __name__ == '__main__':
    main()

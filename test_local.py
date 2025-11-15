"""
本地测试脚本 - 用于验证系统各模块功能
"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.utils import logger


def test_config_loading():
    """测试配置文件加载"""
    logger.info("=" * 60)
    logger.info("测试1: 配置文件加载")
    logger.info("=" * 60)
    
    try:
        import yaml
        
        config_dir = Path(__file__).parent / 'config'
        
        # 测试models.yaml
        with open(config_dir / 'models.yaml', 'r', encoding='utf-8') as f:
            models = yaml.safe_load(f)
            car_count = len(models.get('car_models', []))
            logger.info(f"✅ models.yaml 加载成功，包含 {car_count} 款车型")
        
        # 测试keywords.yaml
        with open(config_dir / 'keywords.yaml', 'r', encoding='utf-8') as f:
            keywords = yaml.safe_load(f)
            category_count = len(keywords.get('content_categories', {}))
            logger.info(f"✅ keywords.yaml 加载成功，包含 {category_count} 个内容分类")
        
        # 测试sources.yaml
        with open(config_dir / 'sources.yaml', 'r', encoding='utf-8') as f:
            sources = yaml.safe_load(f)
            platform_count = len(sources.get('trendradar_platforms', []))
            logger.info(f"✅ sources.yaml 加载成功，包含 {platform_count} 个TrendRadar平台")
        
        logger.info("✅ 配置文件测试通过\n")
        return True
        
    except Exception as e:
        logger.error(f"❌ 配置文件测试失败: {e}\n")
        return False


def test_collectors():
    """测试采集器"""
    logger.info("=" * 60)
    logger.info("测试2: 数据采集器")
    logger.info("=" * 60)
    
    try:
        from src.collectors import SinaCollector, TrendRadarCollector, TechCollector
        
        test_keywords = ['艾力绅', 'HR-V']
        
        # 测试TrendRadar采集器（只测试1个平台）
        logger.info("测试 TrendRadarCollector...")
        trendradar_config = [{'id': 'baidu', 'name': '百度热搜', 'enabled': True}]
        trendradar_collector = TrendRadarCollector(trendradar_config)
        articles = trendradar_collector.collect(test_keywords)
        logger.info(f"✅ TrendRadar采集器测试通过，采集 {len(articles)} 条\n")
        
        logger.info("✅ 采集器测试通过\n")
        return True
        
    except Exception as e:
        logger.error(f"❌ 采集器测试失败: {e}\n")
        return False


def test_filters():
    """测试过滤器"""
    logger.info("=" * 60)
    logger.info("测试3: 过滤器")
    logger.info("=" * 60)
    
    try:
        from src.collectors import Article
        from src.filters import ArticleFilter
        from datetime import datetime
        import yaml
        
        # 加载配置
        config_dir = Path(__file__).parent / 'config'
        with open(config_dir / 'models.yaml', 'r', encoding='utf-8') as f:
            models_config = yaml.safe_load(f)
        with open(config_dir / 'sources.yaml', 'r', encoding='utf-8') as f:
            sources_config = yaml.safe_load(f)
        
        # 创建测试文章
        test_articles = [
            Article(
                title="艾力绅新款上市，配置升级动力更强",
                url="http://test.com/1",
                source="测试来源",
                publish_time=datetime.now()
            ),
            Article(
                title="这是一个不相关的新闻标题",
                url="http://test.com/2",
                source="测试来源",
                publish_time=datetime.now()
            )
        ]
        
        # 测试过滤
        filter_config = sources_config['filter_config']
        article_filter = ArticleFilter(filter_config, models_config)
        filtered = article_filter.filter(test_articles)
        
        logger.info(f"✅ 过滤器测试通过，原始 {len(test_articles)} 条 → 过滤后 {len(filtered)} 条\n")
        return True
        
    except Exception as e:
        logger.error(f"❌ 过滤器测试失败: {e}\n")
        return False


def test_analyzer():
    """测试情感分析器"""
    logger.info("=" * 60)
    logger.info("测试4: AI情感分析器")
    logger.info("=" * 60)
    
    try:
        from src.analyzer import SentimentAnalyzer
        from src.collectors import Article
        from datetime import datetime
        
        # 初始化分析器（不提供API Key，使用规则模式）
        analyzer = SentimentAnalyzer(api_key=None)
        
        # 创建测试文章
        test_article = Article(
            title="艾力绅召回通知：发动机存在安全隐患",
            url="http://test.com/negative",
            source="测试来源",
            publish_time=datetime.now(),
            category="艾力绅"
        )
        
        # 分析
        result = analyzer.analyze_single(test_article)
        
        logger.info(f"分析结果:")
        logger.info(f"  情感: {result.get('sentiment')}")
        logger.info(f"  分类: {result.get('category')}")
        logger.info(f"  本品负面: {result.get('is_own_brand_negative')}")
        logger.info(f"✅ 情感分析器测试通过\n")
        return True
        
    except Exception as e:
        logger.error(f"❌ 情感分析器测试失败: {e}\n")
        return False


def test_env_variables():
    """测试环境变量"""
    logger.info("=" * 60)
    logger.info("测试5: 环境变量配置")
    logger.info("=" * 60)
    
    dashscope_key = os.getenv('DASHSCOPE_API_KEY')
    dingtalk_webhook = os.getenv('DINGTALK_WEBHOOK_URL')
    
    if dashscope_key:
        logger.info(f"✅ DASHSCOPE_API_KEY 已设置 (长度: {len(dashscope_key)})")
    else:
        logger.warning("⚠️ DASHSCOPE_API_KEY 未设置，将使用规则模式分析")
    
    if dingtalk_webhook:
        logger.info(f"✅ DINGTALK_WEBHOOK_URL 已设置")
    else:
        logger.warning("⚠️ DINGTALK_WEBHOOK_URL 未设置，无法推送日报")
    
    logger.info("")
    return True


def main():
    """运行所有测试"""
    logger.info("\n" + "🚗 东风舆情监测系统 - 本地测试".center(60, "="))
    logger.info("\n")
    
    results = {
        '配置文件': test_config_loading(),
        '数据采集': test_collectors(),
        '过滤器': test_filters(),
        'AI分析': test_analyzer(),
        '环境变量': test_env_variables()
    }
    
    logger.info("=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n🎉 所有测试通过！系统已就绪。")
    else:
        logger.info("\n⚠️ 部分测试失败，请检查配置。")
    
    logger.info("=" * 60 + "\n")


if __name__ == '__main__':
    main()

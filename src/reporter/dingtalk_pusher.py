"""
钉钉推送模块
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from collections import Counter

import requests

from ..utils.logger import logger


class DingTalkPusher:
    """钉钉推送器"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        初始化推送器
        
        Args:
            webhook_url: 钉钉Webhook地址
        """
        self.webhook_url = webhook_url or os.getenv('DINGTALK_WEBHOOK_URL')
        
        if not self.webhook_url:
            logger.warning("未设置钉钉Webhook URL")
    
    def push_daily_report(self, analyzed_articles: List[Dict]) -> bool:
        """
        推送每日舆情日报
        
        Args:
            analyzed_articles: 分析后的文章列表
            
        Returns:
            是否推送成功
        """
        if not self.webhook_url:
            logger.error("钉钉Webhook URL未设置，无法推送")
            return False
        
        # 生成报告内容
        markdown = self._generate_report_markdown(analyzed_articles)
        
        # 构造钉钉消息
        message = {
            "msgtype": "markdown",
            "markdown": {
                "title": "🚗 东风舆情监测日报",
                "text": markdown
            }
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info("钉钉推送成功")
                return True
            else:
                logger.error(f"钉钉推送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"钉钉推送异常: {e}")
            return False
    
    def _generate_report_markdown(self, articles: List[Dict]) -> str:
        """生成报告Markdown内容"""
        # 报告头部
        now = datetime.now()
        markdown = f"""# 🚗 东风舆情监测日报

**监测时间**: {now.strftime('%Y年%m月%d日 %H:%M')}  
**监测车型**: 艾力绅、HR-V、Inspire 及竞品  
**今日动态**: 共发现 {len(articles)} 条相关信息

---

"""
        
        # 分类统计
        stats = self._calculate_stats(articles)
        markdown += self._format_stats_section(stats)
        
        # 舆情热词 TOP5
        keywords = self._extract_top_keywords(articles, top_n=5)
        markdown += self._format_keywords_section(keywords)
        
        # 本品负面预警
        own_negatives = [a for a in articles if a.get('is_own_brand_negative', False)]
        if own_negatives:
            markdown += self._format_negative_section(own_negatives)
        
        # 竞品动态
        competitor_articles = [a for a in articles if not a.get('is_own_brand_negative', False)]
        markdown += self._format_competitor_section(competitor_articles)
        
        # 报告尾部
        markdown += f"""
---

*📊 数据来源: TrendRadar(11平台) + 新浪搜索 + IT之家/36氪*  
*🤖 分析引擎: 通义千问 AI*  
*⚠️ 以上内容由系统自动采集分析，仅供参考*
"""
        
        return markdown
    
    def _calculate_stats(self, articles: List[Dict]) -> Dict:
        """计算统计信息"""
        stats = {
            'total': len(articles),
            'positive': 0,
            'negative': 0,
            'neutral': 0,
            'own_negative': 0,
            'by_category': Counter(),
            'by_source': Counter()
        }
        
        for article in articles:
            sentiment = article.get('sentiment', 'neutral')
            stats[sentiment] += 1
            
            if article.get('is_own_brand_negative', False):
                stats['own_negative'] += 1
            
            category = article.get('category', '其他')
            stats['by_category'][category] += 1
            
            source = article.get('source', '未知来源')
            stats['by_source'][source] += 1
        
        return stats
    
    def _format_stats_section(self, stats: Dict) -> str:
        """格式化统计信息"""
        markdown = f"""## 📊 舆情概览

- **总计**: {stats['total']} 条
- **情感分布**: 正面 {stats['positive']} | 中性 {stats['neutral']} | 负面 {stats['negative']}
- **本品负面**: {stats['own_negative']} 条 {'⚠️' if stats['own_negative'] > 0 else '✅'}

**内容分类**:  
"""
        
        for category, count in stats['by_category'].most_common(5):
            markdown += f"- {category}: {count}条\n"
        
        markdown += "\n---\n\n"
        
        return markdown
    
    def _extract_top_keywords(self, articles: List[Dict], top_n: int = 5) -> List[tuple]:
        """提取TOP N关键词"""
        all_keywords = []
        
        for article in articles:
            keywords = article.get('keywords', [])
            all_keywords.extend(keywords)
        
        keyword_counter = Counter(all_keywords)
        return keyword_counter.most_common(top_n)
    
    def _format_keywords_section(self, keywords: List[tuple]) -> str:
        """格式化关键词部分"""
        if not keywords:
            return ""
        
        markdown = "## 🔥 舆情热词 TOP 5\n\n"
        
        for i, (keyword, count) in enumerate(keywords, 1):
            markdown += f"{i}. **{keyword}** ({count}次)\n"
        
        markdown += "\n---\n\n"
        
        return markdown
    
    def _format_negative_section(self, articles: List[Dict]) -> str:
        """格式化本品负面预警"""
        if not articles:
            return ""
        
        markdown = "## ⚠️ 本品负面预警\n\n"
        
        for i, article in enumerate(articles[:5], 1):  # 最多显示5条
            title = article.get('title', '无标题')
            url = article.get('url', '#')
            source = article.get('source', '未知来源')
            summary = article.get('summary', title[:50])
            
            markdown += f"""**{i}. {title}**

> {summary}

来源: {source} | [查看详情]({url})

"""
        
        markdown += "---\n\n"
        
        return markdown
    
    def _format_competitor_section(self, articles: List[Dict]) -> str:
        """格式化竞品动态"""
        if not articles:
            return ""
        
        markdown = "## 📰 竞品动态精选\n\n"
        
        # 按分类分组
        by_category = {}
        for article in articles:
            category = article.get('category', '其他')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(article)
        
        # 优先展示重要分类
        priority_categories = ['上市', '试驾', '评测', '对比', '口碑', '其他']
        
        shown_count = 0
        max_show = 20  # 最多显示20条
        
        for category in priority_categories:
            if category not in by_category:
                continue
            
            articles_in_category = by_category[category]
            
            markdown += f"### {category}\n\n"
            
            for article in articles_in_category[:5]:  # 每个分类最多5条
                if shown_count >= max_show:
                    break
                
                title = article.get('title', '无标题')
                url = article.get('url', '#')
                source = article.get('source', '未知来源')
                summary = article.get('summary', title[:50])
                sentiment = article.get('sentiment', 'neutral')
                
                # 情感标识
                sentiment_icon = {
                    'positive': '👍',
                    'negative': '👎',
                    'neutral': '➡️'
                }.get(sentiment, '➡️')
                
                markdown += f"""**{sentiment_icon} {title}**

> {summary}

来源: {source} | [查看详情]({url})

"""
                shown_count += 1
            
            if shown_count >= max_show:
                break
        
        return markdown

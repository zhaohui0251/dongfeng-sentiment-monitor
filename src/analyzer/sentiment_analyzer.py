"""
情感分析器 - 通义千问API
"""
import os
import json
from typing import Dict, List, Optional

from ..collectors.base_collector import Article
from ..utils.logger import logger

try:
    import dashscope
    from dashscope import Generation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    logger.warning("dashscope库未安装，情感分析功能将被禁用")


class SentimentAnalyzer:
    """情感分析器"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "qwen-turbo"):
        """
        初始化分析器
        
        Args:
            api_key: 通义千问API Key
            model: 模型名称
        """
        self.api_key = api_key or os.getenv('DASHSCOPE_API_KEY')
        self.model = model
        
        if not self.api_key:
            logger.warning("未设置通义千问API Key，情感分析将使用规则模式")
            self.use_ai = False
        elif not DASHSCOPE_AVAILABLE:
            logger.warning("dashscope库未安装，情感分析将使用规则模式")
            self.use_ai = False
        else:
            dashscope.api_key = self.api_key
            self.use_ai = True
            logger.info(f"通义千问API已初始化: {model}")
    
    def analyze_batch(self, articles: List[Article]) -> List[Dict]:
        """
        批量分析文章情感
        
        Args:
            articles: 文章列表
            
        Returns:
            分析结果列表
        """
        results = []
        
        for article in articles:
            result = self.analyze_single(article)
            results.append(result)
        
        return results
    
    def analyze_single(self, article: Article) -> Dict:
        """
        分析单篇文章
        
        Args:
            article: 文章对象
            
        Returns:
            分析结果字典
        """
        if self.use_ai:
            return self._analyze_with_ai(article)
        else:
            return self._analyze_with_rules(article)
    
    def _analyze_with_ai(self, article: Article) -> Dict:
        """使用AI进行情感分析"""
        try:
            # 构造prompt
            prompt = self._build_prompt(article)
            
            # 调用通义千问API
            response = Generation.call(
                model=self.model,
                prompt=prompt,
                result_format='message'
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                result = self._parse_ai_response(content, article)
                return result
            else:
                logger.error(f"通义千问API调用失败: {response.code} - {response.message}")
                return self._analyze_with_rules(article)
            
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            return self._analyze_with_rules(article)
    
    def _build_prompt(self, article: Article) -> str:
        """构造分析提示词"""
        prompt = f"""你是一个汽车行业舆情分析专家。请分析以下汽车新闻的情感倾向和关键信息。

新闻标题：{article.title}
新闻来源：{article.source}
相关车型：{article.category}

请按照以下JSON格式输出分析结果：
{{
    "sentiment": "positive/negative/neutral",
    "sentiment_score": 0.0-1.0之间的分数,
    "summary": "50字以内的摘要，专业、理性、轻度乐观的语气",
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "category": "试驾/上市/评测/口碑/对比/负面之一",
    "is_own_brand_negative": true或false (是否为东风本田负面新闻)
}}

注意：
1. 东风本田旗下车型包括：艾力绅、HR-V、Inspire
2. 负面新闻包括：召回、投诉、质量问题、故障等
3. 摘要需简洁专业，不超过50字
4. 关键词提取3-5个最重要的词

只输出JSON，不要其他内容："""
        
        return prompt
    
    def _parse_ai_response(self, content: str, article: Article) -> Dict:
        """解析AI响应"""
        try:
            # 尝试解析JSON
            result = json.loads(content)
            
            # 补充原始信息
            result.update({
                'title': article.title,
                'url': article.url,
                'source': article.source,
                'publish_time': article.publish_time.isoformat() if article.publish_time else None,
                'matched_keywords': article.matched_keywords
            })
            
            return result
            
        except json.JSONDecodeError:
            logger.warning(f"AI响应解析失败，使用规则模式: {content[:100]}")
            return self._analyze_with_rules(article)
    
    def _analyze_with_rules(self, article: Article) -> Dict:
        """使用规则进行情感分析（备用方案）"""
        title = article.title.lower()
        
        # 正面关键词
        positive_keywords = ['好评', '优秀', '出色', '领先', '推荐', '值得', '超越', '更好', '满意', '喜欢']
        
        # 负面关键词
        negative_keywords = ['召回', '投诉', '质量问题', '缺陷', '故障', '异响', '漏油', '维权', '问题', '隐患']
        
        # 计算情感得分
        positive_count = sum(1 for kw in positive_keywords if kw in title)
        negative_count = sum(1 for kw in negative_keywords if kw in title)
        
        if negative_count > positive_count:
            sentiment = 'negative'
            score = 0.3
        elif positive_count > negative_count:
            sentiment = 'positive'
            score = 0.8
        else:
            sentiment = 'neutral'
            score = 0.5
        
        # 判断是否为本品负面
        own_brands = ['艾力绅', 'HR-V', 'Inspire', '英诗派', '缤智']
        is_own_negative = (
            sentiment == 'negative' and
            any(brand in article.category for brand in own_brands if article.category)
        )
        
        # 生成简单摘要（取标题前50字）
        summary = article.title[:50] + ('...' if len(article.title) > 50 else '')
        
        # 提取关键词（从matched_keywords）
        keywords = article.matched_keywords[:5] if article.matched_keywords else []
        
        # 分类
        category = self._classify_content(title)
        
        return {
            'title': article.title,
            'url': article.url,
            'source': article.source,
            'publish_time': article.publish_time.isoformat() if article.publish_time else None,
            'sentiment': sentiment,
            'sentiment_score': score,
            'summary': summary,
            'keywords': keywords,
            'category': category,
            'is_own_brand_negative': is_own_negative,
            'matched_keywords': article.matched_keywords
        }
    
    def _classify_content(self, title: str) -> str:
        """内容分类"""
        if any(kw in title for kw in ['试驾', '体验', '长测']):
            return '试驾'
        elif any(kw in title for kw in ['上市', '发布', '亮相']):
            return '上市'
        elif any(kw in title for kw in ['评测', '测评', '横评']):
            return '评测'
        elif any(kw in title for kw in ['口碑', '车主', '用户']):
            return '口碑'
        elif any(kw in title for kw in ['对比', 'PK', 'VS', 'vs']):
            return '对比'
        elif any(kw in title for kw in ['召回', '投诉', '质量问题', '故障']):
            return '负面'
        else:
            return '其他'

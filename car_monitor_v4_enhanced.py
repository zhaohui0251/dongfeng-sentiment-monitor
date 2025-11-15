#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东风本田竞品舆情监测系统 - V4增强版
核心原则：宁缺毋滥，质量优先
部署环境：Mac本地 + 居民宽带IP
执行频率：每周一、三、五早9点

V4新增功能：
1. 智能摘要生成（基于jieba + 规则）
2. 执行概要日志（过滤漏斗可视化）
3. 丢弃样本记录（质量优化依据）
4. 配置文件外置（YAML管理）
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from datetime import datetime, timedelta
import time
import json
from difflib import SequenceMatcher
import re
import os
import yaml
import jieba
import jieba.analyse
from collections import Counter

# ==================== 配置加载 ====================
def load_config():
    """加载配置文件"""
    config_path = os.path.expanduser('~/Desktop/东风本田舆情监测/config.yaml')
    
    # 如果配置文件不存在，使用默认配置
    if not os.path.exists(config_path):
        print(f"⚠️  配置文件不存在: {config_path}")
        print(f"📝 将使用代码内置默认配置")
        return get_default_config()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            print(f"✅ 配置文件加载成功: {config_path}")
            return config
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        print(f"📝 将使用代码内置默认配置")
        return get_default_config()

def get_default_config():
    """获取默认配置"""
    return {
        'dingtalk_webhook': 'https://oapi.dingtalk.com/robot/send?access_token=e3eac2cf9076f5aa21516a48576fa7d27a928f5979ff5905f19224cfd0503596',
        
        'car_models': {
            'Inspire': ['英诗派'],
            '雅阁': ['雅阁'],
            '凯美瑞': ['凯美瑞'],
            '天籁': ['天籁'],
            '艾力绅': ['艾力绅'],
            '奥德赛': ['奥德赛'],
            '赛那': ['赛那'],
            'GL8': ['GL8', '别克GL8'],
            'HR-V': ['HRV', '缤智'],
            '锋兰达': ['锋兰达'],
            '逍客': ['逍客'],
            '探歌': ['探歌']
        },
        
        'blacklist': {
            'general': [
                '二手车', '二手', '转让', '出售', '求购', '置换',
                '4S店', '经销商', '降价', '优惠', '促销', '团购',
                '贷款', '金融', '保险', '维修', '保养',
                '改装', '配件', '用品', '车展', '图片', '视频', '直播'
            ],
            'sources': [
                '二手车', '参谋', '车商', '车易', '瓜子', '优信',
                '懂车帝', '易车', '汽车之家', '汽车江湖', '太平洋汽车'
            ],
            'special': {
                'Inspire': ['相机', '耳机', '显卡', '音响', '设计奖', '产品', '设备'],
                'HR-V': ['芯片', 'RISC', '模型', '智能体', '算法', '代码', 'AI', 'ESG'],
                '探歌': ['歌手', '探望', '演员', '明星', '音乐', '歌曲', '演唱'],
                '逍客': ['逍遥', '客串', '演员', '角色', '电视剧'],
                '奥德赛': ['马里奥', '游戏', '任天堂', '玩家', '主机'],
                '凯美瑞': ['凯美瑞德', '软件', '股票', '股权', '收购', '公司'],
                '天籁': ['画家', '水墨', '丹青', '书法', '艺术', '天籁之音']
            }
        },
        
        'automotive_keywords': [
            '汽车', '轿车', 'SUV', 'MPV', '新车', '车型',
            '本田', '丰田', '日产', '别克', '大众', '广汽', '东风',
            '发动机', '变速箱', '底盘', '悬架', '座椅',
            '试驾', '评测', '销量', '车主', '购车',
            '混动', '电动', '续航', '油耗', '空间'
        ],
        
        'system': {
            'days_range': 14,
            'max_news_per_model': 3,
            'log_dir': '~/Desktop/东风本田舆情监测/日志',
            'enable_summary': True,
            'enable_execution_log': True,
            'enable_filtered_log': True
        }
    }

# 加载配置
CONFIG = load_config()

# 提取配置项
DINGTALK_WEBHOOK = CONFIG['dingtalk_webhook']
CAR_MODELS = CONFIG['car_models']
BLACKLIST = CONFIG['blacklist']['general']
SOURCE_BLACKLIST = CONFIG['blacklist']['sources']
SPECIAL_BLACKLIST = CONFIG['blacklist']['special']
AUTOMOTIVE_KEYWORDS = CONFIG['automotive_keywords']
DAYS_RANGE = CONFIG['system']['days_range']
MAX_NEWS_PER_MODEL = CONFIG['system']['max_news_per_model']
LOG_DIR = os.path.expanduser(CONFIG['system']['log_dir'])

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
}

# ==================== 智能摘要生成模块 ====================
class IntelligentSummarizer:
    """智能摘要生成器（基于jieba分词 + 规则）"""
    
    def __init__(self):
        # 情感词典
        self.positive_words = [
            '强劲', '优秀', '出色', '领先', '卓越', '完美', '优异',
            '高效', '智能', '舒适', '豪华', '实用', '创新', '突破',
            '畅销', '热销', '抢手', '口碑', '好评', '推荐', '值得'
        ]
        
        self.negative_words = [
            '召回', '投诉', '缺陷', '问题', '故障', '失望', '落后',
            '不足', '缺点', '遗憾', '质量', '下滑', '销量下降', '滞销'
        ]
        
        # 观点类型关键词
        self.opinion_keywords = {
            'advantage': ['优势', '优点', '强项', '亮点', '特色', '领先'],
            'disadvantage': ['劣势', '缺点', '不足', '短板', '问题'],
            'comparison': ['对比', '比较', 'VS', 'vs', '竞争', '对手'],
            'innovation': ['创新', '首发', '全新', '升级', '改款', '换代'],
            'market_impact': ['销量', '市场', '份额', '排名', '上市', '发布']
        }
    
    def _extract_key_sentences(self, content, max_sentences=3):
        """提取关键句子"""
        if not content:
            return []
        
        # 分句
        sentences = re.split('[。！？\n]', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if not sentences:
            return []
        
        # 给每个句子打分
        scored_sentences = []
        for sentence in sentences:
            score = 0
            
            # 包含汽车关键词加分
            for kw in AUTOMOTIVE_KEYWORDS:
                if kw in sentence:
                    score += 2
            
            # 包含情感词加分
            for word in self.positive_words + self.negative_words:
                if word in sentence:
                    score += 3
            
            # 句子长度适中加分
            if 15 <= len(sentence) <= 50:
                score += 1
            
            scored_sentences.append((sentence, score))
        
        # 排序并取前N句
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored_sentences[:max_sentences]]
    
    def _extract_keywords(self, content, topK=5):
        """提取关键词"""
        if not content:
            return []
        
        try:
            keywords = jieba.analyse.extract_tags(content, topK=topK, withWeight=False)
            return keywords
        except:
            return []
    
    def _analyze_sentiment(self, content, keywords):
        """情感分析"""
        if not content:
            return 'neutral'
        
        positive_count = sum(1 for word in self.positive_words if word in content)
        negative_count = sum(1 for word in self.negative_words if word in content)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _analyze_opinion_type(self, content, keywords):
        """观点类型分析"""
        scores = {}
        
        for opinion_type, type_keywords in self.opinion_keywords.items():
            score = sum(1 for kw in type_keywords if kw in content)
            scores[opinion_type] = score
        
        # 返回得分最高的类型
        if max(scores.values()) == 0:
            return 'general'
        
        return max(scores, key=scores.get)
    
    def generate_summary(self, title, content=''):
        """生成摘要"""
        # 如果没有正文，就用标题分析
        full_text = content if content else title
        
        # 提取关键句子
        key_sentences = self._extract_key_sentences(full_text, max_sentences=2)
        summary_text = '；'.join(key_sentences) if key_sentences else title[:50]
        
        # 提取关键词
        keywords = self._extract_keywords(full_text, topK=5)
        
        # 情感分析
        sentiment = self._analyze_sentiment(full_text, keywords)
        
        # 观点类型
        opinion_type = self._analyze_opinion_type(full_text, keywords)
        
        return {
            'summary': summary_text,
            'keywords': keywords,
            'sentiment': sentiment,
            'opinion_type': opinion_type
        }

# 创建全局摘要生成器实例
summarizer = IntelligentSummarizer()

# ==================== 执行日志模块 ====================
class ExecutionLogger:
    """执行概要日志记录器"""
    
    def __init__(self):
        self.stats = {
            'start_time': datetime.now(),
            'end_time': None,
            'total_fetched': 0,
            'filter_funnel': {
                'stage_1_title_match': 0,
                'stage_2_length_check': 0,
                'stage_3_general_blacklist': 0,
                'stage_4_source_blacklist': 0,
                'stage_5_special_blacklist': 0,
                'stage_6_automotive_keywords': 0,
                'stage_7_time_filter': 0,
                'final_pushed': 0
            },
            'filtered_samples': [],
            'model_stats': {}
        }
    
    def record_fetched(self, count):
        """记录抓取总数"""
        self.stats['total_fetched'] += count
    
    def record_filtered(self, stage, title, reason):
        """记录被过滤的样本"""
        self.stats['filtered_samples'].append({
            'stage': stage,
            'title': title,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
    
    def record_model_stat(self, model_name, fetched, final):
        """记录车型统计"""
        self.stats['model_stats'][model_name] = {
            'fetched': fetched,
            'final': final
        }
    
    def finalize(self, final_count):
        """完成统计"""
        self.stats['end_time'] = datetime.now()
        self.stats['filter_funnel']['final_pushed'] = final_count
        
        # 计算过滤率
        if self.stats['total_fetched'] > 0:
            self.stats['filter_rate'] = round(
                (1 - final_count / self.stats['total_fetched']) * 100, 1
            )
        else:
            self.stats['filter_rate'] = 0
    
    def generate_summary_report(self):
        """生成执行概要报告"""
        report = f"\n{'='*60}\n"
        report += f"📊 执行概要报告\n"
        report += f"{'='*60}\n"
        report += f"⏰ 执行时间: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"⏱️  耗时: {(self.stats['end_time'] - self.stats['start_time']).total_seconds():.1f}秒\n"
        report += f"\n📈 过滤漏斗:\n"
        report += f"  原始抓取: {self.stats['total_fetched']}条\n"
        
        # 计算每个阶段的通过数
        funnel = self.stats['filter_funnel']
        report += f"  → 标题匹配筛选: 通过\n"
        report += f"  → 长度验证: 通过\n"
        report += f"  → 通用黑名单: 通过\n"
        report += f"  → 来源黑名单: 通过\n"
        report += f"  → 车型黑名单: 通过\n"
        report += f"  → 汽车关键词验证: 通过\n"
        report += f"  → 时间过滤: 通过\n"
        report += f"  ✅ 最终推送: {funnel['final_pushed']}条\n"
        report += f"\n📊 过滤率: {self.stats['filter_rate']}%\n"
        
        # 车型统计
        report += f"\n🚗 车型统计:\n"
        for model, stats in self.stats['model_stats'].items():
            if stats['final'] > 0:
                report += f"  {model}: {stats['fetched']}条 → {stats['final']}条\n"
        
        report += f"{'='*60}\n"
        return report
    
    def save_filtered_samples(self):
        """保存丢弃样本记录"""
        if not self.stats['filtered_samples']:
            return
        
        log_file = f"{LOG_DIR}/filtered_samples_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats['filtered_samples'], f, ensure_ascii=False, indent=2)
            print(f"✅ 丢弃样本记录已保存: {log_file}")
        except Exception as e:
            print(f"❌ 丢弃样本记录保存失败: {e}")
    
    def generate_filtered_samples_report(self):
        """生成丢弃样本报告（按阶段分组）"""
        if not self.stats['filtered_samples']:
            return "\n📝 无丢弃样本记录\n"
        
        # 按阶段分组
        grouped = {}
        for sample in self.stats['filtered_samples']:
            stage = sample['stage']
            if stage not in grouped:
                grouped[stage] = []
            grouped[stage].append(sample)
        
        report = f"\n{'='*60}\n"
        report += f"📝 丢弃样本记录（前20条）\n"
        report += f"{'='*60}\n"
        
        total_shown = 0
        for stage, samples in sorted(grouped.items()):
            report += f"\n[{stage}] ({len(samples)}条):\n"
            for sample in samples[:5]:  # 每个阶段最多显示5条
                if total_shown >= 20:
                    break
                report += f"  ❌ \"{sample['title'][:40]}...\" - {sample['reason']}\n"
                total_shown += 1
            if total_shown >= 20:
                break
        
        report += f"\n💡 完整记录已保存到日志文件\n"
        report += f"{'='*60}\n"
        return report

# ==================== 时间处理函数 ====================
def extract_date_from_url(url):
    """从URL中提取日期"""
    patterns = [
        r'(\d{4})-(\d{2})-(\d{2})',
        r'(\d{4})(\d{2})(\d{2})',
        r'/(\d{4})/(\d{1,2})/(\d{1,2})/',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                return datetime(year, month, day)
            except:
                continue
    
    return None

def parse_time_string(time_str, url=''):
    """解析时间字符串"""
    if not time_str or not time_str.strip():
        url_date = extract_date_from_url(url)
        if url_date:
            return url_date, True
        return None, False
    
    time_str = time_str.strip()
    now = datetime.now()
    
    # "X小时前" / "X分钟前" / "X天前"
    if '前' in time_str:
        try:
            if '小时前' in time_str:
                hours = int(re.search(r'(\d+)小时前', time_str).group(1))
                return now - timedelta(hours=hours), True
            elif '分钟前' in time_str:
                minutes = int(re.search(r'(\d+)分钟前', time_str).group(1))
                return now - timedelta(minutes=minutes), True
            elif '天前' in time_str:
                days = int(re.search(r'(\d+)天前', time_str).group(1))
                return now - timedelta(days=days), True
        except:
            pass
    
    # "2025年11月08日 19:39:03"
    try:
        pub_time = datetime.strptime(time_str, '%Y年%m月%d日 %H:%M:%S')
        return pub_time, True
    except:
        pass
    
    # "2025年11月08日 19:39"
    try:
        pub_time = datetime.strptime(time_str, '%Y年%m月%d日 %H:%M')
        return pub_time, True
    except:
        pass
    
    # "2025-11-08 19:39:03"
    try:
        pub_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        return pub_time, True
    except:
        pass
    
    # "2025-11-08"
    try:
        pub_time = datetime.strptime(time_str, '%Y-%m-%d')
        return pub_time, True
    except:
        pass
    
    # "11月08日"
    try:
        pub_time = datetime.strptime(f"{now.year}年{time_str}", '%Y年%m月%d日')
        if pub_time > now:
            pub_time = pub_time.replace(year=now.year - 1)
        return pub_time, True
    except:
        pass
    
    url_date = extract_date_from_url(url)
    if url_date:
        return url_date, True
    
    return None, False

def is_within_days(time_str, url, days):
    """判断时间是否在指定天数内"""
    pub_time, is_certain = parse_time_string(time_str, url)
    
    if not pub_time:
        return False
    
    cutoff_time = datetime.now() - timedelta(days=days)
    
    if pub_time < cutoff_time:
        return False
    
    return True

# ==================== V3超严格验证函数（增强日志版）====================
def is_title_contains_keyword(title, keyword, car_model):
    """V3规则：标题必须包含搜索关键词"""
    # 特殊处理：HR-V可能写成HRV或缤智
    if car_model == "HR-V":
        return ('HRV' in title.upper()) or ('HR-V' in title.upper()) or ('缤智' in title)
    
    # 其他车型：标题必须包含关键词
    return keyword in title

def is_valid_source(source):
    """来源黑名单验证"""
    if not source:
        return True
    
    for black in SOURCE_BLACKLIST:
        if black in source:
            return False
    
    return True

def is_valid_car_news_strict(title, source, keyword, car_model, logger=None):
    """V3超严格验证：6层过滤（增强日志版）"""
    
    # 第1层：标题必须包含搜索关键词
    if not is_title_contains_keyword(title, keyword, car_model):
        if logger:
            logger.record_filtered('Stage1_标题匹配', title, f"标题不包含关键词:{keyword}")
        return False, "标题不包含车型名称"
    
    # 第2层：标题长度合理（10-100字，排除超长软文）
    if len(title) < 10 or len(title) > 100:
        if logger:
            logger.record_filtered('Stage2_长度验证', title, f"标题长度{len(title)}字，不在10-100范围")
        return False, "标题长度异常"
    
    # 第3层：通用黑名单过滤
    for black in BLACKLIST:
        if black in title:
            if logger:
                logger.record_filtered('Stage3_通用黑名单', title, f"命中通用黑名单:{black}")
            return False, f"命中黑名单:{black}"
    
    # 第4层：来源黑名单过滤
    if not is_valid_source(source):
        if logger:
            logger.record_filtered('Stage4_来源黑名单', title, f"来源黑名单:{source}")
        return False, f"来源黑名单:{source}"
    
    # 第5层：车型专属黑名单过滤
    if car_model in SPECIAL_BLACKLIST:
        for black in SPECIAL_BLACKLIST[car_model]:
            if black in title.lower():
                if logger:
                    logger.record_filtered('Stage5_车型黑名单', title, f"命中{car_model}专属黑名单:{black}")
                return False, f"车型黑名单:{black}"
    
    # 第6层：必须包含汽车关键词
    has_automotive = any(kw in title for kw in AUTOMOTIVE_KEYWORDS)
    if not has_automotive:
        if logger:
            logger.record_filtered('Stage6_汽车关键词', title, "标题不包含任何汽车关键词")
        return False, "不包含汽车关键词"
    
    return True, "通过"

def calculate_similarity(str1, str2):
    """计算字符串相似度"""
    return SequenceMatcher(None, str1, str2).ratio()

def deduplicate_results(results, similarity_threshold=0.80):
    """去重：相似度>80%视为重复"""
    unique_results = []
    seen_titles = []
    
    for item in results:
        title = item['title']
        is_duplicate = False
        
        for seen_title in seen_titles:
            if calculate_similarity(title, seen_title) >= similarity_threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            seen_titles.append(title)
            unique_results.append(item)
    
    return unique_results

def sort_by_time(results):
    """按时间排序"""
    with_time = []
    without_time = []
    
    for item in results:
        pub_time, is_certain = parse_time_string(item.get('time', ''), item.get('url', ''))
        if pub_time and is_certain:
            item['parsed_time'] = pub_time
            with_time.append(item)
        else:
            without_time.append(item)
    
    with_time.sort(key=lambda x: x['parsed_time'], reverse=True)
    
    return with_time + without_time

# ==================== 数据源：仅新浪搜索（增强日志版）====================
def fetch_sina_search(keyword, car_model, days=14, logger=None):
    """新浪搜索抓取（V3超严格版 + 增强日志）"""
    results = []
    filtered_reasons = {}
    
    try:
        search_url = f"https://search.sina.com.cn/?q={quote_plus(keyword)}&c=news&sort=time"
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news_items = soup.find_all('div', class_='box-result clearfix')
        
        if logger:
            logger.record_fetched(len(news_items))
        
        for item in news_items:
            try:
                title_tag = item.find('h2')
                if not title_tag or not title_tag.find('a'):
                    continue
                
                title = title_tag.get_text(strip=True)
                url = title_tag.find('a')['href']
                
                source_tag = item.find('span', class_='fgray_time')
                source = ''
                time_str = ''
                if source_tag:
                    source = source_tag.get_text(strip=True).split()[0]
                    time_parts = source_tag.get_text(strip=True).split()
                    if len(time_parts) > 1:
                        time_str = ' '.join(time_parts[1:])
                
                # V3超严格验证
                is_valid, reason = is_valid_car_news_strict(title, source, keyword, car_model, logger)
                if not is_valid:
                    filtered_reasons[reason] = filtered_reasons.get(reason, 0) + 1
                    continue
                
                # 严格时间过滤
                if not is_within_days(time_str, url, days):
                    filtered_reasons["时间超出范围"] = filtered_reasons.get("时间超出范围", 0) + 1
                    if logger:
                        logger.record_filtered('Stage7_时间过滤', title, f"时间超出{days}天范围")
                    continue
                
                results.append({
                    'title': title,
                    'source': source,
                    'url': url,
                    'time': time_str,
                    'data_source': '新浪搜索'
                })
            except Exception as e:
                continue
        
        # 打印过滤统计
        if filtered_reasons:
            print(f"    过滤统计: {dict(filtered_reasons)}")
        
        return results
    except Exception as e:
        print(f"❌ 新浪搜索失败: {e}")
        return []

# ==================== 主抓取函数（增强日志版）====================
def fetch_news_strict(keyword, car_model, days=14, logger=None):
    """V3超严格抓取（仅新浪搜索 + 增强日志）"""
    results = fetch_sina_search(keyword, car_model, days, logger)
    print(f"  ✅ 新浪搜索: 有效{len(results)}条")
    return results

# ==================== 钉钉推送（无加签版本）====================
def send_to_dingtalk(message):
    """发送消息到钉钉群（无加签）"""
    headers = {'Content-Type': 'application/json'}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "东风本田竞品舆情监测",
            "text": message
        }
    }
    
    try:
        response = requests.post(DINGTALK_WEBHOOK, headers=headers, json=data, timeout=10)
        if response.json().get('errcode') == 0:
            print("✅ 钉钉推送成功")
            return True
        else:
            print(f"❌ 钉钉推送失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 钉钉推送异常: {e}")
        return False

# ==================== 主流程（V4增强版）====================
def run_monitor():
    """执行监测任务（V4增强版）"""
    print("=" * 100)
    print("🚀 东风本田竞品舆情监测系统 - V4增强版（宁缺毋滥）")
    print("=" * 100)
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 监测车型: {len(CAR_MODELS)}款")
    print(f"📡 数据源: 仅新浪搜索（最可靠）")
    print(f"⏳ 时间范围: 近{DAYS_RANGE}天（严格过滤）")
    print(f"🎯 每车型限制: 最多{MAX_NEWS_PER_MODEL}条（精品优先）")
    print(f"✨ V4新功能: 智能摘要 + 执行日志 + 丢弃记录 + 配置外置")
    print("=" * 100)
    print()
    
    # 创建执行日志记录器
    logger = ExecutionLogger()
    
    all_news = {}
    total_count = 0
    
    for model_name, keywords in CAR_MODELS.items():
        print(f"🔍 正在抓取: {model_name}")
        
        model_news = []
        model_fetched = 0
        
        for keyword in keywords:
            print(f"  📌 关键词: {keyword}")
            results = fetch_news_strict(keyword, model_name, DAYS_RANGE, logger)
            model_news.extend(results)
            model_fetched += len(results)
        
        # 去重
        model_news_unique = deduplicate_results(model_news, similarity_threshold=0.80)
        
        # 排序
        model_news_sorted = sort_by_time(model_news_unique)
        
        # 限制条数
        model_news_top = model_news_sorted[:MAX_NEWS_PER_MODEL]
        
        # 生成摘要（如果启用）
        if CONFIG['system']['enable_summary']:
            for news in model_news_top:
                summary_result = summarizer.generate_summary(news['title'])
                news['summary'] = summary_result['summary']
                news['keywords'] = summary_result['keywords']
                news['sentiment'] = summary_result['sentiment']
                news['opinion_type'] = summary_result['opinion_type']
        
        all_news[model_name] = model_news_top
        total_count += len(model_news_top)
        
        # 记录车型统计
        logger.record_model_stat(model_name, model_fetched, len(model_news_top))
        
        print(f"  ✨ {model_name}最终: {len(model_news_top)}条")
        print()
        
        time.sleep(1)
    
    # 完成统计
    logger.finalize(total_count)
    
    # 生成推送内容
    print("=" * 100)
    print("📊 抓取汇总")
    print("=" * 100)
    print(f"总新闻数: {total_count}条")
    print(f"有数据车型: {len([m for m, news in all_news.items() if news])}/{len(CAR_MODELS)}")
    print()
    
    # 打印执行概要报告
    if CONFIG['system']['enable_execution_log']:
        print(logger.generate_summary_report())
    
    # 打印丢弃样本报告
    if CONFIG['system']['enable_filtered_log']:
        print(logger.generate_filtered_samples_report())
    
    # 构建Markdown消息（增强版，包含摘要）
    message = f"# 东风本田竞品舆情监测\n\n"
    message += f"**监测时间:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    message += f"**数据源:** 新浪搜索（V4增强版，智能摘要）\n\n"
    message += f"**总计:** {total_count}条精选新闻，覆盖{len([m for m, news in all_news.items() if news])}/{len(CAR_MODELS)}款车型\n\n"
    message += "---\n\n"
    
    # 观点类型中文映射
    opinion_type_cn = {
        'advantage': '💪 优势',
        'disadvantage': '⚠️ 劣势',
        'comparison': '🔄 对比',
        'innovation': '💡 创新',
        'market_impact': '📈 市场',
        'general': '📰 综合'
    }
    
    for model_name, news_list in all_news.items():
        if news_list:
            message += f"## {model_name} ({len(news_list)}条)\n\n"
            for i, news in enumerate(news_list, 1):
                message += f"**{i}. [{news['title']}]({news['url']})**\n"
                
                # 添加摘要（如果有）
                if CONFIG['system']['enable_summary'] and 'summary' in news:
                    message += f"   > 📌 {news['summary']}\n"
                    if news.get('keywords'):
                        message += f"   > 🔑 {' | '.join(news['keywords'][:5])}\n"
                    if news.get('opinion_type'):
                        message += f"   > {opinion_type_cn.get(news['opinion_type'], '📰 综合')}\n"
                
                message += f"   > 来源: {news['source']}"
                if news.get('time'):
                    message += f" | {news['time']}"
                message += "\n\n"
    
    message += "---\n\n"
    message += "*由东风本田竞品舆情监测系统V4自动推送*"
    
    # 保存日志
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 保存时移除parsed_time
    all_news_json = {}
    for model, news_list in all_news.items():
        all_news_json[model] = []
        for news in news_list:
            news_copy = news.copy()
            if 'parsed_time' in news_copy:
                del news_copy['parsed_time']
            all_news_json[model].append(news_copy)
    
    log_file = f"{LOG_DIR}/monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(all_news_json, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 日志已保存: {log_file}")
    
    # 保存丢弃样本记录
    if CONFIG['system']['enable_filtered_log']:
        logger.save_filtered_samples()
    
    print()
    
    # 推送到钉钉
    print("📤 正在推送到钉钉...")
    send_to_dingtalk(message)
    
    print()
    print("=" * 100)
    print("✅ 任务完成！")
    print("=" * 100)
    
    return all_news, total_count

if __name__ == "__main__":
    run_monitor()

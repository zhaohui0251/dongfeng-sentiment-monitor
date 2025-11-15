# 🚗 东风舆情监测日报系统

> 基于GitHub Actions的自动化汽车舆情监测与分析系统，整合TrendRadar、新浪搜索等多源数据，通过AI智能分析生成每日舆情日报。

---

## ✨ 核心特性

- 🔍 **多源数据聚合**
  - TrendRadar 11平台热点（主力）：今日头条、百度、知乎、微博、B站、抖音等
  - 新浪搜索（补充）：专业汽车资讯
  - IT之家/36氪（边缘补充）：偶发汽车内容

- 🎯 **精准监测范围**
  - **艾力绅组**：艾力绅 vs 别克GL8、广汽丰田赛那、广汽本田奥德赛
  - **HR-V组**：HR-V vs 丰田锋兰达、日产逍客、广汽本田缤智
  - **Inspire组**：Inspire vs 广汽丰田凯美瑞、日产天籁、广汽本田雅阁

- 🤖 **AI智能分析**
  - 通义千问API驱动的情感分析
  - 自动生成50字精华摘要（专业、理性、轻度乐观）
  - 提取舆情热词TOP5
  - 正负向判断（重点关注本品负面）

- 📊 **6层严格过滤**
  1. 车型关键词匹配
  2. 标题长度验证（10-100字）
  3. 时间窗口过滤（48小时内）
  4. 黑名单过滤（二手车/改装/经销商等）
  5. 汽车领域关键词验证
  6. 标题去重（相似度>80%跳过）

- ⏰ **自动化调度**
  - 每日 06:00-08:00 三次数据采集
  - 每日 09:00 自动推送钉钉日报
  - GitHub Actions免费托管，无需服务器

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│          GitHub Actions 定时触发                         │
│     (06:00/07:00/08:00 抓取, 09:00 推送)                │
└────────────────────┬────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│ TrendRadar (主力) │  │ 新浪搜索 (补充)  │
│ 11个社交平台     │  │ 汽车专业资讯     │
└────────┬─────────┘  └────────┬─────────┘
         │                     │
         │         ┌───────────────────┐
         └─────────┤ IT之家/36氪      │
                   │ (边缘补充)        │
                   └─────────┬─────────┘
                             │
                             ▼
                   ┌─────────────────┐
                   │ 6层过滤引擎     │
                   │ - 关键词匹配    │
                   │ - 时间窗口      │
                   │ - 黑名单过滤    │
                   │ - 去重          │
                   └─────────┬───────┘
                             │
                             ▼
                   ┌─────────────────┐
                   │ 通义千问AI分析  │
                   │ - 情感判断      │
                   │ - 生成摘要      │
                   │ - 提取热词      │
                   └─────────┬───────┘
                             │
                             ▼
                   ┌─────────────────┐
                   │ 钉钉日报推送    │
                   │ Markdown格式    │
                   └─────────────────┘
```

---

## 🚀 快速开始

### 1. Fork仓库

点击右上角 **Fork** 按钮，将项目复制到你的GitHub账号下。

### 2. 配置GitHub Secrets

进入 `Settings` → `Secrets and variables` → `Actions`，添加以下密钥：

| Secret名称 | 说明 | 获取方式 |
|-----------|------|---------|
| `DASHSCOPE_API_KEY` | 通义千问API密钥 | [阿里云控制台](https://dashscope.console.aliyun.com/) |
| `DINGTALK_WEBHOOK_URL` | 钉钉机器人Webhook | 钉钉群机器人设置 |

#### 获取通义千问API Key

1. 访问 [阿里云灵积平台](https://dashscope.console.aliyun.com/)
2. 登录/注册阿里云账号
3. 开通灵积服务（免费）
4. 创建API Key，复制保存

#### 创建钉钉机器人

1. 打开钉钉群聊 → 群设置 → 智能群助手
2. 添加机器人 → 自定义机器人
3. 机器人名称：`东风舆情日报`
4. 安全设置：选择 **自定义关键词**，输入：`舆情`
5. 复制Webhook URL（格式：`https://oapi.dingtalk.com/robot/send?access_token=...`）

### 3. 启用GitHub Actions

1. 进入仓库的 `Actions` 标签页
2. 点击 `I understand my workflows, go ahead and enable them`
3. 找到 `东风舆情监测日报` 工作流
4. 点击 `Enable workflow`

### 4. 手动测试

点击右侧 `Run workflow` → 选择 `main` 分支 → `Run workflow`

等待2-3分钟，检查：
- ✅ GitHub Actions 显示绿色对勾
- ✅ 钉钉群收到测试日报
- ✅ 日报格式正确，包含舆情信息

---

## 📁 项目结构

```
dongfeng-sentiment-monitor/
├── .github/
│   └── workflows/
│       └── daily_monitor.yml       # GitHub Actions定时任务
├── config/
│   ├── models.yaml                 # 车型配置（9款车 + 竞品关系）
│   ├── keywords.yaml               # 内容分类关键词
│   └── sources.yaml                # 数据源权重配置
├── src/
│   ├── collectors/                 # 数据采集模块
│   │   ├── base_collector.py      # 采集器基类
│   │   ├── trendradar_collector.py # TrendRadar 11平台
│   │   ├── sina_collector.py       # 新浪搜索
│   │   └── tech_collector.py       # IT之家/36氪
│   ├── filters/
│   │   └── article_filter.py      # 6层过滤器
│   ├── analyzer/
│   │   └── sentiment_analyzer.py  # AI情感分析
│   ├── reporter/
│   │   └── dingtalk_pusher.py     # 钉钉推送
│   ├── utils/
│   │   ├── logger.py               # 日志模块
│   │   └── cache.py                # 去重缓存
│   └── main.py                     # 主入口
├── requirements.txt
├── .env.example                    # 环境变量模板
├── .gitignore
└── README.md
```

---

## 🔧 本地开发

### 环境准备

```bash
# 克隆仓库
git clone https://github.com/your-username/dongfeng-sentiment-monitor.git
cd dongfeng-sentiment-monitor

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入API密钥
```

### 运行模式

```bash
# 完整流程（采集+分析+推送）
python src/main.py --mode full

# 仅数据采集
python src/main.py --mode collect

# 仅AI分析
python src/main.py --mode analyze

# 仅推送日报
python src/main.py --mode push
```

---

## ⚙️ 配置说明

### 修改监测车型

编辑 `config/models.yaml`：

```yaml
car_models:
  - name: "新车型名称"
    brand: "品牌"
    category: "SUV/MPV/轿车"
    is_own: true  # 是否为本品
    aliases:
      - "别名1"
      - "别名2"
    keywords:
      - "关键词1"
      - "关键词2"
    competitors:
      - "竞品1"
      - "竞品2"
```

### 调整推送时间

编辑 `.github/workflows/daily_monitor.yml`：

```yaml
schedule:
  # 修改cron表达式（UTC时间 = 北京时间-8小时）
  - cron: '0 1 * * *'  # UTC 01:00 = 北京时间 09:00
```

### 修改黑名单

编辑 `config/models.yaml` 中的 `global_blacklist`：

```yaml
global_blacklist:
  - "二手车"
  - "新增黑名单词"
  # ...
```

---

## 📊 日报示例

```markdown
# 🚗 东风舆情监测日报

**监测时间**: 2025年11月15日 09:00  
**监测车型**: 艾力绅、HR-V、Inspire 及竞品  
**今日动态**: 共发现 18 条相关信息

---

## 📊 舆情概览

- **总计**: 18 条
- **情感分布**: 正面 8 | 中性 9 | 负面 1
- **本品负面**: 0 条 ✅

**内容分类**:  
- 评测: 6条
- 上市: 4条
- 对比: 3条
- 试驾: 3条
- 口碑: 2条

---

## 🔥 舆情热词 TOP 5

1. **新车上市** (5次)
2. **对比评测** (4次)
3. **智能驾驶** (3次)
4. **空间体验** (3次)
5. **油耗表现** (2次)

---

## 📰 竞品动态精选

### 上市

**👍 别克GL8 Avenir新款正式上市，售价45.99万起**

> 别克GL8 Avenir新款正式上市，搭载2.0T发动机，配备智能驾驶辅助系统...

来源: 今日头条 | [查看详情](https://...)

---

*📊 数据来源: TrendRadar(11平台) + 新浪搜索 + IT之家/36氪*  
*🤖 分析引擎: 通义千问 AI*  
*⚠️ 以上内容由系统自动采集分析，仅供参考*
```

---

## ❓ 常见问题

### Q: 为什么没有推送日报？

**排查步骤：**
1. 检查GitHub Actions是否启用
2. 查看Actions运行日志，是否有报错
3. 验证钉钉Webhook URL是否正确
4. 确认钉钉机器人关键词设置（必须包含"舆情"）

### Q: 数据量太少怎么办？

**解决方案：**
1. 检查过滤规则是否过严（`config/models.yaml` 中的黑名单）
2. 增加监测关键词（`config/models.yaml` 中的 `keywords`）
3. 调整时间窗口（`config/sources.yaml` 中的 `time_window_hours`）

### Q: AI分析不准确？

**优化建议：**
1. 使用更高级的通义千问模型（`sentiment_analyzer.py` 中修改 `model` 参数）
2. 优化分析提示词（`sentiment_analyzer.py` 中的 `_build_prompt` 方法）
3. 增加情感关键词词典（`config/keywords.yaml`）

### Q: GitHub Actions运行失败？

**常见原因：**
1. API密钥配置错误 → 检查Secrets设置
2. 网络请求超时 → 重新运行workflow
3. 依赖安装失败 → 检查 `requirements.txt`

---

## 🔄 版本历史

### v1.0.0 (2025-11-15)
- ✅ 整合TrendRadar、新浪搜索、IT之家/36氪数据源
- ✅ 实现6层过滤机制
- ✅ 集成通义千问AI分析
- ✅ 钉钉日报自动推送
- ✅ GitHub Actions自动化部署

---

## 📝 致谢

- [TrendRadar](https://github.com/sansan0/TrendRadar) - 开源热点聚合工具
- [通义千问](https://dashscope.console.aliyun.com/) - AI分析引擎
- 东风本田舆情监测项目 - 过滤逻辑参考

---

## 📧 联系方式

如有问题或建议，请提交 [Issue](https://github.com/your-username/dongfeng-sentiment-monitor/issues)

---

**🎯 让AI驱动舆情洞察，让自动化解放双手！**

# 📦 完整部署指南

## 一、前置准备清单

### 1. GitHub账号
- [ ] 已注册GitHub账号
- [ ] 可以创建公开/私有仓库

### 2. 通义千问API
- [ ] 注册阿里云账号：https://account.aliyun.com/register/
- [ ] 开通灵积服务：https://dashscope.console.aliyun.com/
- [ ] 创建API Key（免费额度：每天100万tokens）

### 3. 钉钉机器人
- [ ] 创建钉钉群（或使用现有群）
- [ ] 添加自定义机器人
- [ ] 获取Webhook URL

---

## 二、详细部署步骤

### 步骤1：Fork项目

1. 访问项目GitHub页面
2. 点击右上角 **Fork** 按钮
3. 等待Fork完成（约10秒）
4. 进入你的Fork仓库

### 步骤2：配置通义千问API

#### 2.1 开通服务

1. 访问 [阿里云灵积控制台](https://dashscope.console.aliyun.com/)
2. 登录阿里云账号（没有的话先注册）
3. 点击 **立即开通** 灵积服务
4. 阅读并同意服务协议
5. 开通成功后进入控制台

#### 2.2 创建API Key

1. 在控制台左侧菜单选择 **API-KEY管理**
2. 点击 **创建新的API-KEY**
3. 填写名称：`dongfeng-sentiment-monitor`
4. 点击 **确定**
5. **⚠️ 重要**：立即复制API Key，后续无法再次查看

#### 2.3 查看额度

- 免费版：每天100万tokens（约分析500篇文章）
- 如需更多额度，可购买付费套餐

### 步骤3：配置钉钉机器人

#### 3.1 创建机器人

1. 打开钉钉群聊
2. 点击右上角 `...` → **群设置**
3. 选择 **智能群助手**
4. 点击 **添加机器人** → **自定义**

#### 3.2 配置机器人

- **机器人名称**：`东风舆情日报`
- **机器人头像**：可上传汽车相关图标
- **消息推送**：默认开启

#### 3.3 安全设置（重要）

选择 **自定义关键词** 模式：
```
关键词1: 舆情
关键词2: 东风
关键词3: 日报
```

**说明**：推送的消息必须包含至少一个关键词，否则会被拒绝。我们的系统消息标题包含"舆情"，所以没问题。

#### 3.4 获取Webhook

1. 完成配置后，钉钉会显示Webhook URL
2. 格式：`https://oapi.dingtalk.com/robot/send?access_token=xxxxx`
3. **⚠️ 重要**：复制完整URL，保密此URL

### 步骤4：配置GitHub Secrets

#### 4.1 进入Secrets设置

1. 在你的Fork仓库页面
2. 点击 **Settings**（设置）
3. 左侧菜单选择 **Secrets and variables** → **Actions**
4. 点击 **New repository secret**

#### 4.2 添加DASHSCOPE_API_KEY

- **Name**: `DASHSCOPE_API_KEY`
- **Secret**: 粘贴你的通义千问API Key
- 点击 **Add secret**

#### 4.3 添加DINGTALK_WEBHOOK_URL

- **Name**: `DINGTALK_WEBHOOK_URL`
- **Secret**: 粘贴你的钉钉Webhook URL
- 点击 **Add secret**

#### 4.4 验证配置

确认Secrets页面显示：
```
DASHSCOPE_API_KEY       Updated now
DINGTALK_WEBHOOK_URL    Updated now
```

### 步骤5：启用GitHub Actions

#### 5.1 进入Actions页面

1. 点击仓库顶部 **Actions** 标签
2. 如果显示禁用提示，点击 **I understand my workflows, go ahead and enable them**

#### 5.2 查看工作流

- 应该看到 `东风舆情监测日报` 工作流
- 状态显示为可用

#### 5.3 手动触发测试

1. 点击 `东风舆情监测日报` 工作流
2. 点击右侧 **Run workflow** 下拉菜单
3. 选择分支：`main`
4. 点击绿色 **Run workflow** 按钮

### 步骤6：验证运行结果

#### 6.1 查看执行日志

1. 刷新页面，看到黄色圆点表示正在运行
2. 点击正在运行的workflow名称
3. 展开 `push-report` 任务
4. 查看各步骤日志：
   - ✅ Checkout代码
   - ✅ 设置Python环境
   - ✅ 安装依赖
   - ✅ 运行完整流程

#### 6.2 检查钉钉推送

大约2-3分钟后：
- ✅ GitHub Actions显示绿色对勾
- ✅ 钉钉群收到日报消息
- ✅ 消息格式正确，包含舆情信息

#### 6.3 查看Artifacts（可选）

1. 在workflow运行页面底部
2. 找到 **Artifacts** 区域
3. 下载 `daily-report-xxx` 查看详细日志

---

## 三、定时任务说明

### 默认调度时间

| 北京时间 | UTC时间 | 任务 |
|---------|---------|------|
| 06:00 | 22:00 (前一天) | 第1次数据采集 |
| 07:00 | 23:00 (前一天) | 第2次数据采集 |
| 08:00 | 00:00 | 第3次数据采集 |
| 09:00 | 01:00 | 完整流程 + 推送日报 |

### 修改推送时间

编辑 `.github/workflows/daily_monitor.yml`：

```yaml
schedule:
  # 例如改为每天10点推送
  - cron: '0 2 * * *'  # UTC 02:00 = 北京时间 10:00
```

**Cron表达式参考**：
```
格式: 分 时 日 月 星期

'0 1 * * *'     每天UTC 01:00 (北京09:00)
'0 2 * * *'     每天UTC 02:00 (北京10:00)
'0 1 * * 1-5'   工作日UTC 01:00 (北京09:00)
'0 1,13 * * *'  每天UTC 01:00和13:00 (北京09:00和21:00)
```

---

## 四、本地调试（可选）

如果需要在本地开发环境测试：

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/dongfeng-sentiment-monitor.git
cd dongfeng-sentiment-monitor
```

### 2. 创建虚拟环境

```bash
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```bash
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxxxx
```

### 5. 测试运行

```bash
# 测试数据采集
python src/main.py --mode collect

# 测试完整流程
python src/main.py --mode full
```

---

## 五、故障排查

### 问题1: Actions运行失败

**症状**：GitHub Actions显示红色❌

**排查步骤**：
1. 点击失败的workflow
2. 展开错误步骤查看日志
3. 常见错误：
   - `DASHSCOPE_API_KEY not found` → Secrets配置错误
   - `Failed to push to DingTalk` → Webhook URL错误或关键词不匹配
   - `ModuleNotFoundError` → 依赖安装失败，检查requirements.txt

### 问题2: 钉钉收不到消息

**排查步骤**：
1. 检查GitHub Actions是否成功（绿色✅）
2. 查看Actions日志，搜索"推送"相关信息
3. 验证Webhook URL：
   ```bash
   curl -X POST "YOUR_WEBHOOK_URL" \
   -H "Content-Type: application/json" \
   -d '{"msgtype":"text","text":{"content":"舆情测试"}}'
   ```
4. 确认返回 `{"errcode":0,"errmsg":"ok"}`
5. 检查机器人是否被删除或禁用

### 问题3: 数据量过少

**原因分析**：
- 过滤规则过严
- 关键词设置不合理
- 数据源暂时无相关内容

**解决方案**：
1. 查看Actions日志中的"过滤统计"
2. 调整 `config/models.yaml` 中的黑名单
3. 增加车型关键词和别名
4. 放宽时间窗口（默认48小时）

### 问题4: AI分析质量差

**优化方案**：
1. 升级模型（`sentiment_analyzer.py`）：
   ```python
   model = "qwen-plus"  # 更强大的模型
   ```
2. 优化提示词（`_build_prompt`方法）
3. 增加情感关键词词典（`config/keywords.yaml`）

---

## 六、维护建议

### 每周检查

- [ ] 查看GitHub Actions运行历史
- [ ] 检查钉钉日报质量
- [ ] 统计数据采集量
- [ ] 评估误抓率

### 每月优化

- [ ] 更新黑名单（根据误抓情况）
- [ ] 调整车型关键词
- [ ] 检查API额度使用情况
- [ ] 备份重要配置文件

### 长期规划

- [ ] 考虑增加新数据源
- [ ] 优化AI分析提示词
- [ ] 添加数据可视化
- [ ] 接入其他推送渠道（企业微信/飞书）

---

## 七、成本估算

| 项目 | 费用 | 说明 |
|-----|------|------|
| GitHub Actions | 免费 | 公开仓库无限制 |
| 通义千问API | 免费 | 每天100万tokens额度 |
| 钉钉机器人 | 免费 | 无限制 |
| **总计** | **0元** | 完全免费 |

**付费升级选项**（可选）：
- 通义千问高级模型：约¥0.002/千tokens
- GitHub Actions私有仓库：2000分钟/月（超出后¥0.008/分钟）

---

## 八、联系支持

**文档问题**：查看 [README.md](README.md)  
**技术问题**：提交 [GitHub Issue](https://github.com/your-username/dongfeng-sentiment-monitor/issues)  
**功能建议**：欢迎提交 [Pull Request](https://github.com/your-username/dongfeng-sentiment-monitor/pulls)

---

**🎉 祝部署顺利！让AI为你的舆情监测保驾护航！**

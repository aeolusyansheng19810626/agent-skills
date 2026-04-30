---
title: Agent Skills
emoji: 🤖
colorFrom: indigo
colorTo: cyan
sdk: streamlit
sdk_version: "1.56.0"
python_version: "3.11"
app_file: app.py
pinned: false
---

# 🤖 Router Agent - 统一对话入口

一个智能 AI Agent 系统，通过 LLM 自动识别用户意图并路由到专门的技能模块。系统提供统一的聊天界面，实时显示技能调用状态。

## 🌟 核心特性

- **🎯 智能路由**: 根据用户输入自动选择合适的技能
- **🔧 实时显示**: 执行时显示 "🔧 正在调用: xxx_skill"
- **📦 模块化技能**: 通过创建 skill.md 和 skill.py 轻松添加新技能
- **💬 Streamlit UI**: 美观、响应式的聊天界面
- **🔄 流式响应**: 实时流式输出技能执行结果
- **🌐 完整中文支持**: 所有界面和输出均为简体中文

## 📁 项目结构

```
agent-skills/
├── app.py                      # Streamlit 主应用
├── router.py                   # Router Agent（LLM 意图识别）
├── skill_loader.py             # 自动技能发现和加载
├── requirements.txt            # Python 依赖
├── .env.example               # 环境变量模板
├── README.md                  # 本文件
└── skills/                    # 技能目录
    ├── web_search/
    │   ├── skill.md          # 技能定义
    │   └── skill.py          # 技能实现
    ├── stock_analysis/
    │   ├── skill.md
    │   └── skill.py
    ├── document_qa/
    │   ├── skill.md
    │   └── skill.py
    └── code_generation/
        ├── skill.md
        └── skill.py
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.8 或更高版本
- Groq API 密钥 ([获取地址](https://console.groq.com/keys))
- Tavily API 密钥 ([获取地址](https://tavily.com/))

### 2. 安装步骤

```bash
# 克隆仓库
git clone <your-repo-url>
cd agent-skills

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，添加你的 API 密钥
# GROQ_API_KEY=your_groq_api_key_here
# TAVILY_API_KEY=your_tavily_api_key_here
```

### 4. 运行应用

```bash
streamlit run app.py
```

应用将在浏览器中打开，地址为 `http://localhost:8501`

## 🎯 可用技能

### 1. 🔍 网络搜索 (`web_search`)
- **功能**: 搜索互联网获取最新信息，自动翻译为简体中文
- **适用场景**: 最新新闻、时事、实时数据
- **技术栈**: Tavily API + Groq LLM（翻译）
- **示例**: "最新的 AI 新闻是什么？"

### 2. 📊 股票分析 (`stock_analysis`)
- **功能**: 分析股票表现，提供技术面和新闻面分析
- **适用场景**: 股价查询、走势分析、公司分析
- **技术栈**: yfinance + Groq LLM
- **特性**: 
  - 市值格式化（T/B 后缀）
  - 新闻自动翻译为简体中文
  - AI 分析避免重复内容
- **示例**: "分析 AAPL 股票"

### 3. 📚 文档问答 (`document_qa`)
- **功能**: 从已上传的文档中检索并回答问题
- **适用场景**: 文档搜索、知识库查询
- **技术栈**: 内存存储 + Groq LLM
- **特性**:
  - 支持 .txt 和 .md 文件
  - 改进的中文搜索算法
  - 防止文档重复上传
  - 持久化存储（session_state）
- **示例**: "根据上传的文档，怎么创建侧边栏？"

### 4. 💻 代码生成 (`code_generation`)
- **功能**: 根据需求生成各种编程语言的代码
- **适用场景**: 函数创建、脚本编写、代码示例
- **技术栈**: Groq LLM
- **特性**:
  - 支持多种编程语言
  - 完整的中文注释和说明
  - 包含使用示例和后续步骤
- **示例**: "写一个 Python 函数计算斐波那契数列"

## 🔧 工作原理

### Router Agent 流程

```
用户输入 → Router Agent → Groq LLM → 意图识别 → 技能选择 → 执行技能 → 流式输出结果 → UI 显示
```

### 核心组件

1. **Skill Loader** (`skill_loader.py`)
   - 自动扫描 `skills/` 目录
   - 解析 `skill.md` 文件获取元数据
   - 构建技能注册表
   - 提供动态技能导入

2. **Router Agent** (`router.py`)
   - 将所有技能描述注入 LLM prompt
   - 使用 Groq LLM (llama-4-scout-17b-16e-instruct) 进行意图识别
   - 返回 JSON 格式的技能名称和参数
   - 完整的简体中文推理过程
   - 处理无匹配查询的回退逻辑

3. **技能模块** (`skills/*/skill.py`)
   - 每个技能有一个 `run(params)` 生成器函数
   - 流式输出结果供 UI 显示
   - 自包含的错误处理
   - 完整的中文本地化

4. **Streamlit 应用** (`app.py`)
   - 聊天界面和历史记录
   - 实时技能调用指示器
   - 文档上传管理（侧边栏）
   - 可折叠的推理过程和结果显示
   - 统一的字体和样式

## ⚠️ 重要注意事项

### 文档问答 (document_qa) 关键点

1. **文档存储持久化**
   - 文档存储在 `st.session_state.document_store` 中
   - 避免 Streamlit 模块热重载导致数据丢失
   - 不要使用模块级全局变量存储数据

2. **防止文档重复上传**
   - 使用 `st.session_state.uploaded_files` 跟踪已上传文件
   - 通过文件名和大小生成唯一标识
   - 上传前检查是否已存在

3. **中文搜索优化**
   - 使用多层次评分机制：
     - 子串匹配（+100分）
     - 单字符匹配（+1分/字符）
     - 词语匹配（+10分/词）
   - 支持中英文混合查询

4. **文档传递机制**
   - app.py 通过 params 传递 document_store 给 skill
   - skill 接收 Optional[DocumentStore] 参数
   - 确保上传和检索使用同一个存储对象

### 股票分析 (stock_analysis) 关键点

1. **市值格式化**
   - >= 1T: 显示为 `$X.XXX T`
   - >= 1B: 显示为 `$X.XX B`
   - < 1B: 显示为 `$X.XX M`

2. **新闻翻译**
   - 使用 Groq LLM 将英文新闻翻译为简体中文
   - 保留原始来源链接

3. **AI 分析**
   - System prompt 包含"避免重复内容"指令
   - 每个观点只陈述一次

### 网络搜索 (web_search) 关键点

1. **结果翻译**
   - Tavily 返回英文结果
   - 使用 Groq LLM 翻译为简体中文
   - 保留段落格式

### 代码生成 (code_generation) 关键点

1. **完整中文化**
   - 所有提示和说明使用简体中文
   - 代码注释使用简体中文
   - 后续步骤说明使用简体中文

## 📝 添加新技能

### 1. 创建技能目录

```bash
mkdir skills/my_new_skill
```

### 2. 创建 `skill.md`

```markdown
# Skill: my_new_skill

## 描述
技能的简要描述

## 触发条件
- 何时触发此技能
- 表明此技能的关键词

## 不触发条件
- 何时不使用此技能

## 参数
- param1: str  # 描述
- param2: int  # 描述

## 返回
技能返回的内容
```

### 3. 创建 `skill.py`

```python
from typing import Generator

def run(params: dict) -> Generator[str, None, None]:
    """
    技能入口函数
    
    Args:
        params: 包含所需参数的字典
        
    Yields:
        结果字符串（支持 Markdown 格式）
    """
    # 获取参数
    param1 = params.get("param1")
    if not param1:
        yield "❌ 错误：缺少 'param1' 参数\n"
        return
    
    # 你的实现代码
    yield f"💡 正在处理：{param1}\n\n"
    
    try:
        # 执行任务
        result = your_processing_logic(param1)
        yield f"✅ 结果：{result}\n"
    except Exception as e:
        yield f"❌ 错误：{str(e)}\n"
```

### 4. 重启应用

技能将自动被发现和加载！

## 🧪 测试单个技能

每个技能都可以独立测试：

```bash
# 测试网络搜索
python skills/web_search/skill.py "最新 AI 新闻"

# 测试股票分析
python skills/stock_analysis/skill.py AAPL

# 测试文档问答
python skills/document_qa/skill.py "退款政策"

# 测试代码生成
python skills/code_generation/skill.py "斐波那契函数"
```

## 🔍 测试路由器

```bash
# 测试路由逻辑
python router.py
```

## 📊 系统要求

- **内存**: 最低 2GB（推荐 4GB）
- **Python**: 3.8+
- **网络**: API 调用需要互联网连接
- **浏览器**: 现代浏览器（Chrome、Firefox、Safari、Edge）

## 🛠️ 故障排除

### 问题: "GROQ_API_KEY not set"
**解决方案**: 确保已创建 `.env` 文件并填入 API 密钥

### 问题: "Skill not found"
**解决方案**: 检查技能目录是否同时包含 `skill.md` 和 `skill.py`

### 问题: "Import error"
**解决方案**: 确保已安装所有依赖: `pip install -r requirements.txt`

### 问题: "Tavily API error"
**解决方案**: 验证 TAVILY_API_KEY 是否正确且有可用额度

### 问题: 文档上传后检索不到
**解决方案**: 
1. 检查是否使用了 session_state 存储
2. 确认 document_store 通过 params 传递给 skill
3. 重启应用清除旧的模块缓存

### 问题: 文档重复累积
**解决方案**:
1. 使用 uploaded_files 跟踪机制
2. 点击"清空所有文档"按钮
3. 重新上传文档

### 问题: 中文搜索匹配失败
**解决方案**:
1. 使用文档中的具体关键词
2. 尝试不同的表述方式
3. 检查文档内容是否包含相关信息

## 🔐 安全注意事项

- 永远不要将 `.env` 文件提交到版本控制
- 保护好 API 密钥并定期轮换
- 生产环境使用环境变量
- 生产部署时实施速率限制
- 文档上传仅支持文本文件（.txt, .md）

## 📈 性能优化建议

1. **缓存**: 考虑为重复查询添加缓存
2. **异步**: 使用异步操作提升性能
3. **批处理**: 批量处理多个文档
4. **连接池**: 复用 HTTP 连接
5. **向量数据库**: 对于大规模文档，考虑使用 Qdrant 等向量数据库

## 🎨 UI 特性

- **可折叠组件**: 推理过程和完整结果可折叠
- **实时状态**: 显示正在调用的技能
- **统一样式**: 一致的字体、字号和颜色
- **响应式设计**: 适配不同屏幕尺寸
- **侧边栏管理**: 技能列表和文档管理

## 🤝 贡献指南

1. Fork 仓库
2. 创建功能分支
3. 添加你的技能或改进
4. 充分测试
5. 提交 Pull Request

## 📄 许可证

MIT License - 可自由用于任何目的

## 🙏 致谢

- **Groq**: 提供快速的 LLM 推理
- **Tavily**: 提供网络搜索 API
- **Streamlit**: 提供出色的 UI 框架
- **yfinance**: 提供股票数据

## 📞 支持

如有问题、疑问或建议：
- 在 GitHub 上提交 issue
- 查看现有文档
- 参考技能示例

## 🔄 版本历史

### v1.0.0 (当前版本)
- ✅ 完整的中文本地化
- ✅ 四个核心技能实现
- ✅ 智能路由系统
- ✅ 文档问答持久化存储
- ✅ 改进的中文搜索算法
- ✅ 股票分析市值格式化
- ✅ 防止文档重复上传
- ✅ 可折叠的 UI 组件

---

**用 ❤️ 构建，使用 Groq、Tavily 和 Streamlit**
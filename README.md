# 文史写稿助手（作者做B站视频写文案用的，需要的关B站关注FlameJZ自取~）

基于中国古代史料的 RAG写作与审稿系统。检索原文、标注出处、核查事实，解决大模型在历史写作中的幻觉问题。

## 与原生大模型的区别

| | 原生大模型 | 本系统 |
|---|---|---|
| 事实来源 | 训练数据，无法追溯 | 史料原文检索，标注出处 [1][2] |
| 幻觉控制 | 无 | 检索 → 相关性过滤 → 引用溯源，多层过滤 |
| 可验证性 | 无 | 来源面板展示原文，高亮被引用句子 |
| 审稿能力 | 无 | 内置审稿模式，逐条核查史实断言 |
| 古文检索 | 通用分词 | jieba + 字级双通道分词，向量 + BM25 混合检索 |

## 架构

```
Frontend (React + TypeScript + Tailwind)
  │  SSE 流式通信
Backend (FastAPI)
  ├── 问答管线: 查询改写 → 混合检索 → 相关性过滤 → 三明治排序 → 生成 → 引用溯源
  ├── 审稿管线: 断言提取 → 并行核查(4线程) → 流式判定推送
  ├── ChromaDB (向量存储, 192k+ 条记录)
  ├── BM25 Index (磁盘缓存, jieba + 字级分词)
  └── Claude Sonnet/Opus API
```

## 核心技术

### 混合检索

- **向量检索**：DashScope text-embedding-v4 + ChromaDB 余弦相似度，捕获语义关联
- **BM25 检索**：jieba 词级 + 字级 token 双通道，适配古文单字即词的特点，索引含书名卷名元数据
- 按 chunk_id 和文本指纹去重，BM25 索引支持磁盘缓存（19 万条首次构建后秒加载）

### 多阶段管线

1. **查询改写**：LLM 将问题拆为 1-3 条检索 query，支持代词解析和多轮上下文
2. **相关性过滤**：LLM 逐条判断检索结果是否相关，移除噪声（保底 1 条）
3. **三明治排序**：最相关结果放首尾，缓解 LLM 长上下文中间遗忘问题
4. **引用溯源**：生成完成后 LLM 标注实际引用的原文句子，前端高亮显示

### 审稿模式(还没完全做好）

独立管线，用于核查稿件史实：

1. **断言提取**：LLM 从稿件中识别可验证的事实断言，跳过主观评论和修辞
2. **并行核查**：4 线程并发，每条断言直接检索证据 + LLM 判定
3. **三级判定**：有据可查 / 与史料矛盾（指出差异）/ 史料不足
4. 完成一条立刻推送前端，无需等待全部完成

### 古文优化

- 按古文标点断句分块（500 字/块，2 句重叠）
- BM25 索引含 citation 和 chapter 前缀，搜书名或卷名可直接命中
- 引文精确到卷和篇：`[1] 《史记·项羽本纪》（卷七）`

## 数据

| 指标 | 数值 |
|------|------|
| 史料来源 | 二十四史、资治通鉴等（25 部，持续扩展） |
| 向量记录数 | 192,311 条 |
| 嵌入模型 | DashScope text-embedding-v4 |
| 生成模型 | Claude Sonnet 4 / Opus 4 |

## 功能

- 问答 + 审稿双模式，侧边栏切换
- 四种文风：默认 / 学术 / 博客 / 叙事
- 史书多选过滤
- SSE 流式输出
- 引用溯源：点击编号跳转原文，高亮引用句
- 可选古文白话对照翻译
- 多轮对话（3 轮上下文，代词解析）
- PDF 导出
- Sonnet / Opus 模型切换

## 快速开始

```bash
# 安装
pip install -e .
cd frontend && npm install && cd ..

# 配置 .env
ANTHROPIC_API_KEY=sk-ant-...
DASHSCOPE_API_KEY=sk-...

# 数据导入
python -m history_rag ingest          # 全部
python -m history_rag ingest -s 史记  # 指定

# 启动
python -m history_rag serve           # 后端 :8000
cd frontend && npm run dev            # 前端 :5173
```

## 技术栈

**后端**：FastAPI, ChromaDB, rank-bm25, jieba, DashScope, Anthropic Claude, Pydantic

**前端**：React 19, TypeScript, Tailwind CSS 4, Vite 7, html2pdf.js

## 项目结构

```
src/history_rag/
├── api.py                  # API 端点（问答 + 审稿）
├── cli.py                  # CLI（ingest / serve / stats）
├── config.py               # 配置
├── ingest/                 # 数据入库（下载 → 解析 → 分块）
├── embeddings/             # 嵌入（DashScope / 本地）
├── store/vectordb.py       # ChromaDB 向量存储
├── retrieval/              # 混合检索（向量 + BM25）
└── generation/             # LLM 调用（生成 / 改写 / 过滤 / 断言提取 / 高亮）

frontend/src/
├── App.tsx                 # 双模式主应用
├── api.ts                  # SSE 客户端
└── components/             # Sidebar / ChatMessage / ReviewMessage / SourcePanel
```

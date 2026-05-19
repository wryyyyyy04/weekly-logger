# 实验日志与周报管理系统

面向研究生的每日实验记录与周报自动生成工具。在浏览器中记录每日待办和实验进展，每周一键生成 PPTX + PDF 格式的周报。

## 功能

| 功能 | 说明 |
|------|------|
| 📋 **每日待办** | 添加、勾选、编辑、删除待办事项，按"待办/实验"分类 |
| 🔬 **实验日志** | 记录实验标题、描述、使用设备、实验结果、标签 |
| 📎 **文件管理** | 拖拽上传、点击选择、Ctrl+V 粘贴剪贴板图片，支持批量上传 |
| 📊 **本周概览** | 按7天网格查看本周记录，课题进展自评（好/中/差） |
| 📄 **周报生成** | 基于一周数据自动汇总，生成 PPTX + PDF 双格式周报 |
| ⏱ **时间节点** | 管理博士关键节点（选题报告、中期、学术报告、论文定稿） |

## 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn sqlalchemy python-pptx python-multipart PyMuPDF aiosqlite
```

### 2. 启动服务

```bash
cd weekly_logger
python main.py
```

### 3. 打开浏览器

访问 **http://localhost:8765**

## 使用流程

```
周一~周五：在「今日记录」中每天录入待办和实验
         ↓
   周五下午：切换到「周报生成」标签页
         ↓
         选择当前周的周一 → 点击「加载本周数据」
         ↓
         检查自动汇总的内容，补充各板块
         ↓
         点击「保存并生成周报」→ 得到 PPTX + PDF
```

## 周报格式

生成的周报包含6个板块，格式与清华大学博士周报模板一致：

1. 上周拟定的本周计划
2. 本周详细研究进展（自动汇总本周记录）
3. 后续待解决的问题或研究方案调整
4. 下周详细计划
5. 课题进展自评（好/中/差）
6. 成果发表时间节点更新

## 文件结构

```
weekly_logger/
├── main.py              # FastAPI 后端入口
├── models.py            # SQLite 数据库模型
├── report_generator.py  # 周报生成器（PPTX + PDF）
├── templates/
│   └── index.html       # 前端界面（深色主题）
├── data/                # 数据库文件（自动创建，已 gitignore）
├── uploads/             # 上传文件存储（已 gitignore）
└── output/              # 生成的周报输出（已 gitignore）
```

## 技术栈

- **后端**：Python FastAPI + SQLAlchemy + SQLite
- **前端**：单页 HTML + Vanilla JS（无需构建工具）
- **报告生成**：python-pptx（PPTX）+ PyMuPDF（PDF）
- **端口**：8765

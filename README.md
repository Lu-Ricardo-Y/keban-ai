# 课伴 AI · 离线资料问答工具

课伴 AI 是一个在自己电脑上运行的选择题助手。它用本地大语言模型读取题目文字或截图，检索你**自行导入**的 PDF、Markdown、TXT 资料，然后给出选项、简短理由和可回查的资料片段。运行时网页、模型和资料检索都在本机；首次安装 Python 依赖、Ollama 和模型需要联网。

**本仓库不含任何真实课程课件、用户上传的 Markdown、题目截图、模型权重、Ollama 程序或资料库。** `examples/demo_notes.txt` 是专门编写的虚构验证资料。每位使用者都在自己的电脑上导入自己有权使用的文件。

> English summary: Keban AI is a local multiple-choice study assistant. It accepts typed or pasted question screenshots, retrieves passages from documents that each user imports on their own computer, and answers with local Ollama models. This repository contains source code and a synthetic demo only. See “English quick start” below.

## 为什么做这个项目

目标是在没有互联网的环境中，仍能查找个人资料并回答选择题，同时让答案附上检索依据。实现过程按实际遇到的问题逐步演进：

1. 先做一个只在 `127.0.0.1` 运行的网页和 Python 服务，实现文件导入、资料库管理、关键词检索和本地模型调用。
2. 接入本地 Ollama 模型，使题目可以通过文字、截图、粘贴或拖入图片提交；图片题要求所选模型支持视觉。题目图片只在本次问答的内存中使用。
3. 给答案增加选项优先的简短格式、来源片段、生成进度、首字等待时间和停止按钮；无课程证据时明确标示模型知识。
4. 处理长文档的页码：PDF 按原页导入，带 `<!-- page: N -->` 或 `## PDF 第 N 页` 标题的 Markdown 按页切分，引用保留文档名和页码。
5. 增加隔离资料库的自动检查，以及可由任何人自行运行的人工验证流程。检查重点包括正确导入、来源页码、图片问题、离线运行与错误提示。

它采用检索增强问答：问题 → 本地检索相关片段 → 将少量片段与题目交给本地模型 → 显示答案和来源。资料存储量可以大于模型一次能读的上下文；每道题只送入少量检索结果。没有模型训练或微调步骤。

## 功能和边界

- 单选、多选或自动识别；输入题干与选项，或上传、拖入、粘贴最多两张 PNG/JPG/WebP 截图。
- PDF、UTF-8 Markdown、TXT 导入；同一个文件重复导入不会创建重复记录。
- PDF 与带页码的 Markdown 显示 PDF 页码；普通 TXT/Markdown 显示文档分段。
- 中文、英文关键词检索。答案可引用界面列出的资料片段；没有匹配资料时会说明使用模型知识。
- 一次一题，不保存聊天历史。模型上下文配置为 8192 token，回答上限 600 token。
- 网页只监听 `127.0.0.1`，默认地址为 `http://127.0.0.1:8765/`。模型服务默认连接本机 Ollama `127.0.0.1:11434`。

当前检索是关键词匹配，不是语义向量检索；跨语言题目最好补充英文专业术语。扫描 PDF 需要预先 OCR。导入的 PDF 中的图片不会自动进入资料检索；题目截图识别与资料库的图片索引是两件不同的事。公式、表格、单位和否定词仍需使用者核对。这里没有独立计算器，也没有声称达到某个考试准确率。

## 安装前准备

需要 Python 3.10 或更新版本、Ollama，以及现代浏览器。Python 依赖只有 `pypdf`（PDF 文字提取）和 `Pillow`（题目图片处理）。macOS、Windows、Linux 都可以按下列命令启动；实际模型速度取决于机器内存与硬件。原型曾在 MacBook Air M4、16 GB 内存上运行，但不能把这个体验当作其他设备的性能保证。

### 先用 llmfit 选择模型

在**目标电脑上联网安装** [llmfit](https://github.com/AlexsJones/llmfit)，让它检测那台电脑的 RAM、CPU、GPU/统一内存，并评估模型是否适合。llmfit 提供的是硬件适配与速度估计，实际速度和题目正确率仍须在目标电脑验证。安装方式以 [llmfit 官方说明](https://github.com/AlexsJones/llmfit#install)为准；例如 macOS 使用 `brew install AlexsJones/llmfit/llmfit`，Windows 可用 `winget install --exact --id AlexsJones.llmfit`，Linux 可下载其官方 release 二进制文件。

```sh
llmfit system
llmfit --max-context 8192 recommend --json --limit 5
llmfit --max-context 8192 recommend --use-case multimodal --json --limit 5
```

第一条核对硬件检测是否正确。文字题可从一般推荐中选择；图片题须从多模态候选中选择，并确认 **Ollama 实际提供该模型、该版本支持 vision**。不要仅凭模型名称含有 `VL` 或 llmfit 的适配分数认定它能在本工具识别图片。llmfit 使用的模型 ID 与 Ollama 下载标签可能不同，要到 [Ollama 模型库](https://ollama.com/search)查对应标签。优先留出系统内存余量，再比较下载大小、预计速度和实际作答效果；没有合适模型时可先用文字题验证流程。**本项目不指定统一的模型型号，也不自动下载模型。**

从 [Ollama 官方下载页](https://ollama.com/download)安装 Ollama 并启动本地服务。在联网时把下面的占位符替换成你选定的 **Ollama 标签**；不要原样复制尖括号：

```sh
ollama pull <你选定的本地模型标签>
ollama list
```

`ollama list` 应列出刚下载的模型。图片题仅支持 Ollama 中带 `vision` 能力的本地模型；LM Studio 适配器目前仅供文字题使用。下载完成、程序依赖安装完成后，可以断开互联网运行。

### macOS / Linux

在项目目录打开终端：

```sh
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python launch.py
```

之后 macOS 也可以双击 `启动.command`；Linux 可以运行 `sh start.sh`。若 macOS 拒绝打开从网络下载的脚本，直接在终端运行上面的 Python 命令即可。请保留启动终端，关闭它会停止网页服务。

### Windows（PowerShell）

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe launch.py
```

之后可以双击 `start.bat`。如果 Ollama 没有自动运行，先启动 Ollama 应用或在另一个终端运行 `ollama serve`。`launch.py` 会尝试启动 PATH 中的 Ollama；若已有本地服务，会复用它。

启动后打开 `http://127.0.0.1:8765/`，点击“检测模型”，**手动选择**已下载的本地模型；程序不会按某个型号自动选中。网页没有联网查询功能，也不能调用云端模型标签。

## 使用方法

1. 在网页“课程资料”区点击“＋ 导入资料”，选择**你自己的** PDF、Markdown 或 TXT 文件。上传仅送到本机的 Python 服务，存入本机 `data/`。单个文件须小于 50 MB。
2. 在资料列表核对文件名、页数及“导入检查提示”。图片型 PDF 或错位的公式、表格要先整理或人工核对。
3. 在题目框输入完整题干与所有选项。图片题可点“添加题目图片”、拖入，或按 ⌘V / Ctrl+V 粘贴截图。每题最多两张图。
4. 选题型并点击“识别并作答”。先看答案，再展开“课程依据与图片转录”核对检索片段和页码。点击“新题”会清空本题输入，不会把上一题带入下一题。

整理过的 Markdown 可使用两种页码方式：

```md
<!-- page: 1 -->
## Introduction
第一页正文

<!-- page: 2 -->
## Next topic
第二页正文
```

或者 `## PDF 第001页：Introduction`、`## PDF 第 2 页：Next topic` 这样的连续标题。页码必须从 1 开始，逐页连续。没有页码标记的 Markdown/TXT 仍能导入，但只能定位到文档分段。请勿把目录、重复 OCR 或重复解释文件作为多份独立证据导入。

## 验证安装与使用

自动验证在隔离的临时资料库运行，不会读取或修改你正式导入的资料：

```sh
# macOS / Linux
./.venv/bin/python -m unittest discover -s tests -v

# Windows PowerShell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试覆盖页码导入、重复文件、检索、来源、模型适配、图片处理、流式输出、本机访问限制等。两项 HTTP 测试需要允许绑定本机临时端口；某些受限沙盒会阻止它们，但普通本机环境应可运行。

人工验证使用仓库里的**虚构示例** `examples/demo_notes.txt`：

1. 导入该 TXT；资料列表应显示一份资料。
2. 问：“According to the imported demo notes, which process cures liquid resin with ultraviolet light? A. Process A B. Process B C. Process C”。预期答 A，并在来源区找到 `demo_notes.txt`。若模型给出别的选项，以示例原文为准；模型输出不是测试的唯一判据。
3. 把这道题截图后贴入问答框，确认截图转录、答案和来源仍可查看。题干与全部选项应清晰可见。
4. 断开 Wi‑Fi、保持 Ollama 模型已下载，刷新网页并重复文字题。页面应仍能连接本地模型并回答；若网页无法打开，检查启动终端是否仍在运行。
5. 自己制作一份两页 Markdown，选用上面任意一种页码格式，并在同一个文件中保持格式一致；资料列表应显示 2 页，问第二页特有的词时来源应显示 PDF 第 2 页。

验证只能说明安装、检索和基本交互正常；真实学科题的正确率还需用带标准答案的题集单独评估。尤其检查 `NOT`、`EXCEPT`、数字、单位和表格列关系。

## 项目结构和数据保护

```text
app.py             本地 HTTP 服务、导入、检索和模型适配
launch.py          启动本地 Ollama（若可用）并打开网页
static/            浏览器界面
tests/             隔离的自动验证
examples/          虚构演示资料
requirements.txt   Python 依赖
启动.command        macOS 启动入口
start.sh           Linux 启动入口
start.bat          Windows 启动入口
data/              用户本机资料和索引；运行时创建，不提交 Git
```

`.gitignore` 排除 `data/`、模型、运行软件、虚拟环境、PDF、图片、ZIP、日志和常见私人资料目录。请在上传自己的 fork 或提交更改前查看 `git status`，确认没有课程原文、个人截图、令牌或本地数据库。**将这个仓库发给别人，不会自动给对方你的资料或模型**；对方需要自行安装模型和导入文件。

### 给安装者或另一位 Agent 的交接步骤

1. 克隆本仓库，阅读上面的功能边界；不要从 GitHub 寻找课程资料，本仓库只有虚构的演示文件。
2. 在**实际要运行工具的电脑**安装 Python、llmfit 和 Ollama；按“先用 llmfit 选择模型”运行硬件检测与推荐。选择一个适合该设备、且在 Ollama 中可用的模型标签。若需要图片答题，额外验证视觉能力。不要把开发者原先使用的型号写死到脚本、配置或安装指令里。
3. 联网下载选定模型和 Python 依赖，按对应系统启动。打开网页检测模型，手动选定它；先用 `examples/demo_notes.txt` 执行下方自动与人工验证。
4. 使用者自行提供有权使用的 PDF/Markdown/TXT，**在自己的电脑上**导入。资料文件、运行生成的 `data/`、模型权重，以及任何背景知识库压缩包都不得提交、上传到 GitHub 或作为 Release 附件发布。若使用者另有本地资料包，应在仓库目录外解压，先检查重复内容、失效图片链接及 OCR 警告，再导入真正需要的文件。
5. 离线前确认网页、Ollama 和选定模型都能在断网状态正常工作。通过演示验证只说明安装成功；答题准确率须用有标准答案的题集另行评测。

## 常见问题

- **检测不到模型**：确认 Ollama 正在运行；在终端执行 `ollama list`；若尚未下载，按上面的 llmfit 流程选定型号，再联网执行 `ollama pull <你选定的本地模型标签>`。
- **网页端口被占用**：关闭另一个占用 8765 的程序，或在启动前设置环境变量 `STUDY_PORT` 为另一个空闲端口。若已有另一款问答工具占用该端口，启动器会明确报错。
- **PDF 页文字很少**：文件可能是扫描件。先做 OCR；原 PDF 图片不会被检索器自动理解。
- **图片题失败或很慢**：确认所选 Ollama 模型的实际能力包含 `vision`；裁剪到一题，确保题干、选项、图例与单位清楚。图像和文字共享 8192 token 上下文；llmfit 的速度估计不能代替本机实测。
- **答案引用不准确**：展开来源检查原文；当前系统只展示模型实际收到的检索片段，不会自动证明每句话都被资料支持。
- **切换到离线后不可用**：首次安装与模型下载必须在联网时完成；离线前确认 `ollama list` 能看到本地模型，浏览器访问的是 `127.0.0.1`。

本项目是本地学习工具，回答由模型生成，使用者应对照原始资料核查关键结论。

## English quick start

Install Python 3.10+, [llmfit](https://github.com/AlexsJones/llmfit), and [Ollama](https://ollama.com/download) while online. On the **target computer**, run `llmfit system` and `llmfit --max-context 8192 recommend --json --limit 5`; for screenshot questions, also run `llmfit --max-context 8192 recommend --use-case multimodal --json --limit 5`. Choose a model that fits the machine, find its actual Ollama tag, and verify vision capability if images are needed. Run `ollama pull <chosen-ollama-tag>` while online. Do not hard-code a model from someone else's computer. Create a Python virtual environment, install `requirements.txt`, then run `python launch.py` from the project directory. Open `http://127.0.0.1:8765/`, detect and manually select the local model, import your own PDF/Markdown/TXT files, and submit one complete multiple-choice question at a time. The app and model run locally after setup. The repository does not contain user documents or model weights. See “验证安装与使用” for the synthetic smoke test and automated test command.

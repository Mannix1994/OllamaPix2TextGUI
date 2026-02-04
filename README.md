# WSL Ollama OCR 助手 🚀

**基于 WSL Ollama 的通用文本与公式 OCR 客户端**

这是一个轻量级、现代化的 Windows 桌面工具，专为连接运行在 WSL (Windows Subsystem for Linux) 或远程服务器上的 Ollama `glm-ocr` 模型而设计（也可以更换其他Ollama支持的OCR模型）。它支持截图识别、公式提取 (LaTeX)、Markdown 格式化输出以及智能重新解析。

## ✨ 功能特性

* **多模态识别**：支持纯文本、数学公式 (LaTeX)、表格及混合排版内容的精准识别。
* **无缝截图**：内置截图工具，支持多屏截图，快捷键 `Alt + A` 一键唤起。
* **自定义 Prompt**：支持多行指令，可让模型输出 Markdown、JSON 或纯文本。
* **重新解析**：对识别结果不满意？修改 Prompt 后点击“重新解析”，无需重新截图。


* **配置持久化**：自动保存 API 地址、模型名称及常用的 Prompt 指令。

---

## 🛠️ 第一步：服务端配置 (WSL)

请在 WSL2 环境 (Ubuntu) 中执行以下操作，部署 OCR 模型服务。

### 1. 安装 Ollama

安装 **0.15.5 及以上版本**。

下载地址：[Ollama GitHub Releases](https://github.com/ollama/ollama/releases)

**手动安装命令 (WSL)：**

```bash
# 下载对应的 Linux 二进制包 (例如 ollama-linux-amd64.tar.zst)
# 解压到 /usr/local
sudo tar -I zstd -xvf ollama-linux-amd64.tar.zst -C /usr/local/

# 赋予执行权限
sudo chmod 555 /usr/local/bin/ollama

```

> **提示**：建议配置代理以加速模型下载。

### 2. 启动 Ollama 服务

为了让 Windows 客户端能够访问 WSL 中的服务，必须配置监听地址和跨域策略。

```bash
# 监听所有网卡，允许 Windows 宿主机连接
export OLLAMA_HOST=0.0.0.0:11434

# 允许所有来源的 API 请求（防止跨域报错）
export OLLAMA_ORIGINS="*"

# 启动服务
ollama serve
```

### 3. 拉取 GLM-OCR 模型

https://ollama.com/library/glm-ocr

保持服务启动状态，新开一个 WSL 终端窗口执行：

```bash
ollama pull glm-ocr
```

**命令行测试（可选）：**

```bash
# 文本识别测试
ollama run glm-ocr "Text Recognition: ./image.png"
```

### 4. 其他OCR模型
* PaddleOCR-VL: https://ollama.com/MedAIBase/PaddleOCR-VL
* DeepSeek-OCR: https://ollama.com/library/deepseek-ocr

保持服务启动状态，新开一个 WSL 终端窗口执行：

```bash
ollama pull deepseek-ocr
ollama pull PaddleOCR-VL
```

## 💻 第二步：客户端安装 (Windows)

请在 Windows PowerShell 中执行以下操作。

### 1. 准备 Python 环境

本项目需要 Python 3.9 或更高版本。

```powershell
# 新建虚拟环境 (可选但推荐)
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1
```

### 2. 安装本项目

在项目根目录（即 `pyproject.toml` 所在目录）执行安装：

```powershell
# 安装当前项目及其依赖 (PyQt6, Pillow 等)
pip install .
```

---

## 📖 使用指南

### 启动客户端

安装完成后，直接在终端输入以下命令启动：

```powershell
ollama-ocr
```

### 操作流程

1. **设置连接**：
* **API URL**: 默认为 `http://{WSL_IP}:11434/api/generate`。程序启动时会自动尝试获取 WSL IP，如果失败请手动填写。
* **模型**: 填写 `glm-ocr`。


2. **设置指令 (Prompt)**：
* 推荐使用 Markdown 格式化指令：
> "Identify all text and tables in the image and output them in standard Markdown format. Formulas should be in LaTeX format."




3. **开始识别**：
* 点击 **“📷 截图识别”** 或按下热键 **`Alt + A`**。
* 框选屏幕区域，松开鼠标即可开始识别。


4. **重新解析**：
* 如果对结果格式不满意，修改 **自定义 Prompt** 内容。
* 点击 **“🔄 重新解析”** 按钮（无需重新截图，基于上次截图缓存快速生成）。



---

## 🧰 维护

### 一键清理依赖

如果需要重置环境，可以使用以下 PowerShell 命令卸载所有包：

```powershell
pip freeze | ForEach-Object { pip uninstall $_ -y }
```

---

## 📄 License

本项目采用 MIT License 开源授权。

---
name: cf-fetcher
作者: 龙骑兵
真实作者: AI龙小兵
description: 高效抓取网页内容，优先获取Markdown格式以节省Token。利用Cloudflare的AI友好模式或本地高性能转换，自动剔除冗余代码，只保留核心内容。当需要获取网页内容时，请尝试使用此技能。
---

# CF Fetcher - 高效、低成本网页内容抓取工具

此技能专为AI Agent设计，旨在以最高效率和最低Token消耗获取网页内容。它结合了Cloudflare的AI友好模式与本地高性能转换技术，确保无论目标网站是否支持，都能提供精简、语义化的Markdown内容。

## 核心功能与优势

1.  **优先 Cloudflare Markdown 转换**：
    *   在发起网页请求时，自动添加 `Accept: text/markdown` 请求头，尝试触发支持Cloudflare AI友好模式的网站直接返回Markdown格式内容。
    *   **优势**：如果成功，可大幅减少网络传输数据量，从源头节省Token。

2.  **本地高性能内容转换**：
    *   如果目标网站未返回Markdown格式（即返回HTML），技能将自动启动本地转换流程。
    *   **正则预处理**：首先通过一系列高性能正则表达式，精准剔除HTML中的“Token杀手”，如`script`、`style`、`header`、`footer`、`nav`、`aside`、`form`、`svg`、`noscript`等冗余代码和非内容元素。
    *   **`html-to-markdown` 库转换**：在预处理的基础上，利用高性能的 `html-to-markdown` 库将清洗后的HTML转换为纯净、结构化的Markdown文本。
    *   **优势**：无论Cloudflare模式是否生效，都能在本地确保大语言模型只接收到核心的、精简的内容，极大节省模型Token消耗，提高理解效率。

3.  **智能降级与超时保护**：
    *   整个抓取和转换过程内置超时机制，防止请求挂死。
    *   自动处理网页编码，避免中文乱码。

## 工作原理简述 (节省 Token 的关键)

当您请求我抓取一个网页时，`cf-fetcher` 技能将执行以下智能流程：

1.  **网络传输 (HTML 原始数据)**：请求发出，网站返回完整的HTML数据。此阶段大语言模型不参与，无Token消耗。
2.  **本地预处理 (脚本执行)**：我的Python脚本接收到HTML后，在本地执行环境中进行正则清洗和`html-to-markdown`转换。此阶段同样不调用大语言模型，无Token消耗。
3.  **大语言模型阅读 (Markdown 精简内容)**：只有经过本地精简和转换后的Markdown文本，才会被提交给我的大语言模型进行阅读和理解。由于内容已高度优化，大语言模型处理的Token数量将大大减少，从而实现显著的Token节省。

## 使用方法

当你需要获取一个网页的核心内容时，直接提供 URL 给我即可。此技能将自动选择最优策略抓取并返回最精简的Markdown格式内容。

**示例：**

`帮我看看 https://www.example.com/some-tech-article 这篇文章的主要内容`

`使用 cf-fetcher 抓取 https://www.253874.net/t/103392`

## 脚本: `scripts/fetch.py`

此技能的核心逻辑封装在 `scripts/fetch.py` 中，它负责处理 HTTP 请求的发送、高性能的正则预处理、以及`html-to-markdown`库的内容转换。

## 环境依赖

本技能依赖 `requests` 和 `html-to-markdown` Python 库。请确保运行环境中已安装：

```bash
pip install requests html-to-markdown
```
(注意：在某些受限环境中，可能需要特殊安装方式，如使用`--break-system-packages`或虚拟环境)

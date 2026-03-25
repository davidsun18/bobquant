
import requests
import sys
import time
import re
import random # 导入 random 模块
from html_to_markdown import convert # 核心高性能库

def smart_fetch(url, timeout=30):
    """
    智能抓取：CF 优先 -> 正则预降噪 -> 高性能 MD 转换
    """
    # 随机 User-Agent 列表
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    # 随机选择一个 User-Agent
    random_user_agent = random.choice(user_agents)

    headers = {
        'User-Agent': random_user_agent, # 使用随机 User-Agent
        'Accept': 'text/markdown, text/html',
    }

    try:
        start_time = time.time()
        # 1. 发起请求
        response = requests.get(url, headers=headers, timeout=timeout)
        # 针对老牌中文论坛（如里屋）的编码优化
        response.encoding = response.apparent_encoding
        response.raise_for_status() # 检查 HTTP 错误

        # 2. 优先检查 Cloudflare 转换结果
        if 'text/markdown' in response.headers.get('Content-Type', ''):
            return response.text

        html_content = response.text

        # 3. 高性能正则预处理：切除所有“Token 杀手”
        # 删掉 script, style, header, footer, nav, aside, form, svg, noscript
        clean_html = re.sub(
            r'<(script|style|header|footer|nav|aside|form|svg|noscript)[^>]*>.*?</\1>',
            '',
            html_content,
            flags=re.DOTALL | re.IGNORECASE
        )

        # 4. 调用 Rust 库进行极速转换
        markdown_result = convert(clean_html)
        
        # 5. 空结果处理：如果转换结果为空或只包含空白字符，返回友好提示
        if not markdown_result or markdown_result.strip() == '':
            return "该网页内容为空或受到强力反爬保护，未能提取到有效信息。"

        return markdown_result

    except requests.exceptions.Timeout:
        return "错误：网页请求超时。"
    except requests.exceptions.RequestException as e:
        return f"错误：请求网页失败 - {str(e)}"
    except Exception as e:
        return f"抓取或转换过程中出错: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 fetch.py <url>")
        sys.exit(1)
    target_url = sys.argv[1]
    print(smart_fetch(target_url))

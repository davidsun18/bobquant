#!/usr/bin/env python3
"""
Tavily Search API 调用脚本
用于 OpenClaw 环境中通过 exec 工具调用 Tavily 搜索

使用方法:
    python3 tavily_search.py "搜索关键词" [max_results] [search_depth]

参数:
    - query: 搜索关键词（必填）
    - max_results: 返回结果数，默认 5，最大 10（可选）
    - search_depth: basic 或 advanced，默认 basic（可选）

示例:
    python3 tavily_search.py "Python 入门教程"
    python3 tavily_search.py "AI 新闻 2026" 10 advanced
"""

import requests
import json
import sys
import os

def tavily_search(query, max_results=5, search_depth="basic", include_answer=True):
    """
    使用 Tavily API 搜索
    
    Args:
        query: 搜索关键词
        max_results: 返回结果数（1-10）
        search_depth: basic 或 advanced
        include_answer: 是否包含 AI 摘要
    
    Returns:
        dict: 搜索结果
    """
    url = "https://api.tavily.com/search"
    
    # 从环境变量或配置文件获取 API Key
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        # 尝试从 .env 文件读取
        env_file = os.path.expanduser("~/.openclaw/.env")
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith("TAVILY_API_KEY="):
                        api_key = line.strip().split("=", 1)[1]
                        break
    
    if not api_key:
        return {"error": "未找到 TAVILY_API_KEY，请配置环境变量或 ~/.openclaw/.env 文件"}
    
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": min(max_results, 10),  # 最大 10 条
        "search_depth": search_depth,
        "include_answer": include_answer,
        "include_images": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "请求超时"}
    except requests.exceptions.RequestException as e:
        return {"error": f"请求失败：{str(e)}"}
    except Exception as e:
        return {"error": f"未知错误：{str(e)}"}

def format_results(results):
    """格式化输出搜索结果"""
    if "error" in results:
        print(f"❌ 错误：{results['error']}")
        return
    
    print(f"🔍 搜索查询：{results.get('query', 'N/A')}")
    print(f"⏱️  响应时间：{results.get('response_time', 'N/A')}秒")
    print(f"📊 结果数量：{len(results.get('results', []))}\n")
    
    if results.get('answer'):
        print(f"🤖 AI 摘要：{results['answer']}\n")
    
    for i, result in enumerate(results.get('results', []), 1):
        print(f"{i}. **{result.get('title', '无标题')}**")
        print(f"   URL: {result.get('url', 'N/A')}")
        if result.get('content'):
            # 截断过长的内容
            content = result['content'][:300] + "..." if len(result['content']) > 300 else result['content']
            print(f"   摘要：{content}")
        print()

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    query = sys.argv[1]
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    search_depth = sys.argv[3] if len(sys.argv) > 3 else "basic"
    
    results = tavily_search(query, max_results, search_depth)
    format_results(results)

if __name__ == "__main__":
    main()

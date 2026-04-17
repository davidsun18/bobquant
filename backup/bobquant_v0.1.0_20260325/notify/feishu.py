# -*- coding: utf-8 -*-
"""
BobQuant 通知模块
"""
import subprocess


def send_feishu(title, message, user_id=''):
    """发送飞书通知（静默失败，不影响交易）"""
    if not user_id:
        return
    try:
        content = f"{title}\n\n{message}"
        cmd = ['message', 'send', '--target', f"user:{user_id}", '--message', content]
        subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except Exception:
        pass

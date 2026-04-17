import streamlit as st
from datetime import datetime

st.title("🚀 BobQuant 测试页面")
st.write("## 如果看到这个页面，说明 Streamlit 正常工作！")
st.write(f"**当前时间**: {datetime.now()}")
st.write(f"**服务器**: {__import__('socket').gethostname()}")

st.success("✅ Streamlit 运行正常！")
st.info("正在加载主应用...")

try:
    st.write("### 尝试导入主应用模块")
    import sys
    sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')
    from bobquant.web.streamlit_app import *
    st.write("✅ 模块导入成功")
except Exception as e:
    st.error(f"❌ 模块导入失败：{e}")
    import traceback
    st.code(traceback.format_exc())

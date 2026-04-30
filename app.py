"""
Router Agent - Streamlit 应用
统一对话入口的主程序
"""
import streamlit as st
import os
from dotenv import load_dotenv
from router import RouterAgent
from skill_loader import get_skill_loader
from skills.document_qa.skill import DocumentStore

# 加载环境变量
load_dotenv()

# 页面配置
st.set_page_config(
    page_title="Router Agent - 智能助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
<style>
    .skill-calling {
        background-color: #e3f2fd;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #2196f3;
        margin: 10px 0;
        font-weight: bold;
    }
    .stChatMessage {
        padding: 1rem;
    }
    /* 统一字体和字号 */
    .stMarkdown {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 16px;
        line-height: 1.6;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    .stMarkdown h2 {
        font-size: 20px;
        margin-top: 1.5em;
        margin-bottom: 0.5em;
    }
    .stMarkdown h3 {
        font-size: 18px;
        margin-top: 1em;
        margin-bottom: 0.5em;
    }
    .stMarkdown p {
        font-size: 16px;
        margin-bottom: 1em;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """初始化 Streamlit 会话状态"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "router" not in st.session_state:
        st.session_state.router = RouterAgent()
    if "skill_loader" not in st.session_state:
        st.session_state.skill_loader = get_skill_loader()
    # 初始化文档存储在 session_state 中，确保不会被模块重载清空
    if "document_store" not in st.session_state:
        st.session_state.document_store = DocumentStore()


def display_sidebar():
    """显示侧边栏信息和控制"""
    with st.sidebar:
        st.title("🤖 Router Agent")
        st.markdown("---")
        
        # 可用技能
        st.subheader("📦 可用技能")
        skills = st.session_state.skill_loader.get_all_skills()
        for skill_name, skill_data in skills.items():
            with st.expander(f"🔧 {skill_name}"):
                st.markdown(f"**描述:** {skill_data['description']}")
                st.markdown("**参数:**")
                for param in skill_data['parameters']:
                    st.markdown(f"- {param}")
        
        st.markdown("---")
        
        # 文档管理
        st.subheader("📚 文档管理")
        doc_store = st.session_state.document_store
        
        # 使用 session_state 跟踪已上传的文件
        if "uploaded_files" not in st.session_state:
            st.session_state.uploaded_files = set()
        
        uploaded_file = st.file_uploader("上传文档", type=['txt', 'md'], key="doc_uploader")
        if uploaded_file is not None:
            # 生成文件的唯一标识
            file_key = f"{uploaded_file.name}_{uploaded_file.size}"
            
            # 只在文件首次上传时处理
            if file_key not in st.session_state.uploaded_files:
                content = uploaded_file.read().decode('utf-8')
                doc_id = doc_store.add_document(content, uploaded_file.name)
                st.session_state.uploaded_files.add(file_key)
                st.success(f"✅ 文档已添加: {uploaded_file.name} (ID: {doc_id})")
            else:
                st.info(f"📄 文档已存在: {uploaded_file.name}")
        
        # 显示当前文档
        docs = doc_store.get_all_documents()
        if docs:
            st.markdown(f"**知识库文档数:** {len(docs)}")
            for doc in docs:
                st.markdown(f"- {doc['filename']} (ID: {doc['id']})")
        else:
            st.info("暂无上传文档")
        
        if st.button("🗑️ 清空所有文档", key="clear_docs_btn"):
            doc_store.clear()
            if "uploaded_files" in st.session_state:
                st.session_state.uploaded_files.clear()  # 同时清空上传记录
            st.success("✅ 所有文档已清空！")
            # 使用 st.rerun() 刷新页面
            st.rerun()
        
        st.markdown("---")
        
        # 清空聊天
        if st.button("🔄 清空聊天记录"):
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        st.markdown("### ℹ️ 关于")
        st.markdown("""
        Router Agent 会根据你的输入自动选择合适的技能：
        
        - 🔍 **web_search**: 搜索最新资讯
        - 📊 **stock_analysis**: 股票数据分析
        - 📚 **document_qa**: 文档问答
        - 💻 **code_generation**: 代码生成
        """)


def execute_skill(skill_name: str, params: dict):
    """执行技能并流式输出结果"""
    try:
        # 导入技能模块
        skill_module = st.session_state.skill_loader.import_skill_module(skill_name)
        
        # 如果是 document_qa skill，传入 document_store
        if skill_name == "document_qa":
            params["document_store"] = st.session_state.document_store
        
        # 执行技能的 run 函数
        if hasattr(skill_module, 'run'):
            yield from skill_module.run(params)
        else:
            yield f"❌ 错误: 技能 '{skill_name}' 没有 'run' 函数\n"
    
    except Exception as e:
        yield f"❌ 执行技能 '{skill_name}' 时出错: {str(e)}\n"


def process_user_input(user_input: str):
    """通过路由器处理用户输入并执行相应技能"""
    # 添加用户消息到聊天
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # 获取路由决策
    with st.chat_message("assistant"):
        # 显示路由决策
        with st.spinner("🤔 正在分析你的请求..."):
            routing_result = st.session_state.router.route(user_input)
        
        skill_name = routing_result.get("skill")
        params = routing_result.get("params", {})
        reasoning = routing_result.get("reasoning", "")
        
        # 显示正在调用的技能
        if skill_name != "none":
            st.markdown(f'<div class="skill-calling">🔧 正在调用: <code>{skill_name}</code></div>', unsafe_allow_html=True)
            
            # 使用可折叠组件显示推理过程
            with st.expander("💭 查看推理过程"):
                st.markdown(f"**模型:** `{st.session_state.router.model}`\n\n")
                st.markdown(f"**推理:** {reasoning}")
            
            # 执行技能并流式输出结果到临时变量
            full_response = ""
            for chunk in execute_skill(skill_name, params):
                full_response += chunk
            
            # 将结果放在可折叠的气泡中（在横线上方）
            with st.expander("📄 查看完整结果", expanded=True):
                st.markdown(full_response)
            
            st.markdown("---")
            
            # 保存助手响应
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response,
                "skill": skill_name,
                "reasoning": reasoning
            })
        
        else:
            # 没有匹配的技能 - 使用直接响应
            st.info(f"💭 {reasoning}")
            
            if "direct_response" in routing_result:
                direct_response = routing_result["direct_response"]
                st.markdown(direct_response)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": direct_response,
                    "skill": "none",
                    "reasoning": reasoning
                })
            else:
                fallback_msg = "我无法确定使用哪个技能来处理你的请求。请尝试重新表述，或询问以下内容：\n- 最新资讯/信息\n- 股票分析\n- 文档问题\n- 代码生成"
                st.markdown(fallback_msg)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": fallback_msg,
                    "skill": "none",
                    "reasoning": reasoning
                })


def main():
    """主应用程序"""
    # 初始化
    initialize_session_state()
    
    # 显示侧边栏
    display_sidebar()
    
    # 主聊天界面
    st.title("💬 Router Agent 聊天")
    st.markdown("问我任何问题！我会自动选择合适的技能来帮助你。")
    
    # 显示聊天历史
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "skill" in message:
                if message["skill"] != "none":
                    st.markdown(f'<div class="skill-calling">🔧 已调用: <code>{message["skill"]}</code></div>', unsafe_allow_html=True)
                    if "reasoning" in message:
                        # 使用可折叠组件显示推理过程
                        with st.expander("💭 查看推理过程"):
                            st.markdown(f"**模型:** `{st.session_state.router.model}`\n\n")
                            st.markdown(f"**推理:** {message['reasoning']}")
                    # 将结果放在可折叠的气泡中（在横线上方）
                    with st.expander("📄 查看完整结果", expanded=True):
                        st.markdown(message["content"])
                    st.markdown("---")
                else:
                    st.markdown(message["content"])
            else:
                st.markdown(message["content"])
    
    # 聊天输入
    if prompt := st.chat_input("你想了解什么？"):
        process_user_input(prompt)


if __name__ == "__main__":
    # 检查必需的环境变量
    if not os.getenv("GROQ_API_KEY"):
        st.error("❌ 未设置 GROQ_API_KEY 环境变量！")
        st.info("请在 .env 文件或环境变量中设置你的 GROQ_API_KEY。")
        st.stop()
    
    if not os.getenv("TAVILY_API_KEY"):
        st.warning("⚠️ 未设置 TAVILY_API_KEY。网络搜索功能将无法使用。")
    
    main()

# Made with Bob

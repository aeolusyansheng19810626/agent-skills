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
import pipeline

# 加载环境变量
load_dotenv()

# 页面配置
st.set_page_config(
    page_title="Router Agent - 智能助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Tokens & Styles
styles_css = """
/* ====== Tokens ====== */
:root {
  --bg:        #F7F7FB;
  --bg-2:      #EFEFF5;
  --surface:   #FFFFFF;
  --line:      #E8E8F0;
  --line-2:    #DEDEE8;
  --line-3:    #C9C9D6;
  --sidebar-bg:#F8F5FF;
  --fg:        #0F0F1A;
  --fg-2:      #2E2E40;
  --fg-3:      #5E5E73;
  --fg-4:      #9494A8;
  --brand:     #4338CA;
  --brand-2:   #6D28D9;
  --brand-3:   #8B5CF6;
  --brand-4:   #A78BFA;
  --accent:    #7C3AED;
  --accent-2:  #5B21B6;
  --electric:  #6366F1;
  --brand-50:  #F3F0FF;
  --brand-100: #E5DEFF;
  --brand-200: #C9BCFF;
  --brand-300: #A78BFA;
  --grad-1: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #A855F7 100%);
  --grad-2: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
  --grad-aurora: linear-gradient(120deg, #4338CA 0%, #5B21B6 30%, #6D28D9 55%, #7C3AED 80%, #8B5CF6 100%);
  --grad-soft: linear-gradient(135deg, #F3F0FF 0%, #FAF5FF 100%);
  --green:     #10B981;
  --green-50:  #ECFDF5;
  --amber:     #F59E0B;
  --amber-50:  #FFFBEB;
  --rose:      #F43F5E;
  --rose-50:   #FFF1F2;
  --r-sm: 6px;
  --r-md: 10px;
  --r-lg: 14px;
  --r-xl: 18px;
  --shadow-sm: 0 1px 2px rgba(24,24,27,.04), 0 0 0 1px rgba(24,24,27,.04);
  --shadow-md: 0 4px 16px rgba(24,24,27,.06), 0 0 0 1px rgba(24,24,27,.05);
  --shadow-lg: 0 16px 40px rgba(24,24,27,.08), 0 0 0 1px rgba(24,24,27,.05);
}
* { box-sizing: border-box; }
body {
  font-family: "Inter","Noto Sans SC",-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  font-size: 14px; color: var(--fg); background: var(--bg);
  -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
}
button { font-family: inherit; cursor: pointer; }
input, textarea, select { font-family: inherit; font-size: inherit; color: inherit; }
.brand-title {
  font-size: 15px; font-weight: 700;
  background: var(--grad-aurora);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: .01em;
  white-space: nowrap;
}
.brand-sub { font-size: 11px; color: var(--fg-4); margin-top: 2px; letter-spacing: .04em; text-transform: uppercase; white-space: nowrap; }
.side-label { font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--fg-4); display: flex; align-items: center; gap: 8px; }
.foot-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); box-shadow: 0 0 0 3px var(--green-50); }
.count-pill { display: inline-flex; align-items: center; justify-content: center; min-width: 18px; height: 18px; padding: 0 5px; background: var(--bg-2); color: var(--fg-3); font-size: 10.5px; font-weight: 600; border-radius: 999px; border: 1px solid var(--line-2); }
.page-title { color: #fff !important; font-size: 15px; margin: 0; }
.page-sub { color: rgba(255,255,255,.82) !important; font-size: 11.5px; margin-top: 1px; }
.status { background: rgba(255,255,255,.18) !important; border-color: rgba(255,255,255,.3) !important; color: #fff !important; backdrop-filter: blur(8px); padding: 4px 10px !important; font-size: 11px !important; }
.status-dot { background: #fff !important; box-shadow: 0 0 0 3px rgba(255,255,255,.25), 0 0 12px rgba(255,255,255,.6) !important; }

.skill-calling {
    background-color: #e3f2fd;
    padding: 10px;
    border-radius: 5px;
    border-left: 4px solid #2196f3;
    margin: 0 0 10px 0;
    font-weight: bold;
}
[data-testid="stChatMessage"]:has(.msg-assistant) [data-testid="stExpander"]:last-of-type {
    margin-bottom: 0 !important;
}

.msg-hook { display: none !important; }

/* st.success / st.info 图标垂直居中 */
[data-testid="stAlert"] {
    align-items: center !important;
}
[data-testid="stAlert"] [data-testid="stAlertContentIcon"] {
    margin-top: 0 !important;
    padding-top: 0 !important;
    align-self: center !important;
}

/* 文档列表删除按钮 — 紧凑小图标 */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:last-child button {
    padding: 0 4px !important;
    min-height: 24px !important;
    height: 24px !important;
    font-size: 14px !important;
    border-radius: 4px !important;
    margin-top: 2px !important;
}
"""

streamlit_overrides = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap');
html, body, [class*="css"], .stApp {
  font-family: "Inter","Noto Sans SC",-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif !important;
}
[data-testid="stApp"], .stApp { background: var(--bg) !important; }

/* 隐藏 Streamlit 顶部菜单/页脚 */
#MainMenu, footer { visibility: hidden; height: 0; }
header[data-testid="stHeader"] { height: 0 !important; min-height: 0 !important; background: transparent !important; box-shadow: none !important; overflow: visible !important; }
.stAppDeployButton { display: none !important; }

/* 侧边栏展开按钮 */
[data-testid="stSidebarExpandButton"],
[data-testid="stSidebarCollapseButton"] {
  z-index: 9999999 !important;
  color: #0F0F1A !important;
  background-color: rgba(255, 255, 255, 0.8) !important;
  border-radius: 50% !important;
  box-shadow: 0 2px 10px rgba(0,0,0,0.2) !important;
  margin-top: 8px !important;
  margin-left: 8px !important;
}
[data-testid="stSidebarExpandButton"]:hover,
[data-testid="stSidebarCollapseButton"]:hover {
  background-color: white !important;
}
[data-testid="stSidebarCollapsedControl"] {
  z-index: 9999998 !important;
}

/* 主区域边距 */
.block-container {
  padding-top: 64px !important;
  padding-bottom: 120px !important;
  padding-left: 32px !important;
  padding-right: 32px !important;
  max-width: 100% !important;
  margin: 0 !important;
}

/* ================= Sidebar ================= */
section[data-testid="stSidebar"][aria-expanded="true"] {
  background: var(--sidebar-bg) !important;
  border-right: 1px solid var(--line);
  width: 300px !important;
  min-width: 300px !important;
}
.brand {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 300px !important;
  height: 60px !important;
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  padding: 0 1.5rem !important;
  border-bottom: 1px solid var(--line) !important;
  background: var(--sidebar-bg) !important;
  box-sizing: border-box !important;
  z-index: 1000 !important;
  margin: 0 !important;
}
.brand-text {
  display: flex !important;
  flex-direction: column !important;
  white-space: nowrap !important;
}

section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
  align-items: center !important;
}
section[data-testid="stSidebar"] [data-testid="column"] {
  margin: 0 !important;
}
section[data-testid="stSidebar"] [data-testid="column"] > div {
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  height: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
}
section[data-testid="stSidebar"] [data-testid="column"] [data-testid="stVerticalBlock"] {
  gap: 0 !important;
  padding: 0 !important;
}
section[data-testid="stSidebar"] .stButton,
section[data-testid="stSidebar"] .stMarkdown {
  margin-bottom: 0 !important;
  margin-top: 0 !important;
  padding: 0 !important;
}
section[data-testid="stSidebar"] [data-testid="column"] [data-testid="stMarkdownContainer"] {
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1 !important;
  height: 38px !important;
}
section[data-testid="stSidebar"] [data-testid="column"] [data-testid="stMarkdownContainer"] p {
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1 !important;
  height: 38px !important;
  display: flex !important;
  align-items: center !important;
}
section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p {
  margin-bottom: 0 !important;
}

section[data-testid="stSidebar"] .stButton {
  display: flex;
  justify-content: flex-end;
}
section[data-testid="stSidebar"] button[kind="secondary"],
section[data-testid="stSidebar"] button[data-testid="baseButton-secondary"] {
  background: linear-gradient(135deg, var(--brand-50), var(--brand-100)) !important;
  border: 1px solid var(--brand-200) !important;
  border-radius: 8px !important;
  color: var(--accent-2) !important;
  padding: 10px 12px !important;
  height: auto !important;
  min-height: 36px !important;
  font-size: 13.5px !important;
  transition: all 0.2s ease !important;
}
section[data-testid="stSidebar"] button[kind="secondary"] p,
section[data-testid="stSidebar"] button[data-testid="baseButton-secondary"] p {
  font-size: 13.5px !important;
}
section[data-testid="stSidebar"] button[kind="secondary"]:hover,
section[data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:hover {
  background: linear-gradient(135deg, var(--brand-100), var(--brand-200)) !important;
  color: var(--accent) !important;
  border-color: var(--accent) !important;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.2) !important;
  transform: translateY(-2px);
}

section[data-testid="stSidebar"] [data-baseweb="input"] > div,
section[data-testid="stSidebar"] [data-baseweb="textarea"] > div,
section[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: var(--surface) !important;
  border: 1px solid var(--line-2) !important;
  border-radius: var(--r-sm) !important;
  font-size: 11px !important;
  color: var(--fg) !important;
  box-shadow: none !important;
  min-height: 34px !important;
}
section[data-testid="stSidebar"] [data-baseweb="input"] > div:focus-within,
section[data-testid="stSidebar"] [data-baseweb="textarea"] > div:focus-within,
section[data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {
  border-color: var(--brand-3) !important;
  box-shadow: 0 0 0 3px var(--brand-50) !important;
}
[data-baseweb="select"] input {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
}
section[data-testid="stSidebar"] label {
  font-size: 11px !important; color: var(--fg-3) !important; font-weight: 500 !important;
  margin-bottom: 4px !important;
}

section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  width: 100%;
  background: var(--grad-1) !important;
  background-size: 150% 150% !important;
  color: #fff !important;
  border: 0 !important;
  border-radius: var(--r-sm) !important;
  height: 38px !important;
  min-height: 38px !important;
  margin: 0 !important;
  font-weight: 500 !important;
  font-size: 13px !important;
  padding: 0 4px !important;
  white-space: nowrap !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-shadow: 0 6px 16px rgba(124,58,237,.28), inset 0 1px 0 rgba(255,255,255,.18) !important;
  transition: background-position .3s, transform .05s, box-shadow .2s !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] p {
  font-size: 13px !important;
  white-space: nowrap !important;
  margin: 0 !important;
  line-height: 1 !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
  background-position: 100% 0 !important;
  box-shadow: 0 10px 22px rgba(124,58,237,.35) !important;
}

/* 侧边栏 alert 组件完美对齐 */
section[data-testid="stSidebar"] [data-testid="stAlert"] {
  font-size: 13px !important;
  height: 38px !important;
  min-height: 38px !important;
  margin: 0 !important;
  padding: 0 12px !important;
  white-space: nowrap !important;
  display: flex !important;
  align-items: center !important;
}
section[data-testid="stSidebar"] [data-testid="stAlert"] * { font-size: 13px !important; white-space: nowrap !important; margin: 0 !important; }
section[data-testid="stSidebar"] [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
  line-height: 1 !important;
  margin: 0 !important;
}
section[data-testid="stSidebar"] [data-testid="stAlert"] div { font-size: 13px !important; }
section[data-testid="stSidebar"] [data-testid="stAlert"] span { font-size: 13px !important; }
section[data-testid="stSidebar"] .stAlert { font-size: 13px !important; }
section[data-testid="stSidebar"] .stAlert * { font-size: 13px !important; }
section[data-testid="stSidebar"] .stAlert > * { font-size: 13px !important; }

/* ================= 文件上传组件 File Uploader ================= */
section[data-testid="stSidebar"] [data-testid="stFileUploader"] label {
  display: none !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] section {
  background: var(--bg-2) !important;
  border: 2px dashed var(--line-3) !important;
  border-radius: var(--r-md) !important;
  padding: 24px 12px !important;
  transition: background .15s, border-color .15s;
}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] section:hover {
  background: var(--brand-50) !important;
  border-color: var(--brand-200) !important;
}

/* Override File Uploader Inner Text */
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] div,
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] svg {
  display: none !important;
}
[data-testid="stFileUploaderDropzone"]::before {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--fg);
  margin-top: 8px;
  margin-bottom: 4px;
  text-align: center;
  padding-top: 48px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='42' fill='none' viewBox='0 0 40 42'%3E%3Crect width='36' height='36' x='2' y='4' fill='%23000000' fill-opacity='0.05' rx='10'/%3E%3Crect width='36' height='36' x='2' y='2' fill='%23ffffff' rx='10' stroke='%23E5E7EB' stroke-width='1'/%3E%3Cpath stroke='%234B5563' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.8' d='M20 22V12m0 0l-4 4m4-4l4 4M14 25v1.5a1.5 1.5 0 0 0 1.5 1.5h9a1.5 1.5 0 0 0 1.5-1.5V25'/%3E%3C/svg%3E");
  background-position: center top;
  background-repeat: no-repeat;
}
[data-testid="stFileUploaderDropzone"]::after {
  display: block;
  font-size: 11px;
  color: var(--fg-4);
  text-align: center;
}

/* 侧边栏 Expander (卡片) 组件字号 */
section[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary span,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary div {
  font-size: 13.5px !important;
  font-weight: 600 !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stText"],
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] li,
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] span,
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] strong {
  font-size: 13px !important;
  line-height: 1.6 !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] code {
  font-size: 12px !important;
}

section[data-testid="stSidebar"] [data-testid="stExpander"] > details {
  background: linear-gradient(135deg, var(--brand-50), var(--brand-100)) !important;
  border: 1px solid var(--brand-200) !important;
  border-radius: 8px !important;
  padding: 8px 10px !important;
  margin-bottom: 6px !important;
}

section[data-testid="stSidebar"] [data-testid="stExpander"] > details summary {
  color: var(--accent-2) !important;
  cursor: pointer !important;
}

/* ================= 主区顶部 Topbar ================= */
.topbar-wrapper {
  width: 100% !important;
  height: 60px !important;
}
.topbar-wrapper .topbar {
  position: fixed !important;
  top: 0 !important;
  left: 300px !important;
  right: 0 !important;
  height: 60px !important;
  padding: 0 32px !important;
  z-index: 1000 !important;
  background: var(--grad-aurora) !important;
  display: flex !important;
  justify-content: space-between !important;
  align-items: center !important;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1) !important;
}
@media (max-width: 768px) {
  .topbar-wrapper .topbar { left: 0 !important; }
}
[data-testid="stSidebar"][aria-expanded="false"] ~ div .topbar-wrapper .topbar {
  left: 0 !important;
}
[data-testid="stSidebar"][aria-expanded="false"] .brand {
  transform: translateX(-300px) !important;
  opacity: 0 !important;
}

.topbar-left { display: flex; flex-direction: column; }
.topbar-right { display: flex !important; align-items: center !important; gap: 12px !important; padding-right: 80px !important; }
.status { display: inline-flex !important; align-items: center !important; gap: 6px !important; padding: 6px 12px !important; border: 1px solid rgba(255,255,255,.3) !important; border-radius: 999px !important; color: white !important; font-size: 11px !important; white-space: nowrap !important; }
.status-dot { display: inline-flex !important; width: 6px !important; height: 6px !important; border-radius: 50% !important; background: white !important; flex-shrink: 0 !important; }

/* ================= 语言切换器 ================= */
div[data-testid="stPopover"] {
  position: fixed !important;
  top: 16px !important;
  right: 32px !important;
  left: auto !important;
  width: auto !important;
  z-index: 1001 !important;
}
div[data-testid="stPopover"] button {
  display: inline-flex !important; align-items: center !important; gap: 6px !important;
  height: 28px !important; padding: 0 8px 0 9px !important;
  background: rgba(255,255,255,.18) !important;
  border: 1px solid rgba(255,255,255,.3) !important;
  border-radius: 999px !important;
  color: white !important;
  font-size: 11.5px !important; font-weight: 500 !important;
  backdrop-filter: blur(8px) !important;
  min-height: 28px !important;
  box-shadow: none !important;
  transition: background .15s, border-color .15s;
}
div[data-testid="stPopover"] button:hover {
  background: rgba(255,255,255,.28) !important;
  border-color: rgba(255,255,255,.45) !important;
}
div[data-testid="stPopover"] button p {
  font-size: 11.5px !important; font-weight: 500 !important; margin: 0 !important;
  font-variant-numeric: tabular-nums; letter-spacing: .02em; min-width: 14px; text-align: center;
}
div[data-testid="stPopoverBody"] {
  min-width: 172px !important;
  max-width: 210px !important;
  background: #fff !important;
  border: 1px solid var(--line) !important;
  border-radius: 10px !important;
  box-shadow: 0 16px 40px rgba(15,15,26,.18), 0 2px 6px rgba(15,15,26,.08) !important;
  padding: 0 !important;
  overflow: hidden !important;
}
div[data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] {
  gap: 2px !important; padding: 4px !important;
}
.lang-hdr {
  font-size: 12.5px !important; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; color: var(--fg-4);
  white-space: nowrap;
  padding: 8px 12px 6px; margin: 0;
  border-bottom: 1px solid var(--line);
}
div[data-testid="stPopoverBody"] [data-testid="stMarkdownContainer"]:has(.lang-hdr) {
  margin: 0 -4px !important; padding: 0 !important;
}
div[data-testid="stPopoverBody"] button {
  display: flex !important; align-items: center !important; gap: 8px !important;
  width: 100% !important; padding: 7px 10px !important;
  background: transparent !important; border: 0 !important; border-radius: 6px !important;
  color: var(--fg) !important; font-size: 12.5px !important; justify-content: flex-start !important;
  min-height: 0 !important; height: auto !important;
  text-align: left !important;
}
div[data-testid="stPopoverBody"] button:hover { background: var(--bg-2) !important; color: var(--fg) !important; border-color: transparent !important; }
div[data-testid="stPopoverBody"] [data-testid="baseButton-primary"],
div[data-testid="stPopoverBody"] button[kind="primary"] {
  background: var(--brand-50) !important;
  color: var(--accent) !important;
  font-weight: 600 !important;
}
div[data-testid="stPopoverBody"] [data-testid="baseButton-primary"]:hover,
div[data-testid="stPopoverBody"] button[kind="primary"]:hover {
  background: var(--brand-100) !important;
}
div[data-testid="stPopoverBody"] button p { margin: 0 !important; width: 100%; font-size: 12.5px !important; }

/* ================= 对话气泡 ================= */
[data-testid="stChatMessage"] {
  background: transparent !important;
  padding: 0 !important;
  margin-bottom: 24px !important;
  display: flex !important;
  width: 100% !important;
  gap: 16px !important;
  align-items: flex-start !important;
}

/* User Message */
[data-testid="stChatMessage"]:has(.msg-user) {
  flex-direction: row-reverse !important;
  justify-content: flex-start !important;
  align-items: center !important;
}
[data-testid="stChatMessage"]:has(.msg-user) [data-testid="stChatMessageContent"] {
  background: linear-gradient(135deg, #4F46E5, #7C3AED, #A855F7) !important;
  color: #fff !important;
  border-radius: 14px !important;
  border-top-right-radius: 4px !important;
  padding: 14px 18px !important;
  max-width: 75% !important;
  width: fit-content !important;
  flex: none !important;
  box-shadow: 0 10px 28px rgba(124,58,237,.32) !important;
  border: none !important;
  margin-left: auto !important;
  margin-right: 0 !important;
  align-self: center !important;
}
[data-testid="stChatMessage"]:has(.msg-user) [data-testid="stChatMessageContent"] p { color: #fff !important; margin: 0 !important;}
[data-testid="stChatMessage"]:has(.msg-user) [data-testid="stChatMessageContent"] [data-testid="stVerticalBlock"] {
  gap: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
}
[data-testid="stChatMessage"]:has(.msg-user) [data-testid="stChatMessageContent"] [data-testid="stMarkdownContainer"],
[data-testid="stChatMessage"]:has(.msg-user) [data-testid="stChatMessageContent"] .stMarkdown {
  margin: 0 !important;
  padding: 0 !important;
}

/* Assistant Message */
[data-testid="stChatMessage"]:has(.msg-assistant) {
  justify-content: flex-start !important;
}
[data-testid="stChatMessage"]:has(.msg-assistant) [data-testid="stChatMessageContent"] {
  background: #FFFFFF !important;
  border: 1px solid #E8E8F0 !important;
  border-radius: 14px !important;
  border-top-left-radius: 4px !important;
  padding: 16px 20px !important;
  box-shadow: 0 4px 16px rgba(0,0,0,0.04) !important;
  position: relative !important;
  overflow: visible !important;
  flex: 1 !important;
}
[data-testid="stChatMessage"]:has(.msg-assistant) [data-testid="stChatMessageContent"]::before {
  content: "" !important;
  position: absolute !important;
  left: -1px !important; top: -1px !important; bottom: -1px !important; width: 4px !important;
  background: linear-gradient(180deg, #4F46E5, #7C3AED, #A855F7) !important;
  border-radius: 14px 0 0 4px !important;
}

/* Avatars */
[data-testid="stChatMessage"] > div:first-child {
  width: 36px !important; height: 36px !important; min-width: 36px !important;
  display: flex !important; align-items: center !important; justify-content: center !important;
  color: transparent !important;
  border-radius: 10px !important;
  overflow: hidden !important;
}
[data-testid="stChatMessage"] > div:first-child * {
  display: none !important;
}

[data-testid="stChatMessage"]:has(.msg-user) > div:first-child {
  align-self: center !important;
  margin-top: auto !important;
  margin-bottom: auto !important;
  background-color: #F3F4F6 !important;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%234B5563'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z'/%3E%3C/svg%3E") !important;
  background-size: 20px !important; background-position: center !important; background-repeat: no-repeat !important;
  border: 1px solid #E5E7EB !important;
}

[data-testid="stChatMessage"]:has(.msg-assistant) > div:first-child {
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z'/%3E%3C/svg%3E") center / 20px no-repeat, linear-gradient(135deg, #8B5CF6, #7C3AED) !important;
  border: none !important;
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.4) !important;
}

/* ================= Chat Input ================= */
[data-testid="stChatInput"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}
/* Move border/radius to inner flex row so overflow:hidden clips the abs-positioned button */
[data-testid="stChatInput"] > div {
  background: var(--surface) !important;
  border: 1px solid var(--line-2) !important;
  border-radius: 16px !important;
  box-shadow: 0 12px 32px rgba(124,58,237,.08), 0 0 0 1px rgba(124,58,237,.04) !important;
  padding: 4px 6px 4px 12px !important;
  position: relative !important;
  overflow: hidden !important;
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
  margin: 0 !important;
}
[data-testid="stChatInput"] textarea {
  font-size: 14px !important;
  color: var(--fg) !important;
  padding: 8px 0 !important;
}
/* Chat submit button - circle, sits at right edge inside the container */
[data-testid="stChatInputSubmitButton"],
[data-testid="stChatInputSubmitButton"] button {
  background: linear-gradient(135deg, #4F46E5, #7C3AED) !important;
  border-radius: 50% !important;
  border: none !important;
  width: 36px !important; height: 36px !important;
  min-width: 36px !important; min-height: 36px !important;
  max-width: 36px !important; max-height: 36px !important;
  padding: 0 !important;
  display: flex !important; align-items: center !important; justify-content: center !important;
  cursor: pointer !important;
  flex-shrink: 0 !important;
  align-self: center !important;
}
[data-testid="stChatInputSubmitButton"] svg { fill: white !important; width: 16px !important; height: 16px !important; }
"""

# 多语言翻译 - 必须在 get_dynamic_css() 调用之前定义
i18n = {
    "zh": {
        "brand_title": "路由智能体",
        "brand_sub": "技能路由器",
        "available_skills": "可用技能",
        "document_management": "文档管理",
        "about": "关于",
        "code_generation": "代码生成",
        "document_qa": "文档问答",
        "stock_analysis": "股票分析",
        "web_search": "网络搜索",
        "description": "描述",
        "parameters": "参数",
        "clear_all_docs": "🗑️ 清空所有文档",
        "clear_chat": "🔄 清空聊天记录",
        "knowledge_base_docs": "知识库文档数",
        "no_docs": "暂无上传文档",
        "doc_added": "✅ 文档已添加",
        "doc_exists": "📄 文档已存在",
        "all_docs_cleared": "✅ 所有文档已清空！",
        "topbar_title": "路由智能体 · 智能技能路由",
        "topbar_sub": "自动路由至合适的技能：搜索 · 股票 · 文档 · 代码",
        "skills_loaded": "已加载",
        "skill_text": "个技能",
        "analyzing": "🤔 正在分析你的请求...",
        "calling": "正在调用",
        "pipeline": "Pipeline",
        "view_reasoning": "💭 查看推理过程",
        "model": "模型",
        "reasoning": "推理",
        "view_full_result": "📄 查看完整结果",
        "no_skill_match": "我无法确定使用哪个技能来处理你的请求。请尝试重新表述，或询问以下内容：\n- 最新资讯/信息\n- 股票分析\n- 文档问题\n- 代码生成",
        "chat_placeholder": "你想了解什么？输入任意问题...",
        "drag_to_upload": "拖拽或点击上传",
        "upload_hint": "TXT, MD · 单文件 ≤ 200MB",
        "code_generation_desc": "根据用户需求生成代码，支持多种编程语言。",
        "code_generation_requirement": "需求描述",
        "code_generation_language": "编程语言（默认 Python）",
        "document_qa_desc": "在已上传的文档知识库中检索并回答问题。",
        "document_qa_query": "问题",
        "stock_analysis_desc": "获取股票数据并进行技术面、新闻面分析，生成分析报告。",
        "stock_analysis_ticker": "股票代码",
        "web_search_desc": "搜索互联网获取最新信息，适用于需要实时数据、新闻、时事的问题。",
        "web_search_query": "搜索关键词",
        "delete_doc": "删除",
        "doc_deleted": "✅ 文档已删除",
    },
    "ja": {
        "brand_title": "Router Agent",
        "brand_sub": "ｽｷﾙﾙｰﾀｰ",
        "available_skills": "利用可能ｽｷﾙ",
        "document_management": "文書管理",
        "about": "について",
        "code_generation": "ｺｰﾄﾞ生成",
        "document_qa": "ﾄﾞｷｭﾒﾝﾄ Q&A",
        "stock_analysis": "株式分析",
        "web_search": "ｳｪﾌﾞ検索",
        "description": "説明",
        "parameters": "ﾊﾟﾗﾒｰﾀｰ",
        "clear_all_docs": "🗑️ すべてのﾄﾞｷｭﾒﾝﾄをｸﾘｱ",
        "clear_chat": "🔄 ﾁｬｯﾄ履歴をｸﾘｱ",
        "knowledge_base_docs": "ﾅﾚｯｼﾞﾍﾞｰｽ文書数",
        "no_docs": "ｱｯﾌﾟﾛｰﾄﾞされたﾄﾞｷｭﾒﾝﾄがありません",
        "doc_added": "✅ ﾄﾞｷｭﾒﾝﾄが追加されました",
        "doc_exists": "📄 ﾄﾞｷｭﾒﾝﾄは既に存在します",
        "all_docs_cleared": "✅ すべてのﾄﾞｷｭﾒﾝﾄがｸﾘｱされました！",
        "topbar_title": "Router Agent・ｽｷﾙﾙｰﾃｨﾝｸﾞ",
        "topbar_sub": "適切なｽｷﾙへ自動ﾙｰﾃｨﾝｸﾞ：検索·株式·文書·ｺｰﾄﾞ",
        "skills_loaded": "ﾛｰﾄﾞ済",
        "skill_text": "ｽｷﾙ",
        "analyzing": "🤔 ﾘｸｴｽﾄを分析しています...",
        "calling": "呼び出し中",
        "pipeline": "ﾊﾟｲﾌﾟﾗｲﾝ",
        "view_reasoning": "💭 推論を表示",
        "model": "ﾓﾃﾞﾙ",
        "reasoning": "推論",
        "view_full_result": "📄 完全な結果を表示",
        "no_skill_match": "ﾘｸｴｽﾄを処理するｽｷﾙを決定できません。言い直すか、次のいずれかをお問い合わせください：\n- 最新のﾆｭｰｽ/情報\n- 株式分析\n- ﾄﾞｷｭﾒﾝﾄの質問\n- ｺｰﾄﾞ生成",
        "chat_placeholder": "何を知りたいですか？質問を入力してください...",
        "drag_to_upload": "ﾄﾞﾗｯｸﾞまたはｸﾘｯｸしてｱｯﾌﾟﾛｰﾄﾞ",
        "upload_hint": "TXT、MD · 単一ﾌｧｲﾙ ≤ 200MB",
        "code_generation_desc": "ﾕｰｻﾞｰの要求に応じてｺｰﾄﾞを生成し、複数のﾌﾟﾛｸﾞﾗﾐﾝｸﾞ言語をｻﾎﾟｰﾄします。",
        "code_generation_requirement": "要件説明",
        "code_generation_language": "ﾌﾟﾛｸﾞﾗﾐﾝｸﾞ言語（ﾃﾌｫﾙﾄ Python）",
        "document_qa_desc": "ｱｯﾌﾟﾛｰﾄﾞされたﾄﾞｷｭﾒﾝﾄﾅﾚｯｼﾞﾍﾞｰｽで検索して質問に答えます。",
        "document_qa_query": "質問",
        "stock_analysis_desc": "ｽﾄｯｸﾃﾞｰﾀを取得し、技術的および新聞面分析を実施して、分析ﾚﾎﾟｰﾄを生成します。",
        "stock_analysis_ticker": "ｽﾄｯｸｺｰﾄﾞ",
        "web_search_desc": "ｲﾝﾀｰﾈｯﾄを検索してｺﾞ最新情報を取得し、ﾘｱﾙﾀｲﾑﾃﾞｰﾀ、ﾆｭｰｽ、時事ｲﾝﾌｫﾒｰｼｮﾝが必要な質問に適しています。",
        "web_search_query": "検索ｷｰﾜｰﾄﾞ",
        "delete_doc": "削除",
        "doc_deleted": "✅ ﾄﾞｷｭﾒﾝﾄが削除されました",
    },
    "en": {
        "brand_title": "Router Agent",
        "brand_sub": "SKILL ROUTER",
        "available_skills": "Available Skills",
        "document_management": "Document Management",
        "about": "About",
        "code_generation": "Code Generation",
        "document_qa": "Document Q&A",
        "stock_analysis": "Stock Analysis",
        "web_search": "Web Search",
        "description": "Description",
        "parameters": "Parameters",
        "clear_all_docs": "🗑️ Clear All Documents",
        "clear_chat": "🔄 Clear Chat History",
        "knowledge_base_docs": "Knowledge Base Documents",
        "no_docs": "No documents uploaded",
        "doc_added": "✅ Document added",
        "doc_exists": "📄 Document already exists",
        "all_docs_cleared": "✅ All documents cleared!",
        "topbar_title": "Router Agent · Intelligent Skill Routing",
        "topbar_sub": "Auto-route to appropriate skills: Search · Stock · Document · Code",
        "skills_loaded": "Loaded",
        "skill_text": "skills",
        "analyzing": "🤔 Analyzing your request...",
        "calling": "Calling",
        "pipeline": "Pipeline",
        "view_reasoning": "💭 View Reasoning",
        "model": "Model",
        "reasoning": "Reasoning",
        "view_full_result": "📄 View Full Result",
        "no_skill_match": "I cannot determine which skill to use for your request. Please try rephrasing, or ask about:\n- Latest news/information\n- Stock analysis\n- Document questions\n- Code generation",
        "chat_placeholder": "What would you like to know? Enter any question...",
        "drag_to_upload": "Drag or click to upload",
        "upload_hint": "TXT, MD · Single file ≤ 200MB",
        "code_generation_desc": "Generate code based on user requirements, supporting multiple programming languages.",
        "code_generation_requirement": "Requirement description",
        "code_generation_language": "Programming language (default Python)",
        "document_qa_desc": "Retrieve and answer questions from uploaded document knowledge base.",
        "document_qa_query": "Question",
        "stock_analysis_desc": "Fetch stock data and perform technical and news analysis, generating analysis reports.",
        "stock_analysis_ticker": "Stock ticker",
        "web_search_desc": "Search the internet to obtain the latest information, suitable for questions requiring real-time data, news, and current events.",
        "web_search_query": "Search keywords",
        "delete_doc": "Delete",
        "doc_deleted": "✅ Document deleted",
    }
}

def t(key):
    """获取当前语言的翻译"""
    lang = st.session_state.lang
    return i18n.get(lang, i18n["zh"]).get(key, key)


def get_dynamic_css():
    """根据当前语言生成动态CSS"""
    if "lang" not in st.session_state:
        lang = "zh"
    else:
        lang = st.session_state.lang

    drag_text = i18n.get(lang, i18n["zh"]).get("drag_to_upload", "拖拽或点击上传")
    hint_text = i18n.get(lang, i18n["zh"]).get("upload_hint", "TXT, MD · 单文件 ≤ 200MB")

    return f"""
  [data-testid="stFileUploaderDropzone"]::before {{
    content: "{drag_text}";
  }}
  [data-testid="stFileUploaderDropzone"]::after {{
    content: "{hint_text}";
  }}
"""


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
    if "lang" not in st.session_state:
        st.session_state.lang = "en"
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0


def display_sidebar():
    """显示侧边栏信息和控制"""
    with st.sidebar:
        st.markdown(
            '<div class="brand"><div class="brand-text">'
            f'<span class="brand-title">{t("brand_title")}</span>'
            f'<span class="brand-sub">{t("brand_sub")}</span>'
            '</div></div>',
            unsafe_allow_html=True
        )

        # 可用技能
        skills = st.session_state.skill_loader.get_all_skills()
        skill_count = len(skills)
        st.markdown(f'<div class="side-label">📦 {t("available_skills")} <span class="count-pill">{skill_count}</span></div>', unsafe_allow_html=True)

        skill_name_map = {
            "code_generation": t("code_generation"),
            "document_qa": t("document_qa"),
            "stock_analysis": t("stock_analysis"),
            "web_search": t("web_search")
        }

        for skill_name, skill_data in skills.items():
            display_name = skill_name_map.get(skill_name, skill_name)
            with st.expander(f"🔧 {display_name}"):
                # 使用翻译的技能描述
                desc_key = f"{skill_name}_desc"
                desc = t(desc_key) if desc_key in i18n.get(st.session_state.lang, {}) else skill_data['description']
                st.markdown(f"**{t('description')}:** {desc}")

                st.markdown(f"**{t('parameters')}:**")
                # 为参数显示翻译的标签（如果存在）
                param_labels = {
                    "code_generation": {"requirement": t("code_generation_requirement"), "language": t("code_generation_language")},
                    "document_qa": {"query": t("document_qa_query")},
                    "stock_analysis": {"ticker": t("stock_analysis_ticker")},
                    "web_search": {"query": t("web_search_query")}
                }

                for param in skill_data['parameters']:
                    param_name = param.split(":")[0].strip()
                    if skill_name in param_labels and param_name in param_labels[skill_name]:
                        label = param_labels[skill_name][param_name]
                    else:
                        label = param_name
                    st.markdown(f"- {label}")

        st.markdown("---")

        # 文档管理
        st.markdown(f'<div class="side-label">📚 {t("document_management")}</div>', unsafe_allow_html=True)
        doc_store = st.session_state.document_store

        # 使用 session_state 跟踪已上传的文件
        if "uploaded_files" not in st.session_state:
            st.session_state.uploaded_files = set()

        uploaded_file = st.file_uploader("", type=['txt', 'md'], key=f"doc_uploader_{st.session_state.uploader_key}")
        if uploaded_file is not None:
            # 生成文件的唯一标识
            file_key = f"{uploaded_file.name}_{uploaded_file.size}"

            # 只在文件首次上传时处理
            if file_key not in st.session_state.uploaded_files:
                content = uploaded_file.read().decode('utf-8')
                doc_id = doc_store.add_document(content, uploaded_file.name)
                st.session_state.uploaded_files.add(file_key)
                st.success(f"{t('doc_added')}: {uploaded_file.name}")
            else:
                st.info(f"{t('doc_exists')}: {uploaded_file.name}")

        # 显示当前文档
        docs = doc_store.get_all_documents()
        if docs:
            st.markdown(f"**{t('knowledge_base_docs')}:** {len(docs)}")
            for doc in docs:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"- {doc['filename']}")
                with col2:
                    if st.button("🗑️", key=f"del_{doc['id']}", use_container_width=True):
                        doc_store.remove_document(doc['id'])
                        if "uploaded_files" in st.session_state:
                            # 清除该文件对应的上传记录，允许重新上传同名文件
                            st.session_state.uploaded_files = {
                                k for k in st.session_state.uploaded_files
                                if not k.startswith(doc['filename'] + '_')
                            }
                        st.session_state.uploader_key += 1
                        st.success(t('doc_deleted'))
                        st.rerun()
        else:
            st.info(t('no_docs'))

        if st.button(t('clear_all_docs'), key="clear_docs_btn", use_container_width=True, type="secondary"):
            st.session_state.document_store = DocumentStore()
            if "uploaded_files" in st.session_state:
                st.session_state.uploaded_files.clear()
            st.session_state.uploader_key += 1  # 重置文件上传组件，避免文档被重新添加
            st.success(t('all_docs_cleared'))
            st.rerun()

        st.markdown("---")

        # 清空聊天
        if st.button(t('clear_chat'), use_container_width=True, type="primary"):
            st.session_state.messages = []
            st.rerun()

        st.markdown("""
<div style="text-align:center; font-size:12px; color:#9CA3AF; padding: 8px 0 4px;">
  Built by <a href="https://github.com/aeolusyansheng19810626" target="_blank" style="color:#7C3AED; text-decoration:none;">Sheng Yan</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/aeolusyansheng19810626" target="_blank" style="color:#7C3AED; text-decoration:none;">GitHub</a>
</div>
        """, unsafe_allow_html=True)


def _inject_document_store(routing_result: dict):
    """Inject session document_store into params for document_qa steps."""
    if "plan" in routing_result:
        for step in routing_result["plan"]:
            if step.get("skill") == "document_qa":
                step["params"]["document_store"] = st.session_state.document_store
    elif routing_result.get("skill") == "document_qa":
        routing_result["params"]["document_store"] = st.session_state.document_store


def execute_skill(routing_result: dict, user_query: str = ""):
    """执行路由结果（单技能或 pipeline），流式输出结果"""
    _inject_document_store(routing_result)
    yield from pipeline.execute(routing_result, st.session_state.skill_loader, user_query=user_query)


def process_user_input(user_input: str):
    """通过路由器处理用户输入并执行相应技能"""
    # 添加用户消息到聊天
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(f'<span class="msg-hook msg-user"></span>{user_input}', unsafe_allow_html=True)

    # 获取路由决策
    with st.chat_message("assistant"):
        st.markdown('<span class="msg-hook msg-assistant"></span>', unsafe_allow_html=True)
        # 显示路由决策
        with st.spinner(t("analyzing")):
            routing_result = st.session_state.router.route(user_input)

        reasoning = routing_result.get("reasoning", "")
        is_plan = "plan" in routing_result
        skill_name = routing_result.get("skill", "none")
        is_active = is_plan or skill_name != "none"

        # 显示正在调用的技能
        if is_active:
            if is_plan:
                steps = routing_result["plan"]
                def _step_label(s):
                    if "parallel" in s:
                        return "(" + " ‖ ".join(sub["skill"] for sub in s["parallel"]) + ")"
                    return s.get("skill", "?")
                label = " → ".join(_step_label(s) for s in steps)
            else:
                label = None  # will be set in placeholder below

            # 执行技能（单个或 pipeline）并收集结果
            skill_label = skill_name if not is_plan else label
            current_model = st.session_state.router.model
            _MARKER_PREFIX = "\x00DYNAMIC_SKILL:"

            full_response = ""
            pipeline_label = t("pipeline")
            calling_label = t("calling")
            spinner_label = f'{pipeline_label if is_plan else calling_label}: {skill_label}'
            with st.spinner(spinner_label):
                for chunk in execute_skill(routing_result, user_query=user_input):
                    if _MARKER_PREFIX in chunk:
                        dynamic_name = chunk.split(_MARKER_PREFIX)[1].rstrip("\x00").strip()
                        skill_label = skill_label + f" → ✨{dynamic_name}"
                    else:
                        full_response += chunk

            # 渲染最终气泡（最上方，在推理过程之前）
            prefix = f"{t('pipeline')}: " if (is_plan or " → " in skill_label) else f"{t('calling')}: "
            model_label = t("model")
            st.markdown(
                f'<div class="skill-calling">🔧 {prefix}<code>{skill_label}</code> &nbsp;·&nbsp; {model_label}: <code>{current_model}</code></div>',
                unsafe_allow_html=True,
            )

            # 使用可折叠组件显示推理过程
            with st.expander(t("view_reasoning")):
                st.markdown(f"**{t('model')}:** `{st.session_state.router.model}`\n\n")
                st.markdown(f"**{t('reasoning')}:** {reasoning}")

            # 将结果放在可折叠的气泡中（在横线上方）
            with st.expander(t("view_full_result"), expanded=True):
                st.markdown(full_response)

            # 保存助手响应
            display_skill = f"pipeline:{label}" if is_plan else skill_name
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response,
                "skill": display_skill,
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
                fallback_msg = t("no_skill_match")
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

    # 注入 CSS（基础样式 + Streamlit 重写 + 动态CSS）
    dynamic_css = get_dynamic_css()
    st.markdown(f"<style>\n{styles_css}\n{streamlit_overrides}\n{dynamic_css}\n</style>", unsafe_allow_html=True)

    # 显示侧边栏
    display_sidebar()

    # Topbar
    skill_count = len(st.session_state.skill_loader.get_all_skills()) if "skill_loader" in st.session_state else 0
    skills_text = t("skill_text")
    skills_loaded = t("skills_loaded")
    topbar_html = f"""<div class='topbar-wrapper'><div class='topbar'><div class='topbar-left'><div class='page-title'>{t('topbar_title')}</div><div class='page-sub'>{t('topbar_sub')}</div></div><div class='topbar-right'><div class='status'><span class='status-dot'></span>{skills_loaded}{skill_count}{skills_text}</div><div id='lang-switcher-anchor'></div></div></div></div></div>"""
    st.markdown(topbar_html, unsafe_allow_html=True)

    # Language Switcher - positioned in topbar via CSS (position:fixed)
    lang_labels = {"zh": "中", "ja": "日", "en": "英"}
    cur_label = lang_labels.get(st.session_state.lang, "中")
    with st.popover(cur_label, use_container_width=False):
        st.markdown('<p class="lang-hdr">LANGUAGE / 语言</p>', unsafe_allow_html=True)
        for code, abbr, name in [("zh", "CN", "简体中文"), ("ja", "JP", "日本語"), ("en", "EN", "English")]:
            active = st.session_state.lang == code
            label = f"{abbr}  {name}  ✓" if active else f"{abbr}  {name}"
            if st.button(label, use_container_width=True,
                         type="primary" if active else "secondary",
                         key=f"lang_{code}"):
                st.session_state.lang = code
                st.rerun()

    # 显示聊天历史
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(f'<span class="msg-hook msg-user"></span>{message["content"]}', unsafe_allow_html=True)
            elif message["role"] == "assistant" and "skill" in message:
                st.markdown('<span class="msg-hook msg-assistant"></span>', unsafe_allow_html=True)
                if message["skill"] != "none":
                    is_pipeline = message["skill"].startswith("pipeline:")
                    prefix = t("pipeline") if is_pipeline else t("calling")
                    label = message["skill"].removeprefix("pipeline:")
                    st.markdown(f'<div class="skill-calling">🔧 {prefix}: <code>{label}</code></div>', unsafe_allow_html=True)
                    if "reasoning" in message:
                        # 使用可折叠组件显示推理过程
                        with st.expander(t("view_reasoning")):
                            st.markdown(f"**{t('model')}:** `{st.session_state.router.model}`\n\n")
                            st.markdown(f"**{t('reasoning')}:** {message['reasoning']}")
                    # 将结果放在可折叠的气泡中（在横线上方）
                    with st.expander(t("view_full_result"), expanded=True):
                        st.markdown(message["content"])
                else:
                    st.markdown(message["content"])
            else:
                st.markdown(message["content"])

    # 聊天输入
    if prompt := st.chat_input(t("chat_placeholder")):
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

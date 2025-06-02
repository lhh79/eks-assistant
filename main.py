
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="AWS EKS 클러스터 관리 어시스턴트",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사이드바 구성
with st.sidebar:
    st.markdown("### EKS 관리 도구")
    
    # 새 대화 시작 버튼
    if st.button("➕ 새 대화 시작", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    
    # 메뉴 항목들
    menu_items = [
        ("📊", "클러스터 현황 조회"),
        ("🔧", "kubectl 명령어 가이드"),
        ("⭐", "Bedrock 모델 목록"),
        ("⚙️", "EKS 보안 설정"),
        ("💾", "RDS 연결 설정")
    ]
    
    for icon, label in menu_items:
        if st.button(f"{icon} {label}", use_container_width=True):
            st.session_state.selected_menu = label
    
    st.markdown("---")
    st.markdown("**최근 (4개)**")
    st.button("💬 새 대화 (8:17 #1)", use_container_width=True)

# 메인 콘텐츠 영역
st.markdown("""
<div style="text-align: center; margin: 2rem 0;">
    <h1>☁️ AWS EKS 클러스터 관리 어시스턴트</h1>
    <p style="color: #666; font-size: 1.1rem;">AWS Bedrock과 EKS 서비스를 활용한 클러스터 관리 및 문제 해결을 도와드립니다.</p>
</div>
""", unsafe_allow_html=True)

# EKS 클러스터 상태 섹션
st.markdown("### 📊 EKS 클러스터 상태")
col1, col2 = st.columns([3, 1])

with col1:
    cluster_name = st.text_input("", placeholder="lgons-champions-agent-eks", key="cluster_input")

with col2:
    st.button("새로 검색하기", type="primary")

# 기능 카드들
st.markdown("### 주요 기능")

col1, col2 = st.columns(2)

with col1:
    with st.container():
        st.markdown("""
        <div style="border: 1px solid #333; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; background-color: #1e1e1e;">
            <h4>☁️ How do I create an EKS cluster?</h4>
            <p style="color: #ccc; font-size: 0.9rem;">Get a step-by-step guide to create and configure an EKS cluster</p>
        </div>
        """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown("""
        <div style="border: 1px solid #333; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; background-color: #1e1e1e;">
            <h4>🔧 Common kubectl commands for EKS</h4>
            <p style="color: #ccc; font-size: 0.9rem;">Get the most useful kubectl commands for managing EKS clusters</p>
        </div>
        """, unsafe_allow_html=True)

with col2:
    with st.container():
        st.markdown("""
        <div style="border: 1px solid #333; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; background-color: #1e1e1e;">
            <h4>📊 Show me my EKS clusters</h4>
            <p style="color: #ccc; font-size: 0.9rem;">List all available EKS clusters in my AWS account</p>
        </div>
        """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown("""
        <div style="border: 1px solid #333; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; background-color: #1e1e1e;">
            <h4>📈 How do I scale my EKS deployment?</h4>
            <p style="color: #ccc; font-size: 0.9rem;">Learn how to scale your applications running on EKS</p>
        </div>
        """, unsafe_allow_html=True)

# 추가 기능 카드
with st.container():
    st.markdown("""
    <div style="border: 1px solid #333; border-radius: 8px; padding: 1rem; margin: 1rem 0; background-color: #1e1e1e;">
        <h4>💾 How to connect RDS to my EKS cluster?</h4>
        <p style="color: #ccc; font-size: 0.9rem;">Steps to integrate your EKS cluster with AWS RDS</p>
    </div>
    """, unsafe_allow_html=True)

# 하단 입력 영역
st.markdown("---")
col1, col2, col3 = st.columns([8, 1, 1])

with col1:
    user_input = st.text_input("", placeholder="AWS EKS 관련 질문이나 명령어를 입력해주세요...", key="main_input")

with col2:
    st.markdown("<div style='margin-top: 1.5rem;'>0/4000</div>", unsafe_allow_html=True)

with col3:
    if st.button("📤", help="전송"):
        if user_input:
            st.success(f"질문을 받았습니다: {user_input}")

# CSS 스타일링
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    
    .stSidebar {
        background-color: #1e1e1e;
    }
    
    .stButton > button {
        background-color: #262730;
        color: white;
        border: 1px solid #333;
        border-radius: 6px;
    }
    
    .stButton > button:hover {
        background-color: #364364;
        border-color: #4a90e2;
    }
    
    .stTextInput > div > div > input {
        background-color: #1e1e1e;
        color: white;
        border: 1px solid #333;
    }
    
    h1, h2, h3, h4 {
        color: white;
    }
    
    p {
        color: #ccc;
    }
</style>
""", unsafe_allow_html=True)

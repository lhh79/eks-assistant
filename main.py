
import streamlit as st
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import json
import time
import os
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="AWS EKS 클러스터 관리 어시스턴트",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# AWS 클라이언트 초기화
@st.cache_resource
def init_aws_clients():
    """AWS 클라이언트들을 초기화합니다."""
    try:
        # AWS 자격 증명 확인
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        if not aws_access_key_id or not aws_secret_access_key:
            st.error("❌ AWS 자격 증명이 설정되지 않았습니다. Secrets에서 AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY를 설정해주세요.")
            return None
        
        # 기본 리전 설정
        region = 'us-west-2'  # 미국 서부 리전
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region
        )
        
        return {
            'eks': session.client('eks', region_name=region),
            'bedrock_runtime': session.client('bedrock-runtime', region_name='us-west-2'),
            'bedrock': session.client('bedrock', region_name='us-west-2')
        }
    except (NoCredentialsError, ClientError) as e:
        st.error(f"AWS 서비스 초기화 중 오류가 발생했습니다: {e}")
        return None

# 사용 가능한 Bedrock 모델 조회
def get_available_models(bedrock_client):
    """사용 가능한 Bedrock 모델 목록을 조회합니다."""
    try:
        response = bedrock_client.list_foundation_models()
        models = []
        
        for model in response['modelSummaries']:
            # 텍스트 생성이 가능한 모델만 필터링하고 Claude 4 모델 제외
            if ('TEXT' in model.get('inputModalities', []) and 
                'TEXT' in model.get('outputModalities', []) and
                'claude-4' not in model['modelId'].lower() and
                'opus-4' not in model['modelId'].lower()):
                models.append({
                    'modelId': model['modelId'],
                    'modelName': model['modelName'],
                    'providerName': model['providerName']
                })
        
        return models
    except ClientError as e:
        st.error(f"Bedrock 모델 조회 중 오류가 발생했습니다: {e}")
        return []

# EKS 클러스터 정보 조회
def get_eks_clusters(eks_client):
    """EKS 클러스터 목록을 조회합니다."""
    try:
        response = eks_client.list_clusters()
        clusters = []
        
        for cluster_name in response['clusters']:
            cluster_detail = eks_client.describe_cluster(name=cluster_name)
            clusters.append({
                'name': cluster_name,
                'status': cluster_detail['cluster']['status'],
                'version': cluster_detail['cluster']['version'],
                'endpoint': cluster_detail['cluster']['endpoint'],
                'created_at': cluster_detail['cluster']['createdAt']
            })
        
        return clusters
    except ClientError as e:
        st.error(f"EKS 클러스터 조회 중 오류가 발생했습니다: {e}")
        return []

# Bedrock 모델 호출
def invoke_bedrock_model(bedrock_runtime, model_id, prompt, temperature=0.7, max_tokens=1000):
    """Bedrock 모델을 직접 호출합니다."""
    try:
        if 'anthropic.claude' in model_id:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType='application/json'
            )
            
        elif 'amazon.titan' in model_id:
            body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": temperature,
                    "topP": 0.9
                }
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType='application/json'
            )
            
        elif 'meta.llama' in model_id:
            body = {
                "prompt": prompt,
                "max_gen_len": max_tokens,
                "temperature": temperature,
                "top_p": 0.9
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType='application/json'
            )
            
        else:
            # 기본 형식
            body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": temperature
                }
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType='application/json'
            )
        
        response_body = json.loads(response['body'].read())
        
        # 모델별 응답 파싱
        if 'anthropic.claude' in model_id:
            return response_body['content'][0]['text']
        elif 'amazon.titan' in model_id:
            return response_body['results'][0]['outputText']
        elif 'meta.llama' in model_id:
            return response_body['generation']
        else:
            return response_body.get('outputText', str(response_body))
            
    except ClientError as e:
        st.error(f"Bedrock 모델 호출 중 오류가 발생했습니다: {e}")
        return None

# AWS 설정 초기화
aws_clients = init_aws_clients()

# 세션 상태 초기화
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'selected_cluster' not in st.session_state:
    st.session_state.selected_cluster = None
if 'chat_sessions' not in st.session_state:
    st.session_state.chat_sessions = []
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = 0

# 사이드바 구성
with st.sidebar:
    st.markdown("### EKS 관리 도구")
    
    # AWS 설정 섹션
    st.markdown("#### ⚙️ AWS 설정")
    
    # Bedrock 모델 설정
    if aws_clients and 'bedrock' in aws_clients:
        with st.expander("🤖 Bedrock 모델 설정", expanded=True):
            # 사용 가능한 모델 목록 조회
            if 'available_models' not in st.session_state:
                with st.spinner("사용 가능한 모델을 조회하는 중..."):
                    models = get_available_models(aws_clients['bedrock'])
                    st.session_state.available_models = models
            
            models = st.session_state.get('available_models', [])
            
            if models:
                # 모델 이름을 간단하게 변환하는 함수
                def get_simple_model_name(model_id, provider_name):
                    # Claude 모델들 (Claude 4는 현재 지원하지 않음)
                    if 'claude-3-5-sonnet' in model_id:
                        return "Claude 3.5 Sonnet"
                    elif 'claude-3-5-haiku' in model_id:
                        return "Claude 3.5 Haiku"
                    elif 'claude-3-opus' in model_id:
                        return "Claude 3 Opus"
                    elif 'claude-3-sonnet' in model_id:
                        return "Claude 3 Sonnet"
                    elif 'claude-3-haiku' in model_id:
                        return "Claude 3 Haiku"
                    elif 'claude' in model_id:
                        return f"Claude ({model_id.split('.')[-1]})"
                    
                    # Amazon Titan 모델들
                    elif 'titan-text-premier' in model_id:
                        return "Titan Text Premier"
                    elif 'titan-text-express' in model_id:
                        return "Titan Text Express"
                    elif 'titan-text-lite' in model_id:
                        return "Titan Text Lite"
                    elif 'titan' in model_id:
                        return f"Titan ({model_id.split('.')[-1]})"
                    
                    # Meta Llama 모델들
                    elif 'llama3-2-90b' in model_id:
                        return "Llama 3.2 90B"
                    elif 'llama3-2-11b' in model_id:
                        return "Llama 3.2 11B"
                    elif 'llama3-2-3b' in model_id:
                        return "Llama 3.2 3B"
                    elif 'llama3-2-1b' in model_id:
                        return "Llama 3.2 1B"
                    elif 'llama' in model_id:
                        return f"Llama ({model_id.split('.')[-1]})"
                    
                    # Cohere Command 모델들
                    elif 'command-r-plus' in model_id:
                        return "Command R+"
                    elif 'command-r' in model_id:
                        return "Command R"
                    elif 'command' in model_id:
                        return f"Command ({model_id.split('.')[-1]})"
                    
                    # AI21 Jamba 모델들
                    elif 'jamba-1-5-large' in model_id:
                        return "Jamba 1.5 Large"
                    elif 'jamba-1-5-mini' in model_id:
                        return "Jamba 1.5 Mini"
                    elif 'jamba' in model_id:
                        return f"Jamba ({model_id.split('.')[-1]})"
                    
                    # 기타 모델들 - 제공사명과 모델ID의 마지막 부분 사용
                    else:
                        # 모델 ID에서 버전 정보 추출 시도
                        model_parts = model_id.split('.')
                        if len(model_parts) > 1:
                            return f"{provider_name} ({model_parts[-1]})"
                        else:
                            return f"{provider_name} Model"
                
                model_options = [get_simple_model_name(model['modelId'], model['providerName']) for model in models]
                model_ids = [model['modelId'] for model in models]
                
                selected_index = st.selectbox(
                    "사용할 모델 선택",
                    range(len(model_options)),
                    format_func=lambda x: model_options[x],
                    index=0,
                    help="Bedrock에서 사용할 AI 모델을 선택하세요"
                )
                
                selected_model_id = model_ids[selected_index]
                
                # 모델 파라미터 설정
                col1, col2 = st.columns(2)
                with col1:
                    temperature = st.slider(
                        "Temperature",
                        min_value=0.0,
                        max_value=1.0,
                        value=0.7,
                        step=0.1,
                        help="창의성 조절 (0: 일관성, 1: 창의적)"
                    )
                
                with col2:
                    max_tokens = st.number_input(
                        "Max Tokens",
                        min_value=100,
                        max_value=4000,
                        value=1000,
                        step=100,
                        help="최대 응답 길이"
                    )
                
                # 설정 저장
                st.session_state.selected_model_id = selected_model_id
                st.session_state.temperature = temperature
                st.session_state.max_tokens = max_tokens
                
                st.success(f"✅ 선택된 모델: {model_options[selected_index]}")
            else:
                st.warning("사용 가능한 모델이 없습니다.")
                if st.button("🔄 모델 목록 새로고침"):
                    if 'available_models' in st.session_state:
                        del st.session_state.available_models
                    st.rerun()
    else:
        st.warning("AWS Bedrock 서비스에 연결되지 않았습니다.")
    
    st.markdown("---")
    
    # 새 대화 시작 버튼
    if st.button("➕ 새 대화 시작", use_container_width=True):
        # 현재 대화가 있으면 저장
        if st.session_state.chat_history:
            session_title = f"대화 #{len(st.session_state.chat_sessions) + 1}"
            first_user_message = next((msg for role, msg in st.session_state.chat_history if role == "user"), "")
            if first_user_message:
                session_title = first_user_message[:30] + ("..." if len(first_user_message) > 30 else "")
            
            new_session = {
                'id': st.session_state.current_session_id,
                'title': session_title,
                'messages': st.session_state.chat_history.copy(),
                'timestamp': datetime.now().strftime('%H:%M')
            }
            
            st.session_state.chat_sessions.append(new_session)
            st.session_state.current_session_id += 1
            
            st.success(f"✅ 현재 대화를 '{session_title}'로 저장했습니다.")
        
        st.session_state.chat_history = []
        st.rerun()
    
    st.markdown("---")
    
    # kubectl 명령어 가이드
    st.markdown("#### 🔧 kubectl 명령어 가이드")
    
    # Pod 관련 명령어
    with st.expander("📦 Pod 관리", expanded=False):
        st.code("kubectl get pods", language="bash")
        st.code("kubectl get pods -o wide", language="bash")
        st.code("kubectl describe pod <pod-name>", language="bash")
        st.code("kubectl logs <pod-name>", language="bash")
        st.code("kubectl exec -it <pod-name> -- /bin/bash", language="bash")
        st.code("kubectl delete pod <pod-name>", language="bash")
    
    # Deployment 관련 명령어
    with st.expander("🚀 Deployment 관리", expanded=False):
        st.code("kubectl get deployments", language="bash")
        st.code("kubectl describe deployment <deployment-name>", language="bash")
        st.code("kubectl scale deployment <deployment-name> --replicas=3", language="bash")
        st.code("kubectl rollout status deployment/<deployment-name>", language="bash")
        st.code("kubectl rollout restart deployment/<deployment-name>", language="bash")
        st.code("kubectl rollout undo deployment/<deployment-name>", language="bash")
    
    # Service 관련 명령어
    with st.expander("🌐 Service 관리", expanded=False):
        st.code("kubectl get services", language="bash")
        st.code("kubectl get svc", language="bash")
        st.code("kubectl describe service <service-name>", language="bash")
        st.code("kubectl port-forward service/<service-name> 8080:80", language="bash")
        st.code("kubectl expose deployment <deployment-name> --port=80 --type=LoadBalancer", language="bash")
    
    # 클러스터 정보 명령어
    with st.expander("📊 클러스터 정보", expanded=False):
        st.code("kubectl cluster-info", language="bash")
        st.code("kubectl get nodes", language="bash")
        st.code("kubectl get nodes -o wide", language="bash")
        st.code("kubectl top nodes", language="bash")
        st.code("kubectl top pods", language="bash")
        st.code("kubectl get namespaces", language="bash")
    
    # ConfigMap & Secret 명령어
    with st.expander("🔐 ConfigMap & Secret", expanded=False):
        st.code("kubectl get configmaps", language="bash")
        st.code("kubectl get secrets", language="bash")
        st.code("kubectl describe configmap <configmap-name>", language="bash")
        st.code("kubectl describe secret <secret-name>", language="bash")
        st.code("kubectl create secret generic <secret-name> --from-literal=key=value", language="bash")
    
    # 리소스 관리 명령어
    with st.expander("📋 리소스 관리", expanded=False):
        st.code("kubectl get all", language="bash")
        st.code("kubectl get all -n <namespace>", language="bash")
        st.code("kubectl apply -f <file.yaml>", language="bash")
        st.code("kubectl delete -f <file.yaml>", language="bash")
        st.code("kubectl edit deployment <deployment-name>", language="bash")
        st.code("kubectl patch deployment <deployment-name> -p '{\"spec\":{\"replicas\":5}}'", language="bash")
    
    st.markdown("---")
    
    # 이전 채팅 기록
    st.markdown("#### 📝 이전 대화")
    
    # 디버깅 정보 (개발 중에만 표시)
    if st.checkbox("🔍 디버그 정보", value=False):
        st.write(f"현재 대화 메시지 수: {len(st.session_state.chat_history)}")
        st.write(f"저장된 세션 수: {len(st.session_state.chat_sessions)}")
        if st.session_state.chat_history:
            st.write("현재 대화 미리보기:")
            for i, (role, msg) in enumerate(st.session_state.chat_history[-2:]):
                st.write(f"  {i}: {role} - {msg[:50]}...")
    
    if st.session_state.chat_sessions:
        # 최근 5개 대화만 표시
        recent_sessions = st.session_state.chat_sessions[-5:]
        recent_sessions.reverse()  # 최신순으로 정렬
        
        for session in recent_sessions:
            col1, col2 = st.columns([4, 1])
            
            with col1:
                if st.button(f"💬 {session['title']}", 
                           key=f"session_{session['id']}", 
                           use_container_width=True,
                           help=f"대화 시간: {session['timestamp']}"):
                    # 선택된 대화로 복원
                    st.session_state.chat_history = session['messages'].copy()
                    st.success(f"✅ '{session['title']}' 대화를 불러왔습니다.")
                    st.rerun()
            
            with col2:
                if st.button("🗑️", 
                           key=f"delete_{session['id']}", 
                           help="대화 삭제"):
                    st.session_state.chat_sessions = [s for s in st.session_state.chat_sessions if s['id'] != session['id']]
                    st.rerun()
        
        st.markdown("---")
        
        # 모든 대화 삭제 버튼
        if st.button("🗑️ 모든 대화 삭제", use_container_width=True):
            st.session_state.chat_sessions = []
            st.rerun()
    else:
        st.info("저장된 대화가 없습니다.")

# 메인 콘텐츠 영역
st.markdown("""
<div style="text-align: center; margin: 2rem 0;">
    <h1>☁️ AWS EKS 클러스터 관리 어시스턴트</h1>
    <p style="color: #666; font-size: 1.1rem;">AWS Bedrock과 EKS 서비스를 활용한 클러스터 관리 및 문제 해결을 도와드립니다.</p>
</div>
""", unsafe_allow_html=True)

# AWS 연결 상태 확인
if aws_clients:
    st.success("✅ AWS 서비스에 연결되었습니다.")
    
    # EKS 클러스터 상태 섹션
    st.markdown("### 📊 EKS 클러스터 상태")
    
    if st.button("🔄 클러스터 목록 새로고침"):
        st.cache_resource.clear()
    
    # EKS 클러스터 목록 조회
    clusters = get_eks_clusters(aws_clients['eks'])
    
    if clusters:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            cluster_names = [cluster['name'] for cluster in clusters]
            selected_cluster_name = st.selectbox(
                "클러스터 선택",
                cluster_names,
                index=0 if cluster_names else None
            )
            
            if selected_cluster_name:
                selected_cluster = next(c for c in clusters if c['name'] == selected_cluster_name)
                st.session_state.selected_cluster = selected_cluster
        
        with col2:
            if st.button("클러스터 세부 정보", type="primary"):
                if st.session_state.selected_cluster:
                    cluster = st.session_state.selected_cluster
                    st.info(f"""
                    **클러스터**: {cluster['name']}
                    **상태**: {cluster['status']}
                    **버전**: {cluster['version']}
                    **생성일**: {cluster['created_at'].strftime('%Y-%m-%d %H:%M:%S')}
                    """)
        
        # 클러스터 상태 표시
        if clusters:
            cols = st.columns(len(clusters))
            for i, cluster in enumerate(clusters):
                with cols[i]:
                    status_color = "🟢" if cluster['status'] == 'ACTIVE' else "🔴"
                    st.metric(
                        label=f"{status_color} {cluster['name']}",
                        value=cluster['status'],
                        delta=f"v{cluster['version']}"
                    )
    else:
        st.warning("조회된 EKS 클러스터가 없습니다.")
else:
    st.error("❌ AWS 서비스 연결에 실패했습니다. 자격 증명을 확인해주세요.")

# 채팅 기록 표시
if st.session_state.chat_history:
    st.markdown("### 💬 대화 기록")
    
    # 채팅 기록을 컨테이너로 감싸서 스크롤 가능하게 만들기
    chat_container = st.container()
    
    with chat_container:
        for i, (role, message) in enumerate(st.session_state.chat_history):
            if role == "user":
                st.markdown(f"""
                <div style="background-color: #2b313e; padding: 10px; border-radius: 10px; margin: 10px 0; border-left: 3px solid #4CAF50;">
                    <strong>👤 사용자:</strong><br>
                    {message}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background-color: #1e1e1e; padding: 10px; border-radius: 10px; margin: 10px 0; border-left: 3px solid #2196F3;">
                    <strong>🤖 어시스턴트:</strong><br>
                    {message.replace('\n', '<br>')}
                </div>
                """, unsafe_allow_html=True)

# 기능 카드들
st.markdown("### 주요 기능")

col1, col2 = st.columns(2)

with col1:
    if st.button("☁️ How do I create an EKS cluster?", use_container_width=True):
        if aws_clients and st.session_state.get('selected_model_id'):
            with st.spinner("Bedrock 모델에서 응답을 가져오는 중..."):
                response = invoke_bedrock_model(
                    aws_clients['bedrock_runtime'],
                    st.session_state.selected_model_id,
                    "How do I create an EKS cluster? Provide step-by-step instructions.",
                    st.session_state.get('temperature', 0.7),
                    st.session_state.get('max_tokens', 1000)
                )
                if response:
                    st.session_state.chat_history.append(("user", "How do I create an EKS cluster?"))
                    st.session_state.chat_history.append(("assistant", response))
                    st.rerun()
    
    if st.button("🔧 Common kubectl commands for EKS", use_container_width=True):
        if aws_clients and st.session_state.get('selected_model_id'):
            with st.spinner("Bedrock 모델에서 응답을 가져오는 중..."):
                response = invoke_bedrock_model(
                    aws_clients['bedrock_runtime'],
                    st.session_state.selected_model_id,
                    "What are the most common kubectl commands for managing EKS clusters?",
                    st.session_state.get('temperature', 0.7),
                    st.session_state.get('max_tokens', 1000)
                )
                if response:
                    st.session_state.chat_history.append(("user", "Common kubectl commands for EKS"))
                    st.session_state.chat_history.append(("assistant", response))
                    st.rerun()

with col2:
    if st.button("📊 Show me my EKS clusters", use_container_width=True):
        if clusters:
            cluster_info = "\n".join([f"- {c['name']} (상태: {c['status']}, 버전: {c['version']})" for c in clusters])
            st.session_state.chat_history.append(("user", "Show me my EKS clusters"))
            st.session_state.chat_history.append(("assistant", f"현재 AWS 계정의 EKS 클러스터 목록:\n{cluster_info}"))
            st.rerun()
    
    if st.button("📈 How do I scale my EKS deployment?", use_container_width=True):
        if aws_clients and st.session_state.get('selected_model_id'):
            with st.spinner("Bedrock 모델에서 응답을 가져오는 중..."):
                response = invoke_bedrock_model(
                    aws_clients['bedrock_runtime'],
                    st.session_state.selected_model_id,
                    "How do I scale my EKS deployment? Include both horizontal and vertical scaling options.",
                    st.session_state.get('temperature', 0.7),
                    st.session_state.get('max_tokens', 1000)
                )
                if response:
                    st.session_state.chat_history.append(("user", "How do I scale my EKS deployment?"))
                    st.session_state.chat_history.append(("assistant", response))
                    st.rerun()

# 추가 기능 카드
if st.button("💾 How to connect RDS to my EKS cluster?", use_container_width=True):
    if aws_clients and st.session_state.get('selected_model_id'):
        with st.spinner("Bedrock 모델에서 응답을 가져오는 중..."):
            response = invoke_bedrock_model(
                aws_clients['bedrock_runtime'],
                st.session_state.selected_model_id,
                "How do I connect RDS to my EKS cluster? Include security best practices.",
                st.session_state.get('temperature', 0.7),
                st.session_state.get('max_tokens', 1000)
            )
            if response:
                st.session_state.chat_history.append(("user", "How to connect RDS to my EKS cluster?"))
                st.session_state.chat_history.append(("assistant", response))
                st.rerun()

# 하단 입력 영역
st.markdown("---")

# 채팅 입력 폼 생성 (엔터키로 전송 가능)
with st.form(key='chat_form', clear_on_submit=True):
    col1, col2, col3 = st.columns([8, 1, 1])
    
    with col1:
        user_input = st.text_input("질문 입력", 
                                  placeholder="AWS EKS 관련 질문이나 명령어를 입력해주세요... (엔터키로 전송)", 
                                  key="main_input",
                                  label_visibility="hidden")
    
    with col2:
        char_count = len(user_input) if user_input else 0
        st.markdown(f"<div style='margin-top: 1.5rem; color: #666;'>{char_count}/4000</div>", unsafe_allow_html=True)
    
    with col3:
        submitted = st.form_submit_button("📤", help="전송 (또는 엔터키)")

# 폼이 제출되었을 때 처리
if submitted and user_input:
    if aws_clients and st.session_state.get('selected_model_id'):
        with st.spinner("Bedrock 모델에서 응답을 가져오는 중..."):
            # 선택된 클러스터 정보를 컨텍스트에 추가
            context = ""
            if st.session_state.selected_cluster:
                cluster = st.session_state.selected_cluster
                context = f"현재 선택된 EKS 클러스터: {cluster['name']} (상태: {cluster['status']}, 버전: {cluster['version']})\n\n"
            
            full_prompt = context + user_input
            response = invoke_bedrock_model(
                aws_clients['bedrock_runtime'],
                st.session_state.selected_model_id,
                full_prompt,
                st.session_state.get('temperature', 0.7),
                st.session_state.get('max_tokens', 1000)
            )
            
            if response:
                st.session_state.chat_history.append(("user", user_input))
                st.session_state.chat_history.append(("assistant", response))
                st.rerun()
    elif not st.session_state.get('selected_model_id'):
        st.warning("Bedrock 모델을 먼저 선택해주세요.")
    else:
        st.error("AWS 서비스에 연결되지 않았습니다.")
elif submitted and not user_input:
    st.warning("질문을 입력해주세요.")

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
    
    .stSelectbox > div > div > select {
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
    
    .metric-container {
        background-color: #1e1e1e;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

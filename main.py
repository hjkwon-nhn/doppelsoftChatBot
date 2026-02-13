from openai import OpenAI
import streamlit as st
# from dotenv import load_dotenv
import os

# load_dotenv()
# client = OpenAI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")

# OpenAI 클라이언트 초기화 (API 키 명시)
client = OpenAI(api_key=OPENAI_API_KEY)

# 페이지 설정
st.set_page_config(
    page_title="도플소프트 블로그 챗봇",
    page_icon="🤖",
    layout="centered"
)

# ============================================
# Streamlit UI
# ============================================
st.title("🤖 도플소프트 블로그 챗봇")
st.caption("지하철종결자 · 전국스마트버스 · 스마트무브")

# 사용 방법 안내
st.info("""
💡 **사용 방법:**
- `/지하철` - 지하철종결자 앱만 검색
- `/버스` - 전국스마트버스 앱만 검색  
- `/무브` - 스마트무브 앱만 검색
- 명령어 없이 질문하면 **전체** 앱에서 검색합니다
""")

# Vector Store ID 확인
if not VECTOR_STORE_ID:
    st.error("⚠️ Vector Store ID가 설정되지 않았습니다!")
    st.info("""
    ### .env 파일 설정 방법:
    
    프로젝트 폴더에 `.env` 파일을 만들고 아래 내용을 추가하세요:
    
    ```
    OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
    VECTOR_STORE_ID=vs_xxxxxxxxxxxxx
    ```
    """)
    st.stop()

st.success(f"✅ Vector Store 연결됨")
st.divider()

# ============================================
# 채팅 대화 표시 영역
# ============================================

# 대화 히스토리 초기화
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# 지난 대화 출력
for message in st.session_state.chat_history:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

# ============================================
# 명령어 파싱 함수
# ============================================

def parse_command(text):
    """
    텍스트에서 명령어 파싱
    Returns: (service, clean_text)
    """
    text = text.strip()
    
    commands = {
        "/지하철": "지하철",
        "/버스": "버스",
        "/무브": "무브"
    }
    
    for cmd, service in commands.items():
        if text.startswith(cmd):
            # 명령어 제거하고 나머지 텍스트 반환
            clean_text = text[len(cmd):].strip()
            return service, clean_text
    
    # 명령어 없으면 전체
    return "전체", text

# 서비스별 필터링 프롬프트 생성
def get_service_instruction(service):
    service_map = {
        "지하철": "지하철종결자",
        "버스": "전국스마트버스",
        "무브": "스마트무브"
    }
    
    app_name = service_map.get(service, "")
    
    if service == "전체":
        return ""
    else:
        other_apps = [v for k, v in service_map.items() if k != service]
        return f"\n\n[중요: {app_name} 앱에 관련된 내용만 답변하세요. 다른 앱({', '.join(other_apps)})에 대한 질문이면 '이 질문은 {app_name} 앱과 관련이 없습니다'라고 안내하세요.]"

# ============================================
# 질문 입력 (브라우저 하단 자동 고정)
# ============================================

prompt = st.chat_input("질문을 입력하세요. 예: /지하철 프리미엄 해지 방법")

# ============================================
# 메시지 처리
# ============================================

if prompt:
    # 명령어 파싱
    service_filter, clean_prompt = parse_command(prompt)
    
    # 사용자 질문 출력
    service_icon = {"전체": "🔍", "지하철": "🚇", "버스": "🚌", "무브": "🚗"}
    with st.chat_message('user'):
        st.markdown(f"{service_icon[service_filter]} **[{service_filter}]** {clean_prompt}")
    st.session_state.chat_history.append({
        'role': 'user', 
        'content': f"{service_icon[service_filter]} [{service_filter}] {clean_prompt}",
        'service': service_filter
    })

    # 서비스별 필터 추가
    service_instruction = get_service_instruction(service_filter)
    enhanced_prompt = clean_prompt + service_instruction

    # 지난 대화가 없을 때
    if 'response_id' not in st.session_state:
        with st.spinner('답변 생성 중...'):
            response = client.responses.create(
                model="gpt-4o-mini",
                instructions="""당신은 도플소프트의 공식 고객지원 AI 어시스턴트입니다.

[회사 정보]
도플소프트는 다음 3가지 대중교통 앱을 서비스합니다:
- 지하철종결자: 지하철 전용 앱
- 전국스마트버스: 버스 전용 앱  
- 스마트무브: 통합 대중교통 앱

[핵심 규칙 - 반드시 준수]
1. 오직 도플소프트 블로그에 있는 정보만 사용하여 답변하세요
2. 사용자가 특정 앱을 선택한 경우, 해당 앱에 대한 정보만 제공하세요
3. 블로그에 없는 내용은 "블로그에서 관련 정보를 찾을 수 없습니다"라고 답변하세요
4. 절대로 외부 지식이나 일반적인 설명을 사용하지 마세요
5. 웹 검색이나 외부 네트워크 접근을 절대 시도하지 마세요

[답변 형식]
- 질문에 대한 명확하고 구체적인 답변
- 어떤 앱에 대한 내용인지 명시
- 답변 끝에 관련 게시글 링크 추가

[링크 규칙]
- 답변 본문에는 링크를 넣지 말 것
- 답변 끝에만 "📚 관련 게시글:" 섹션 추가
- 마크다운 형식: [게시글 제목](URL)
- 중복 없이 한 번씩만 나열

[답변할 수 없는 경우]
블로그에서 관련 정보를 찾을 수 없습니다. 더 구체적인 질문을 주시거나, 
고객센터(이메일/전화)로 문의해주세요.""",
                input=enhanced_prompt,
                tools=[{
                    "type": "file_search",
                    "vector_store_ids": [VECTOR_STORE_ID]
                }]
            )
    
    # 지난 대화가 있을 때
    else:
        with st.spinner('답변 생성 중...'):
            response = client.responses.create(
                previous_response_id=st.session_state.response_id,
                model="gpt-4o-mini",
                instructions="""당신은 도플소프트의 공식 고객지원 AI 어시스턴트입니다.

[회사 정보]
도플소프트는 다음 3가지 대중교통 앱을 서비스합니다:
- 지하철종결자: 지하철 전용 앱
- 전국스마트버스: 버스 전용 앱  
- 스마트무브: 통합 대중교통 앱

[핵심 규칙 - 반드시 준수]
1. 오직 도플소프트 블로그에 있는 정보만 사용하여 답변하세요
2. 사용자가 특정 앱을 선택한 경우, 해당 앱에 대한 정보만 제공하세요
3. 블로그에 없는 내용은 "블로그에서 관련 정보를 찾을 수 없습니다"라고 답변하세요
4. 절대로 외부 지식이나 일반적인 설명을 사용하지 마세요
5. 웹 검색이나 외부 네트워크 접근을 절대 시도하지 마세요

[답변 형식]
- 질문에 대한 명확하고 구체적인 답변
- 어떤 앱에 대한 내용인지 명시
- 답변 끝에 관련 게시글 링크 추가

[링크 규칙]
- 답변 본문에는 링크를 넣지 말 것
- 답변 끝에만 "📚 관련 게시글:" 섹션 추가
- 마크다운 형식: [게시글 제목](URL)
- 중복 없이 한 번씩만 나열

[답변할 수 없는 경우]
블로그에서 관련 정보를 찾을 수 없습니다. 더 구체적인 질문을 주시거나, 
고객센터(이메일/전화)로 문의해주세요.""",
                input=enhanced_prompt,
                tools=[{
                    "type": "file_search",
                    "vector_store_ids": [VECTOR_STORE_ID]
                }]
            )

    # LLM 답변 출력
    with st.chat_message('assistant'):
        st.markdown(response.output_text)
    st.session_state.chat_history.append({
        'role': 'assistant', 
        'content': response.output_text
    })
    st.session_state.response_id = response.id
    
    # 페이지 새로고침
    st.rerun()

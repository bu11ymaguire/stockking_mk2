import streamlit as st
import os
from agent import InvestmentAgent
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_option_menu import option_menu

# 페이지 설정
st.set_page_config(
    page_title="버핏 스타일 주식 분석기",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일링
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.2rem;
        color: #64748b;
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 12px 24px;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "agent" not in st.session_state:
    st.session_state.agent = None

# 로그인 페이지
if not st.session_state.logged_in:
    add_vertical_space(2)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<h1 class="main-header">🔐 버핏 스타일 주식 분석기</h1>', unsafe_allow_html=True)
        st.markdown('<p class="subtitle">워렌 버핏의 투자 철학으로 주식을 분석합니다</p>', unsafe_allow_html=True)

        add_vertical_space(2)

        colored_header(
            label="API 키 로그인",
            description="분석을 시작하려면 API 키를 입력해주세요",
            color_name="blue-70"
        )

        add_vertical_space(1)

        with st.form("login_form"):
            google_key = st.text_input(
                "🤖 Google Gemini API Key",
                type="password",
                placeholder="AIza...",
                help="https://aistudio.google.com/apikey — 무료 티어 사용 가능"
            )

            add_vertical_space(1)

            st.info(
                "💡 시장 데이터는 Genspark CLI(`gsk`)로 수집하고, "
                "분석은 Google Gemini 2.5 Flash 모델로 처리합니다. "
                "OpenAI/Perplexity 키 모두 불필요!",
                icon="✨"
            )

            add_vertical_space(2)

            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                submit_button = st.form_submit_button(
                    "🚀 로그인하고 시작하기",
                    use_container_width=True,
                    type="primary"
                )

            if submit_button:
                if not google_key:
                    st.error("⚠️ Gemini API 키를 입력해주세요!", icon="🚨")
                else:
                    try:
                        with st.spinner("로그인 중..."):
                            default_pdf = "stockking.pdf"
                            pdf_path = default_pdf if os.path.exists(default_pdf) else None

                            agent = InvestmentAgent(
                                google_api_key=google_key,
                                pdf_path=pdf_path
                            )
                            st.session_state.agent = agent
                            st.session_state.logged_in = True

                            if agent.vector_store:
                                st.success(f"✅ 로그인 성공! RAG 시스템 활성화됨", icon="✨")
                            else:
                                st.success("✅ 로그인 성공!", icon="✨")
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ API 키 검증 실패: {str(e)}", icon="🚨")

        add_vertical_space(2)

        with st.expander("💡 API 키 발급 가이드", expanded=False):
            st.markdown("""
            ### 🤖 Google Gemini API Key (무료!)
            1. [Google AI Studio](https://aistudio.google.com/apikey) 접속
            2. 구글 계정으로 로그인
            3. **"Create API key"** 클릭
            4. 새 프로젝트 선택 또는 기존 프로젝트 사용
            5. 생성된 키 (AIza...로 시작) 복사 → 위 입력란에 붙여넣기

            ### 💰 무료 티어 한도 (Gemini 2.0 Flash)
            - **1분당 15회 요청** (RPM)
            - **일일 1,500회 요청** (RPD)
            - **분당 100만 토큰** (TPM)

            학습/개인 사용엔 충분합니다. 신용카드 등록 불필요!
            """)

            st.warning("⚠️ API 키는 안전하게 보관하고 절대 공유하지 마세요!", icon="🔒")

# 메인 애플리케이션
else:
    # 헤더
    col_logo, col_title, col_logout = st.columns([0.5, 3, 1])
    with col_logo:
        st.markdown("# 📈")
    with col_title:
        st.markdown('<h1 class="main-header" style="font-size: 2.5rem;">버핏 스타일 주식 분석기</h1>', unsafe_allow_html=True)
    with col_logout:
        add_vertical_space(1)
        if st.button("🚪 로그아웃", use_container_width=True, type="secondary"):
            st.session_state.logged_in = False
            st.session_state.agent = None
            st.rerun()

    st.markdown("---")

    # 사이드바
    with st.sidebar:
        colored_header(
            label="설정 패널",
            description="분석 파라미터 조정",
            color_name="blue-70"
        )

        add_vertical_space(1)

        selected = option_menu(
            menu_title=None,
            options=["🎛️ 파라미터", "📄 PDF 업로드"],
            icons=["sliders", "file-earmark-pdf"],
            default_index=0,
            styles={
                "container": {"padding": "0!important"},
                "nav-link": {
                    "font-size": "14px",
                    "text-align": "left",
                    "margin": "0px",
                    "--hover-color": "#eee"
                },
                "nav-link-selected": {"background-color": "#3b82f6"}
            }
        )

        add_vertical_space(1)

        # 변수 초기화 (여기에 추가!)
        uploaded_file = None
        perplexity_max_tokens = 1500
        perplexity_temperature = 0.2
        openai_max_tokens = 6000  # 한글 분석은 토큰 많이 먹음
        openai_temperature = 0.3

        if selected == "🎛️ 파라미터":
            st.markdown("### 🔍 리서치 설정 (Genspark)")
            st.caption("정량 데이터는 자동 수집됩니다. 아래는 호환용 슬라이더 (현재는 사용 안 함).")
            perplexity_max_tokens = st.slider(
                "Max Tokens (참고용)",
                500, 3000, 1500,
                key="pplx_tokens",
                help="현재는 Genspark CLI가 자동 처리"
            )
            perplexity_temperature = st.slider(
                "Temperature (참고용)",
                0.0, 1.0, 0.2,
                step=0.1,
                key="pplx_temp",
                help="현재는 Genspark CLI가 자동 처리"
            )

            add_vertical_space(1)

            st.markdown("### 🤖 Gemini 분석 설정")
            openai_max_tokens = st.slider(
                "Max Tokens",
                1000, 8000, 6000,
                key="openai_tokens",
                help="분석 길이"
            )
            openai_temperature = st.slider(
                "Temperature",
                0.0, 1.0, 0.3,
                step=0.1,
                key="openai_temp",
                help="분석 창의성"
            )

        else:  # PDF 업로드
            st.markdown("### 📄 버크셔 서한 업로드")
            uploaded_file = st.file_uploader(
                "PDF 파일 선택",
                type=["pdf"],
                help="워렌 버핏의 투자 철학이 담긴 PDF"
            )

            if uploaded_file:
                with open("temp_uploaded.pdf", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success("✓ PDF 업로드 완료", icon="✅")
                st.info(f"📄 {uploaded_file.name}")
            else:
                st.info("PDF를 업로드하면 버핏의 인사이트가 분석에 반영됩니다.", icon="💡")

        add_vertical_space(2)
        st.caption("🔒 API 키는 세션 동안만 사용됩니다")

    # 메인 영역
    col_main1, col_main2 = st.columns([2, 1])

    with col_main1:
        colored_header(
            label="질문 입력",
            description="분석하고 싶은 주식에 대해 물어보세요",
            color_name="blue-70"
        )

        user_query = st.text_area(
            "💬 질문을 입력하세요",
            placeholder="예시:\n• What is NVIDIA?\n• Tesla 주식 분석해줘\n• Should I invest in Apple?\n• Microsoft의 경쟁력은?",
            height=180,
            label_visibility="collapsed"
        )

    with col_main2:
        colored_header(
            label="예시 질문",
            description="참고하세요",
            color_name="violet-70"
        )

        examples = [
            "What is NVIDIA?",
            "삼성전자 주식 분석",
            "Should I invest in Tesla?",
            "Apple의 투자 가치는?",
            "Microsoft 경쟁력 분석"
        ]

        for example in examples:
            if st.button(f"💡 {example}", use_container_width=True, key=f"ex_{example}"):
                st.session_state.example_query = example
                st.rerun()

        if hasattr(st.session_state, 'example_query'):
            user_query = st.session_state.example_query
            del st.session_state.example_query

    add_vertical_space(1)

    # 분석 버튼
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        analyze_button = st.button(
            "🚀 분석 시작하기",
            type="primary",
            use_container_width=True
        )

    if analyze_button:
        if not user_query:
            st.error("⚠️ 질문을 입력해주세요!", icon="🚨")
        else:
            with st.spinner("🔍 시장 데이터 수집 중..."):
                try:
                    # 파라미터 가져오기
                    if 'pplx_tokens' in st.session_state:
                        perplexity_max_tokens = st.session_state.pplx_tokens
                        perplexity_temperature = st.session_state.pplx_temp
                        openai_max_tokens = st.session_state.openai_tokens
                        openai_temperature = st.session_state.openai_temp
                    else:
                        perplexity_max_tokens = 1500
                        perplexity_temperature = 0.2
                        openai_max_tokens = 6000
                        openai_temperature = 0.3

                    pdf_path = "temp_uploaded.pdf" if uploaded_file else None

                    result = st.session_state.agent.analyze_stock(
                        user_query=user_query,
                        pdf_path=pdf_path,
                        perplexity_max_tokens=perplexity_max_tokens,
                        perplexity_temperature=perplexity_temperature,
                        openai_max_tokens=openai_max_tokens,
                        openai_temperature=openai_temperature
                    )

                    add_vertical_space(1)
                    st.success("✅ 분석 완료!", icon="✨")

                    # 결과 탭
                    tab1, tab2, tab3 = st.tabs([
                        "📊 종합 분석",
                        "🔍 시장 데이터",
                        "💡 버핏 인사이트"
                    ])

                    with tab1:
                        colored_header(
                            label="투자 분석 결과",
                            description="AI가 생성한 종합 분석",
                            color_name="green-70"
                        )

                        st.markdown(result["final_analysis"])

                        add_vertical_space(1)

                        col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
                        with col_dl2:
                            st.download_button(
                                "📥 분석 결과 다운로드",
                                result["final_analysis"],
                                file_name=f"분석_{user_query[:20]}.txt",
                                mime="text/plain",
                                use_container_width=True
                            )

                    with tab2:
                        colored_header(
                            label="Genspark 수집 정보",
                            description="실시간 시장 데이터",
                            color_name="blue-70"
                        )

                        st.markdown(result["market_data"].get("raw_response", "정보 없음"))

                        if result["market_data"].get("citations"):
                            add_vertical_space(1)
                            st.markdown("### 📚 참고 출처")
                            for i, citation in enumerate(result["market_data"]["citations"], 1):
                                st.markdown(f"{i}. [{citation}]({citation})")

                    with tab3:
                        colored_header(
                            label="버크셔 서한 인사이트",
                            description="워렌 버핏의 투자 철학",
                            color_name="orange-70"
                        )

                        if result["buffett_insights"]:
                            for i, insight in enumerate(result["buffett_insights"], 1):
                                with st.expander(f"💡 인사이트 #{i}", expanded=(i == 1)):
                                    st.markdown(insight)
                        else:
                            st.info(
                                "📄 PDF를 업로드하면 버핏의 인사이트를 확인할 수 있습니다.",
                                icon="💡"
                            )

                    if result.get("error"):
                        st.warning(f"⚠️ {result['error']}", icon="⚠️")

                except Exception as e:
                    st.error(f"❌ 오류 발생: {str(e)}", icon="🚨")
                    st.info("API 키를 확인하거나 로그아웃 후 다시 시도해주세요.", icon="💡")

    # 하단 정보
    add_vertical_space(2)
    st.markdown("---")

    with st.expander("💡 사용 팁 & 주의사항", expanded=False):
        col_tip1, col_tip2 = st.columns(2)

        with col_tip1:
            st.markdown("""
            **📌 효과적인 사용법**
            - 명확한 회사명/티커 심볼 사용
            - 구체적인 질문으로 정확한 답변 유도
            - 너무 맹신하지 않기
            - 파라미터 조정으로 맞춤 분석
            """)

        with col_tip2:
            st.markdown("""
            **⚠️ 주의사항**
            - 분석 결과는 참고용입니다
            - 투자 결정은 본인의 책임입니다
            - 실시간 데이터가 아닐 수 있습니다
            - API 사용량에 따라 비용 발생
            """)
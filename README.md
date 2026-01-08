# 📈 주식왕 스토킹 (StockKing)

**워렌 버핏 스타일 AI 주식 분석기** - RAG 기반 투자 철학 분석 시스템

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B.svg)](https://streamlit.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991.svg)](https://openai.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 프로젝트 개요

주식왕 스토킹은 워렌 버핏의 투자 철학을 AI로 재현한 주식 분석 시스템입니다.
- **Perplexity AI**로 최신 시장 데이터 수집
- **RAG(Retrieval-Augmented Generation)**로 버크셔 해서웨이 서한 분석
- **OpenAI GPT-4o**로 버핏 스타일 종합 투자 의견 생성

---

## ✨ 주요 기능

### 1. 🔍 실시간 시장 정보 수집
- Perplexity Sonar API로 최신 주가, 뉴스, 재무지표 수집
- Bloomberg, Reuters, WSJ 등 신뢰할 수 있는 출처만 사용

### 2. 📚 버핏 철학 기반 분석
- 버크셔 해서웨이 주주 서한 PDF에서 투자 원칙 추출
- FAISS 벡터 검색으로 관련 인사이트 자동 매칭

### 3. 🤖 5가지 투자 기준 평가
1. **비즈니스 이해도** - 명확한 수익 모델인가?
2. **경제적 해자** - 지속 가능한 경쟁 우위가 있는가?
3. **경영진 평가** - 주주 친화적 리더십인가?
4. **밸류에이션** - 내재 가치 대비 적정 가격인가?
5. **종합 투자 의견** - 매수/보유/매도 액션 아이템

### 4. 🎨 세련된 Streamlit UI
- **streamlit-option-menu**: 직관적인 네비게이션
- **streamlit-shadcn-ui**: 현대적인 카드/알림 컴포넌트
- **streamlit-extras**: 메트릭 카드, 컬러 헤더

---

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 리포지토리 클론
git clone https://github.com/bu11ymaguire/stockking.git
cd stockking

# 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

**requirements.txt:**
```text
streamlit>=1.28.0
streamlit-extras>=0.3.0
streamlit-option-menu>=0.3.6
streamlit-shadcn-ui>=0.1.0
langchain>=0.1.0
langchain-openai>=0.0.2
langchain-community>=0.0.10
faiss-cpu>=1.7.4
pypdf>=3.17.0
python-dotenv>=1.0.0
requests>=2.31.0
```

### 2. API 키 설정
사용자 로그인 형식으로, 보안에 얽매이지 않고 자유롭게 개발.

### 3. PDF 준비

버크셔 해서웨이 주주 서한 PDF를 프로젝트 루트에 배치:
```bash
stockking/
├── stockking.pdf  # 필수!
├── streamlit_app.py
├── agent.py
└── ...
```

### 4. 실행

**Jupyter Notebook 버전 (개발/테스트):**
```bash
jupyter notebook 주식왕스토킹_MK2.ipynb
```

**Streamlit 웹 앱:**
```bash
streamlit run streamlit_app.py
```

### 5. Streamlit Cloud에서 만나보세요 
[![Oracle of Omaha](https://img.shields.io/badge/Oracle_of_Omaha-Live_on_Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://oracleofomaha.streamlit.app/)

---

## 📁 프로젝트 구조

```
stockking/
├── 주식왕스토킹_MK2.ipynb    # 📌 핵심 분석 엔진 (우선순위 1)
├── streamlit_app.py          # 🎨 Streamlit UI
├── agent.py                  # 🤖 InvestmentAgent 클래스
├── test_agent.py             # 🧪 터미널 테스트 스크립트
├── stockking.pdf             # 📄 버크셔 서한 (필수)
├── requirements.txt          # 📦 의존성 패키지
└── README.md                 # 📖 문서
```

---

## 💻 사용 예시

### Jupyter Notebook

```python
# 1. RAG 초기화
pdf_path = 'stockking.pdf'
initialize_rag(pdf_path)

# 2. 주식 분석 실행
result = analyze_stock(
    user_query="What is NVIDIA?",
    pdf_path=pdf_path,
    perplexity_max_tokens=1500,
    perplexity_temperature=0.2,
    openai_max_tokens=2000,
    openai_temperature=0.3
)

# 3. 결과 확인
print(result['final_analysis'])
```

### Streamlit 웹 앱

1. **로그인**: OpenAI, Perplexity API 키 입력
2. **질문 입력**: "Microsoft 투자 의견", "TSLA는 어때?"
3. **파라미터 조정**: 설정 메뉴에서 max\_tokens, temperature 변경
4. **분석 시작**: 🚀 버튼 클릭
5. **결과 확인**: 종합 분석, 시장 데이터, 버핏 인사이트 탭

---

## 🔧 커스터마이징

### 분석 파라미터

**Perplexity (시장 정보 수집):**
- `max_tokens`: 500~3000 (기본 1500)
- `temperature`: 0.0~1.0 (기본 0.2, 낮을수록 일관적)

**OpenAI (종합 분석):**
- `max_tokens`: 500~4000 (기본 2000)
- `temperature`: 0.0~1.0 (기본 0.3, 낮을수록 보수적)

### PDF 변경

다른 투자 서적을 사용하려면:
```python
# agent.py 또는 노트북에서
initialize_rag("your_investment_book.pdf")
```

---

## 📊 워크플로우

```mermaid
graph LR
    A[사용자 질문] --> B[Perplexity API]
    B --> C[시장 데이터 수집]
    C --> D[RAG 검색]
    D --> E[버핏 인사이트 추출]
    E --> F[OpenAI GPT-4o]
    F --> G[종합 분석 생성]
    G --> H[5가지 기준 평가]
```

---

## 📌 주의사항

⚠️ **투자 책임**
- 본 도구는 **교육/연구 목적**입니다
- 실제 투자 결정은 본인의 책임입니다
- AI 분석 결과를 맹신하지 마세요

⚠️ **API 비용**
- OpenAI GPT-4o: $0.03/1K tokens (출력)
- Perplexity Sonar: $5/1K requests (프로 플랜)

---

## 🤝 기여하기

```bash
# 1. Fork 후 클론
git clone https://github.com/your-username/stockking.git

# 2. 브랜치 생성
git checkout -b feature/amazing-feature

# 3. 커밋
git commit -m "Add: 놀라운 기능 추가"

# 4. 푸시 및 PR
git push origin feature/amazing-feature
```

---

## 📝 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 📧 문의

- **GitHub**: [@bu11ymaguire](https://github.com/bu11ymaguire)
- **Issue**: [문제 리포트](https://github.com/bu11ymaguire/stockking/issues)

---

## 🙏 감사의 글

**Special Thanks:**
- **[SKT8LL 팀](https://github.com/SKT8LL)** - 본 프로젝트는 [원본 Jupyter Notebook](https://github.com/SKT8LL/stockking)을 Python 웹 애플리케이션으로 발전시킨 버전입니다. Python으로 구현해주신 팀장님 감사합니다! 🙌

**Powered by:**
- **Warren Buffett**: 투자 철학 제공
- **OpenAI**: GPT-4o API
- **Perplexity AI**: 실시간 검색 API
- **LangChain**: RAG 프레임워크
- **Streamlit**: 아름다운 UI 도구

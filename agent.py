import os
import requests
from datetime import datetime
from typing import TypedDict, List
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, END

from buffett_philosophy import (
    PERPLEXITY_SYSTEM_PROMPT,
    build_buffett_constitution,
)


class InvestmentState(TypedDict):
    user_query: str
    market_data: dict
    buffett_insights: List[str]
    final_analysis: str
    error: str
    perplexity_max_tokens: int
    perplexity_temperature: float
    openai_max_tokens: int
    openai_temperature: float


class InvestmentAgent:
    def __init__(self, openai_api_key: str, perplexity_api_key: str, pdf_path: str = None):
        self.openai_api_key = openai_api_key
        self.perplexity_api_key = perplexity_api_key
        self.vector_store = None
        self._current_pdf_path = None  # 캐싱: 같은 PDF면 재초기화 안 함

        # PDF 경로가 제공되면 즉시 RAG 초기화
        if pdf_path and os.path.exists(pdf_path):
            print(f"🔧 에이전트 초기화 시 RAG 설정: {pdf_path}")
            self.initialize_rag(pdf_path)

    def perplexity_research_node(self, state: InvestmentState) -> InvestmentState:
        """Perplexity API로 정보 수집"""
        user_query = state["user_query"]
        max_tokens = state.get("perplexity_max_tokens", 1500)
        temperature = state.get("perplexity_temperature", 0.2)

        print(f"🔍 Perplexity로 정보 수집 중: '{user_query}'")
        print(f"   📊 설정: max_tokens={max_tokens}, temperature={temperature}")

        try:
            url = "https://api.perplexity.ai/chat/completions"
            today = datetime.now().strftime("%Y-%m-%d")

            payload = {
                "model": "sonar-pro",
                "messages": [
                    {
                        "role": "system",
                        "content": PERPLEXITY_SYSTEM_PROMPT + f"\n\nToday's date: {today}"
                    },
                    {"role": "user", "content": user_query}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "return_citations": True,
                "search_domain_filter": [
                    "bloomberg.com", "reuters.com", "wsj.com",
                    "finance.yahoo.com", "investing.com", "seekingalpha.com",
                    "sec.gov", "ft.com"
                ]
            }

            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()
            market_data = {
                "raw_response": result["choices"][0]["message"]["content"],
                "citations": result.get("citations", []),
                "user_query": user_query
            }

            print(f"✓ Perplexity 정보 수집 완료")
            return {**state, "market_data": market_data}

        except Exception as e:
            print(f"❌ Perplexity API 오류: {str(e)}")
            return {
                **state,
                "market_data": {
                    "raw_response": f"정보 수집 실패: {str(e)}",
                    "user_query": user_query
                },
                "error": str(e)
            }

    def initialize_rag(self, pdf_path: str, force: bool = False):
        """RAG 시스템 초기화. 동일 PDF면 재구축 생략 (force=True로 강제)."""
        if not pdf_path:
            print("⚠️ PDF 경로가 제공되지 않았습니다. RAG 초기화 건너뜀")
            return

        if not os.path.exists(pdf_path):
            print(f"⚠️ PDF 파일을 찾을 수 없습니다: {pdf_path}")
            return

        # 캐싱: 같은 PDF면 재구축 안 함
        if (not force
                and self.vector_store is not None
                and self._current_pdf_path == pdf_path):
            print(f"✓ RAG 캐시 사용 (이미 초기화됨): {pdf_path}")
            return

        print(f"📄 PDF 로딩 중: {pdf_path}")

        loader = PyPDFLoader(pdf_path)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(documents)

        # api_key 명시적 전달 (os.environ 의존 제거)
        embeddings = OpenAIEmbeddings(api_key=self.openai_api_key)
        self.vector_store = FAISS.from_documents(splits, embeddings)
        self._current_pdf_path = pdf_path

        print(f"✓ RAG 초기화 완료: {len(splits)}개 청크")

    def rag_buffett_wisdom_node(self, state: InvestmentState) -> InvestmentState:
        """
        Perplexity가 수집한 회사 컨텍스트를 활용해
        버크셔 서한에서 *이 회사 평가에 직접 관련된* 구절을 동적으로 검색한다.
        하드코딩된 일반 키워드 대신, 회사·섹터·이슈 기반 쿼리를 생성한다.
        """
        user_query = state["user_query"]
        market_data = state.get("market_data", {})
        market_context = market_data.get("raw_response", "")
        print("📚 버핏 서한에서 관련 원칙 검색 중...")

        if self.vector_store is None:
            print("⚠️ RAG 시스템이 초기화되지 않음. 내장 원칙만 사용")
            return {**state, "buffett_insights": []}

        # 회사 컨텍스트가 있으면 그걸 검색 시드로 활용
        # (Perplexity가 식별한 사업 성격·섹터·이슈가 자연어로 담겨 있음)
        context_seed = (market_context[:800] if market_context else "")

        search_queries = [
            f"{user_query}",                                  # 사용자 원문
            f"{user_query} business quality moat",            # 해자 관련
            f"{user_query} management capital allocation",    # 경영진/자본배분
            f"{context_seed} valuation intrinsic value",      # 회사 맥락 + 밸류에이션
        ]
        # 빈/너무 짧은 쿼리 제거
        search_queries = [q.strip() for q in search_queries if len(q.strip()) > 5]

        insights = []
        seen_pages = set()
        for query in search_queries:
            docs = self.vector_store.similarity_search(query, k=3)
            for doc in docs:
                page = doc.metadata.get("page", -1)
                # 같은 페이지 중복 방지 (다양성 확보)
                key = (page, doc.page_content[:80])
                if key in seen_pages:
                    continue
                seen_pages.add(key)
                # 자르지 않고 그대로 보존 (1000자 청크 단위)
                insights.append({
                    "page": page,
                    "content": doc.page_content,
                })

        # 너무 많으면 상위 6개만
        insights = insights[:6]
        print(f"✓ {len(insights)}개 인사이트 추출 완료 ({len(seen_pages)}개 중복 제거)")
        return {**state, "buffett_insights": insights}

    def openai_analysis_node(self, state: InvestmentState) -> InvestmentState:
        """버핏 헌법을 system prompt로 주입하고, RAG/Perplexity 결과를 토대로 분석."""
        user_query = state["user_query"]
        market_data = state["market_data"]
        buffett_insights = state["buffett_insights"]
        max_tokens = state.get("openai_max_tokens", 2000)
        temperature = state.get("openai_temperature", 0.3)

        print("🤖 OpenAI로 종합 분석 중...")
        print(f"   📊 설정: max_tokens={max_tokens}, temperature={temperature}")

        # RAG 인사이트 포맷 (자르지 않음, 페이지 번호 포함)
        if buffett_insights:
            insights_text = "\n\n".join(
                f"[서한 p.{ins.get('page', '?')}]\n{ins.get('content', '')}"
                for ins in buffett_insights
            )
        else:
            insights_text = "(RAG 비활성화 — 내장된 버핏 원칙으로만 판단)"

        # 시스템 프롬프트: 버핏 헌법
        system_prompt = build_buffett_constitution() + """

# 분석 임무

당신은 위 가치관을 *내재화한* 분석가입니다. "버핏이라면 어떻게 볼까"가 아니라,
당신 자신이 그 가치관으로 직접 판단합니다.

## 평가 기준 (5점 척도)

### 1. 비즈니스 이해도 (Circle of Competence)
- 1점: 비즈니스 모델이 복잡하거나 10년 뒤를 예측 불가
- 3점: 어느 정도 이해 가능하나 일부 불확실성
- 5점: 단순하고 명확한 수익 구조 (예: 코카콜라)

### 2. 경제적 해자 (Economic Moat)
- 1점: 해자 없음, 경쟁 격렬, 가격 결정력 없음
- 3점: 일부 우위 (브랜드, 전환비용)
- 5점: 강력하고 지속 가능한 해자 (네트워크 효과, 규모의 경제, 라이선스)

### 3. 경영진 (Management Quality)
- 1점: 주주가치 훼손 이력, 과도한 보상, 회계 곡예, ABC 증상
- 3점: 평범하나 명백한 결격 사유 없음
- 5점: 주주 친화적, 정직, 자본 배분 능력 입증

### 4. 밸류에이션 (Margin of Safety)
- 1점: 심각한 고평가, 안전마진 전무
- 3점: 적정 가격
- 5점: 명백한 저평가, 큰 안전마진

## 출력 규칙

- **반드시 한국어로** 작성한다.
- 각 점수에 대해 **버크셔 서한의 어떤 원칙/사례를 적용했는지** 명시.
- 데이터가 부족하면 점수 대신 "N/A (정보 부족)"으로 표기.
- 추측이 필요한 부분은 "추정"이라고 명시.

## 안전 규칙 (절대 위반 금지)

- "매수/매도/보유" 같은 명시적 액션 권고를 하지 않는다.
- "내재가치 = $XXX" 같은 구체적 단정 가격을 제시하지 않는다.
  (대신 "안전마진 관점에서 현 가격이 어떻게 보이는지" 정성적으로 설명)
- 답변 마지막에 면책 문구를 포함한다:
  "본 분석은 교육·연구 목적이며 투자 권유가 아닙니다.
   실제 투자 결정은 본인의 책임입니다."

## 출력 형식

```
## 📌 [회사명] (TICKER) 분석

### 비즈니스 개요
(2-3문장)

### 평가

**1. 비즈니스 이해도: X/5**
- 근거: ...
- 적용한 버핏 원칙: ...

**2. 경제적 해자: X/5**
- 근거: ...
- 적용한 버핏 원칙: ...

**3. 경영진: X/5**
- 근거: ...
- 적용한 버핏 원칙: ...

**4. 밸류에이션: X/5**
- 근거: ...
- 적용한 버핏 원칙: ...

### 종합 평균: X.X / 5

### 🟢 강점
- ...

### 🔴 우려 사항
- ...

### 💬 버핏이라면 (서한 인용)
> "...(서한 원문 인용)..." (p.X)

이 인용이 이 회사에 어떻게 적용되는지: ...

---
⚠️ 본 분석은 교육·연구 목적이며 투자 권유가 아닙니다.
실제 투자 결정은 본인의 책임입니다.
```
"""

        user_message = f"""# 분석 대상
사용자 질문: {user_query}

# 리서치 결과 (사전 수집)
{market_data.get('raw_response', '정보 없음')}

# 버크셔 서한에서 검색된 관련 구절
{insights_text}

위 자료를 토대로, 당신의 내재화된 가치관으로 직접 평가하세요.
"""

        try:
            llm = ChatOpenAI(
                model="gpt-4o",
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.openai_api_key,  # 명시적 전달 (env 의존 제거)
            )
            response = llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ])
            analysis = response.content

            print(f"✓ 분석 완료 ({len(analysis)} 글자)")
            return {**state, "final_analysis": analysis}

        except Exception as e:
            print(f"❌ OpenAI API 오류: {str(e)}")
            return {
                **state,
                "final_analysis": f"분석 중 오류 발생: {str(e)}",
                "error": str(e)
            }

    def create_workflow(self):
        """워크플로우 생성"""
        workflow = StateGraph(InvestmentState)

        workflow.add_node("perplexity_research", self.perplexity_research_node)
        workflow.add_node("rag_wisdom", self.rag_buffett_wisdom_node)
        workflow.add_node("openai_analysis", self.openai_analysis_node)

        workflow.set_entry_point("perplexity_research")
        workflow.add_edge("perplexity_research", "rag_wisdom")
        workflow.add_edge("rag_wisdom", "openai_analysis")
        workflow.add_edge("openai_analysis", END)

        return workflow.compile()

    def analyze_stock(
        self,
        user_query: str,
        pdf_path: str = None,
        perplexity_max_tokens: int = 1500,
        perplexity_temperature: float = 0.2,
        openai_max_tokens: int = 2000,
        openai_temperature: float = 0.3
    ):
        """주식 분석 실행"""
        print("=" * 60)
        print("🎯 버핏 스타일 주식 분석 시작")
        print("=" * 60)

        print(f"pdf path: {pdf_path if pdf_path else 'None (RAG 비활성화)'}")
        if pdf_path:
            # 같은 PDF면 캐시 사용 (재임베딩 비용 절감)
            self.initialize_rag(pdf_path)

        app = self.create_workflow()

        initial_state = {
            "user_query": user_query,
            "market_data": {},
            "buffett_insights": [],
            "final_analysis": "",
            "error": "",
            "perplexity_max_tokens": perplexity_max_tokens,
            "perplexity_temperature": perplexity_temperature,
            "openai_max_tokens": openai_max_tokens,
            "openai_temperature": openai_temperature
        }

        result = app.invoke(initial_state)

        print("\n" + "=" * 60)
        print("📊 분석 결과")
        print("=" * 60)
        print(result["final_analysis"])

        if result.get("error"):
            print(f"\n⚠️ 경고: {result['error']}")

        return result

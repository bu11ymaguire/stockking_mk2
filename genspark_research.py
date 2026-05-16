# -*- coding: utf-8 -*-
"""
Genspark CLI(`gsk`)를 활용한 시장 리서치 모듈.
Perplexity API를 대체한다.

활용 도구:
  - gsk stock_price <ticker>: 정량 데이터 (P/E, ROE, FCF, DCF, 5년 시세 등)
  - gsk search <query>:       정성 정보 (뉴스, 분석 기사)

워크플로우:
  1. (선택) 사용자 질문에서 티커 추출
  2. stock_price로 수치 데이터 수집
  3. search로 정성 정보 수집
  4. 두 결과를 합쳐 버핏 관점 요약 텍스트로 변환

요약 단계는 GPT-4o(또는 호출자의 LLM)가 담당하므로,
본 모듈은 raw 데이터를 깔끔하게 반환만 한다.
"""

import json
import os
import re
import shutil
import subprocess
from typing import Optional


def _find_gsk() -> str:
    """gsk CLI 실행파일을 찾는다. PATH 우선, 없으면 알려진 위치 탐색."""
    # 1) PATH 검색 (.cmd, .exe 자동 인식)
    found = shutil.which("gsk")
    if found:
        return found

    # 2) 환경변수 GSK_PATH 우선
    if env_path := os.environ.get("GSK_PATH"):
        if os.path.exists(env_path):
            return env_path

    # 3) Genspark Claw bundled location (Windows)
    appdata = os.environ.get("APPDATA", "")
    candidates = [
        os.path.join(
            appdata,
            "Genspark Claw",
            "bundled-resources",
            "openclaw",
            "node_modules",
            ".bin",
            "gsk.cmd",
        ),
        # npm global 기본 위치
        os.path.join(appdata, "npm", "gsk.cmd"),
        os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Roaming", "npm", "gsk.cmd"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path

    return "gsk"  # 최후의 수단 (실패 시 명확한 에러 메시지 나옴)


GSK_CMD = _find_gsk()


class GenSparkError(Exception):
    """gsk CLI 호출 실패."""


def _run_gsk(args: list[str], timeout: int = 120) -> dict:
    """gsk 명령을 실행하고 JSON 결과를 반환한다."""
    # Windows .cmd 파일은 shell=True가 필요한 경우가 있음
    use_shell = GSK_CMD.lower().endswith(".cmd") or GSK_CMD.lower().endswith(".bat")

    try:
        if use_shell:
            # 인자에 공백 들어가는 경우 따옴표로 감싸기
            quoted_args = [f'"{a}"' if " " in a else a for a in args]
            cmd_str = f'"{GSK_CMD}" {" ".join(quoted_args)}'
            result = subprocess.run(
                cmd_str,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        else:
            result = subprocess.run(
                [GSK_CMD, *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
    except FileNotFoundError as e:
        raise GenSparkError(
            f"gsk CLI를 찾을 수 없습니다 (경로 시도: {GSK_CMD}). "
            f"'gsk --help'로 설치 확인하거나, "
            f"환경변수 GSK_PATH에 절대경로를 지정하세요."
        ) from e
    except subprocess.TimeoutExpired as e:
        raise GenSparkError(f"gsk 명령 타임아웃 ({timeout}s): {' '.join(args)}") from e

    if result.returncode != 0:
        raise GenSparkError(
            f"gsk 실패 (exit {result.returncode}): {result.stderr[:300]}"
        )

    # gsk는 [INFO] 같은 로그를 stdout 앞에 섞어 보낼 수 있음. JSON만 추출.
    stdout = result.stdout
    # JSON 시작 위치 찾기
    first_brace = stdout.find("{")
    if first_brace == -1:
        raise GenSparkError(f"gsk 응답에 JSON 없음: {stdout[:300]}")

    try:
        return json.loads(stdout[first_brace:])
    except json.JSONDecodeError as e:
        raise GenSparkError(f"gsk JSON 파싱 실패: {e}") from e


# ──────────────────────────────────────────────────────────────────────────
# 1. 티커 추출
# ──────────────────────────────────────────────────────────────────────────

# 흔한 티커 패턴 (2-5자 대문자)
_TICKER_PATTERN = re.compile(r"\b([A-Z]{2,5})\b")

# 한국어 종목명 → 티커 (확장 가능)
_KR_NAME_TO_TICKER = {
    "엔비디아": "NVDA",
    "테슬라": "TSLA",
    "애플": "AAPL",
    "마이크로소프트": "MSFT",
    "구글": "GOOGL",
    "알파벳": "GOOGL",
    "아마존": "AMZN",
    "메타": "META",
    "페이스북": "META",
    "삼성전자": "005930.KS",
    "sk하이닉스": "000660.KS",
    "코카콜라": "KO",
    "버크셔": "BRK-B",
    "버크셔해서웨이": "BRK-B",
    "월마트": "WMT",
    "디즈니": "DIS",
    "넷플릭스": "NFLX",
    "팔란티어": "PLTR",
}


def extract_ticker(query: str) -> Optional[str]:
    """
    사용자 질문에서 티커 후보를 추출.
    1) 대문자 2-5자 시퀀스 우선
    2) 한국어 종목명 매핑
    3) 못 찾으면 None
    """
    if not query:
        return None

    query_lower = query.lower().replace(" ", "")
    # 한국어 매핑
    for kr, ticker in _KR_NAME_TO_TICKER.items():
        if kr.lower() in query_lower:
            return ticker

    # 대문자 티커 추출 (일반 단어 제외)
    blacklist = {
        "AI", "CEO", "CFO", "ETF", "IPO", "USA", "USD", "AMD",  # AMD는 진짜 티커이긴 함
        "ROE", "ROI", "FCF", "GDP", "API", "RAG", "PDF",
    }
    candidates = [t for t in _TICKER_PATTERN.findall(query) if t not in blacklist]
    if candidates:
        return candidates[0]
    return None


# ──────────────────────────────────────────────────────────────────────────
# 2. 데이터 수집
# ──────────────────────────────────────────────────────────────────────────


def fetch_stock_data(ticker: str) -> dict:
    """
    gsk stock_price로 정량 데이터 수집.
    반환: profile, metrics, ratios만 추려서 반환 (historical은 너무 큼).
    """
    raw = _run_gsk(["stock_price", ticker])
    if raw.get("status") != "ok":
        raise GenSparkError(f"stock_price 실패: {raw.get('message')}")

    data = raw.get("data", {})
    return {
        "ticker": ticker,
        "profile": data.get("profile", {}),
        "metrics": data.get("metrics", {}),
        "ratios": (data.get("ratios") or [{}])[0],  # 최신 1개만
    }


def fetch_web_research(query: str, max_results: int = 6) -> dict:
    """
    gsk search로 정성 정보 수집.
    """
    raw = _run_gsk(["search", query])
    if raw.get("status") != "ok":
        raise GenSparkError(f"search 실패: {raw.get('message')}")

    data = raw.get("data", {})
    organic = (data.get("organic_results") or [])[:max_results]
    return {
        "query": query,
        "results": [
            {
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "snippet": r.get("snippet", ""),
                "date": r.get("date", ""),
            }
            for r in organic
        ],
        "related_questions": [
            {
                "question": q.get("question", ""),
                "snippet": q.get("snippet", ""),
            }
            for q in (data.get("related_questions") or [])[:3]
        ],
    }


# ──────────────────────────────────────────────────────────────────────────
# 3. 버핏 관점 텍스트 변환
# ──────────────────────────────────────────────────────────────────────────


def format_stock_data_for_llm(stock: dict) -> str:
    """수치 데이터를 LLM이 소화하기 좋은 텍스트로 변환."""
    if not stock:
        return "(주가 데이터 없음 — 티커 미확정)"

    p = stock.get("profile", {})
    m = stock.get("metrics", {})
    r = stock.get("ratios", {})

    lines = [f"## {p.get('companyName', stock.get('ticker'))} ({stock.get('ticker')})"]
    if p.get("sector") or p.get("industry"):
        lines.append(f"- 섹터/산업: {p.get('sector')} / {p.get('industry')}")
    if p.get("ceo"):
        lines.append(f"- CEO: {p.get('ceo')}")
    if p.get("fullTimeEmployees"):
        lines.append(f"- 직원 수: {p.get('fullTimeEmployees')}")
    if p.get("description"):
        desc = p["description"][:600]
        lines.append(f"- 사업 설명: {desc}...")

    # 시장 정보
    lines.append("\n### 시장 정보")
    if p.get("price"):
        lines.append(f"- 현재가: {p['price']} {p.get('currency', '')}")
    if p.get("mktCap"):
        mkt_b = p["mktCap"] / 1e9
        lines.append(f"- 시가총액: ${mkt_b:,.1f}B")
    if p.get("beta") is not None:
        lines.append(f"- Beta: {p['beta']}")
    if m.get("yearHigh") and m.get("yearLow"):
        lines.append(f"- 52주 범위: {m['yearLow']} - {m['yearHigh']}")
    if p.get("dcf"):
        lines.append(
            f"- DCF 추정 내재가치: {p['dcf']:.2f} "
            f"(시장가 대비 {((p['dcf'] - p.get('price', 0)) / max(p.get('price', 1), 0.01)) * 100:+.1f}%)"
        )

    # 버핏이 관심 가질 정량 지표
    lines.append("\n### 버핏 관점 핵심 지표")

    def fmt_pct(v):
        return f"{v * 100:.1f}%" if v is not None else "N/A"

    def fmt_num(v, digits=2):
        return f"{v:.{digits}f}" if v is not None else "N/A"

    if r:
        lines.append(f"- **ROE (자기자본이익률, TTM):** {fmt_pct(r.get('returnOnEquityTTM'))}")
        lines.append(f"- **ROA (총자산이익률, TTM):** {fmt_pct(r.get('returnOnAssetsTTM'))}")
        lines.append(f"- **ROIC (투하자본이익률, TTM):** {fmt_pct(r.get('returnOnCapitalEmployedTTM'))}")
        lines.append(f"- **영업이익률:** {fmt_pct(r.get('operatingProfitMarginTTM'))}")
        lines.append(f"- **순이익률:** {fmt_pct(r.get('netProfitMarginTTM'))}")
        lines.append(f"- **매출총이익률:** {fmt_pct(r.get('grossProfitMarginTTM'))}")

        lines.append(f"\n- **부채비율 (D/E):** {fmt_num(r.get('debtEquityRatioTTM'))}")
        lines.append(f"- **유동비율:** {fmt_num(r.get('currentRatioTTM'))}")
        lines.append(f"- **이자보상배율:** {fmt_num(r.get('interestCoverageTTM'), 1)}")

        lines.append(f"\n- **P/E:** {fmt_num(r.get('peRatioTTM'), 1)}")
        lines.append(f"- **P/B:** {fmt_num(r.get('priceToBookRatioTTM'), 1)}")
        lines.append(f"- **PEG:** {fmt_num(r.get('priceEarningsToGrowthRatioTTM'))}")
        lines.append(f"- **P/FCF:** {fmt_num(r.get('priceToFreeCashFlowsRatioTTM'), 1)}")
        lines.append(f"- **배당수익률:** {fmt_pct(r.get('dividendYielTTM'))}")
        lines.append(f"- **배당성향:** {fmt_pct(r.get('payoutRatioTTM'))}")

        lines.append(
            f"\n- **주당 영업현금흐름:** {fmt_num(r.get('operatingCashFlowPerShareTTM'))}"
        )
        lines.append(f"- **주당 잉여현금흐름:** {fmt_num(r.get('freeCashFlowPerShareTTM'))}")
        lines.append(f"- **주당 현금:** {fmt_num(r.get('cashPerShareTTM'))}")

    return "\n".join(lines)


def format_web_research_for_llm(web: dict) -> str:
    """검색 결과를 LLM이 소화하기 좋은 텍스트로 변환."""
    if not web or not web.get("results"):
        return "(웹 검색 결과 없음)"

    lines = [f"## 웹 검색 결과 (쿼리: {web.get('query', '')})"]
    for i, r in enumerate(web["results"], 1):
        lines.append(f"\n### [{i}] {r['title']}")
        if r["date"]:
            lines.append(f"- 게시일: {r['date']}")
        lines.append(f"- 출처: {r['url']}")
        lines.append(f"- 요약: {r['snippet']}")

    if web.get("related_questions"):
        lines.append("\n### 관련 질문 (시장의 관심사)")
        for q in web["related_questions"]:
            lines.append(f"- Q: {q['question']}")
            if q["snippet"]:
                lines.append(f"  A: {q['snippet'][:200]}")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────
# 4. 통합 리서치 (외부에서 호출하는 메인 함수)
# ──────────────────────────────────────────────────────────────────────────


def research(user_query: str) -> dict:
    """
    사용자 질문을 받아 정량+정성 리서치를 수행하고
    LLM에 던질 수 있는 통합 텍스트를 반환한다.

    반환:
      {
        "ticker": "NVDA" 또는 None,
        "stock_data": {...} 또는 None,
        "web_research": {...} 또는 None,
        "summary_text": "...LLM에 넘길 통합 텍스트...",
        "errors": ["에러 메시지 리스트"]
      }
    """
    errors = []
    ticker = extract_ticker(user_query)
    stock_data = None
    web_research_data = None

    # 1) 정량 데이터 (티커가 잡혔을 때만)
    if ticker:
        try:
            print(f"📊 정량 데이터 수집 중: {ticker}")
            stock_data = fetch_stock_data(ticker)
            print(f"✓ stock_price 성공: {stock_data['profile'].get('companyName', ticker)}")
        except GenSparkError as e:
            err = f"stock_price 실패 ({ticker}): {e}"
            print(f"⚠️ {err}")
            errors.append(err)

    # 2) 정성 정보 (항상 시도)
    try:
        # 검색어를 회사명으로 보강
        search_query = user_query
        if stock_data and stock_data["profile"].get("companyName"):
            company = stock_data["profile"]["companyName"]
            search_query = f"{company} {ticker} financial analysis moat ROE"
        print(f"🔍 웹 검색 중: {search_query[:80]}")
        web_research_data = fetch_web_research(search_query)
        print(f"✓ search 성공: {len(web_research_data['results'])}개 결과")
    except GenSparkError as e:
        err = f"web search 실패: {e}"
        print(f"⚠️ {err}")
        errors.append(err)

    # 3) 통합 텍스트
    parts = []
    if stock_data:
        parts.append(format_stock_data_for_llm(stock_data))
    if web_research_data:
        parts.append(format_web_research_for_llm(web_research_data))

    if not parts:
        summary_text = (
            "⚠️ 정량 데이터와 웹 검색 모두 실패했습니다. "
            "사용자 질문만으로 분석을 시도합니다.\n"
            f"사용자 질문: {user_query}"
        )
    else:
        summary_text = "\n\n---\n\n".join(parts)

    return {
        "ticker": ticker,
        "stock_data": stock_data,
        "web_research": web_research_data,
        "summary_text": summary_text,
        "errors": errors,
    }

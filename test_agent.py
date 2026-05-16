# test_agent.py
import os
from agent import InvestmentAgent


def main():
    """CLI에서 API 키를 입력받아 에이전트 테스트"""
    print("=" * 60)
    print("🧪 InvestmentAgent 테스트")
    print("=" * 60)

    # API 키 입력받기
    google_api_key = input("\n🔑 Google Gemini API 키를 입력하세요: ").strip()

    if not google_api_key:
        print("❌ Gemini API 키를 입력해야 합니다.")
        print("   발급: https://aistudio.google.com/apikey  (무료)")
        return

    # PDF 파일 경로 입력
    pdf_path = input("\n📄 PDF 파일 경로를 입력하세요 (기본값: berkshire_letters.pdf): ").strip()
    if not pdf_path:
        pdf_path = "berkshire_letters.pdf"

    # PDF 파일 존재 확인
    if not os.path.exists(pdf_path):
        print(f"⚠️ 경고: PDF 파일을 찾을 수 없습니다: {pdf_path}")
        use_pdf = input("PDF 없이 계속하시겠습니까? (y/n): ").strip().lower()
        if use_pdf != 'y':
            return
        pdf_path = None

    # 에이전트 초기화
    try:
        agent = InvestmentAgent(
            google_api_key=google_api_key,
            pdf_path=pdf_path,
        )
        print("\n✓ 에이전트 초기화 성공")
    except Exception as e:
        print(f"\n❌ 에이전트 초기화 실패: {e}")
        return

    # 테스트 쿼리 입력
    print("\n" + "=" * 60)
    print("📝 분석할 주식을 입력하세요")
    print("예시: 애플 주식 분석해줘, TSLA는 어때?, Microsoft 투자 의견")
    print("=" * 60)

    user_query = input("\n질문: ").strip()
    if not user_query:
        user_query = "애플 주식에 대해 분석해줘"
        print(f"기본 질문 사용: {user_query}")

    # 파라미터 설정
    print("\n⚙️ Gemini 파라미터 설정 (Enter 키로 기본값 사용)")

    try:
        gemini_max_tokens = input("max_tokens (기본: 2000): ").strip()
        gemini_max_tokens = int(gemini_max_tokens) if gemini_max_tokens else 2000

        gemini_temperature = input("temperature (기본: 0.3): ").strip()
        gemini_temperature = float(gemini_temperature) if gemini_temperature else 0.3
    except ValueError as e:
        print(f"⚠️ 잘못된 입력입니다. 기본값을 사용합니다: {e}")
        gemini_max_tokens = 2000
        gemini_temperature = 0.3

    # 분석 실행
    print("\n🚀 분석을 시작합니다...\n")

    try:
        # 키 이름은 하위 호환 (analyze_stock 시그니처)
        result = agent.analyze_stock(
            user_query=user_query,
            pdf_path=pdf_path,
            openai_max_tokens=gemini_max_tokens,
            openai_temperature=gemini_temperature,
        )

        # 결과 요약
        print("\n" + "=" * 60)
        print("✅ 테스트 완료")
        print("=" * 60)
        print(f"📌 질문: {result['user_query']}")
        print(f"📊 수집된 인사이트: {len(result['buffett_insights'])}개")
        print(f"📈 분석 길이: {len(result['final_analysis'])} 글자")

        if result.get('error'):
            print(f"⚠️ 에러: {result['error']}")

    except Exception as e:
        print(f"\n❌ 분석 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

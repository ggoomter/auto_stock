"""
삼성전자 전략 비교 테스트 (2024년)

100만원으로 삼성전자를 2024년에 구매했을 때
어떤 대가 전략이 가장 좋은 성과를 냈는지 테스트

캐싱 시스템 검증:
- 첫 실행: 백테스트 수행 + 캐시 저장
- 두 번째 실행: 캐시에서 즉시 반환
"""
import requests
import json
import time
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"
RESULTS_DIR = Path("test_results/samsung_2024")


def print_section(title: str):
    """섹션 제목 출력"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_samsung_strategy_comparison():
    """삼성전자 전략 비교 테스트"""
    print_section("삼성전자 전략 비교 테스트 시작")

    # 테스트 파라미터
    payload = {
        "strategy_names": [
            "buffett",      # Warren Buffett (가치투자)
            "lynch",        # Peter Lynch (성장주)
            "graham",       # Benjamin Graham (깊은 가치)
            "dalio",        # Ray Dalio (올웨더)
            "livermore",    # Jesse Livermore (추세추종)
            "soros",        # George Soros (매크로)
            "druckenmiller", # Stanley Druckenmiller (성장+매크로)
            "oneil"         # William O'Neil (CANSLIM)
        ],
        "symbols": ["005930.KS"],  # 삼성전자
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "initial_capital": 1000000  # 100만원
    }

    print(f"\n📋 테스트 설정:")
    print(f"   - 종목: 삼성전자 (005930.KS)")
    print(f"   - 기간: 2024-01-01 ~ 2024-12-31")
    print(f"   - 초기 자본: {payload['initial_capital']:,}원")
    print(f"   - 테스트 전략: {len(payload['strategy_names'])}개")
    for strategy in payload['strategy_names']:
        print(f"     * {strategy}")

    # 첫 번째 실행 (백테스트 + 캐싱)
    print_section("1차 실행: 백테스트 수행 + 캐시 저장")

    start_time = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/compare-strategies",
            json=payload,
            timeout=300  # 5분 타임아웃
        )
        first_run_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ 1차 실행 성공")
            print(f"   - 실행 시간: {first_run_time:.2f}초")
            print(f"   - 성공한 전략: {len(data['results'])}개")

            # 결과 저장
            save_results(data, "first_run")

            return data, first_run_time
        else:
            print(f"❌ 1차 실행 실패: {response.status_code}")
            print(f"   - 에러: {response.text}")
            return None, None

    except Exception as e:
        print(f"❌ 1차 실행 오류: {e}")
        return None, None


def test_cached_request():
    """캐싱 검증: 동일한 요청 재실행"""
    print_section("2차 실행: 캐시에서 즉시 반환")

    # 동일한 파라미터로 재요청
    payload = {
        "strategy_names": [
            "buffett", "lynch", "graham", "dalio",
            "livermore", "soros", "druckenmiller", "oneil"
        ],
        "symbols": ["005930.KS"],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "initial_capital": 1000000
    }

    start_time = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/compare-strategies",
            json=payload,
            timeout=30  # 캐시 사용 시 즉시 반환 기대
        )
        second_run_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ 2차 실행 성공 (캐시 사용)")
            print(f"   - 실행 시간: {second_run_time:.2f}초")
            print(f"   - 성공한 전략: {len(data['results'])}개")

            # 결과 저장
            save_results(data, "second_run_cached")

            return data, second_run_time
        else:
            print(f"❌ 2차 실행 실패: {response.status_code}")
            print(f"   - 에러: {response.text}")
            return None, None

    except Exception as e:
        print(f"❌ 2차 실행 오류: {e}")
        return None, None


def save_results(data: dict, run_type: str):
    """결과를 파일로 저장"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # JSON 전체 결과 저장
    output_file = RESULTS_DIR / f"{run_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 결과 저장: {output_file}")


def analyze_results(data: dict):
    """결과 분석 및 출력"""
    if not data or not data.get('results'):
        print("❌ 분석할 결과가 없습니다.")
        return

    print_section("전략별 성과 분석")

    results = data['results']
    best_strategy = data.get('best_strategy', 'unknown')

    # 성과 지표 테이블 출력
    print(f"\n{'전략명':<20} {'CAGR':<10} {'Sharpe':<10} {'MaxDD':<10} {'승률':<10} {'거래수':<10}")
    print("-" * 80)

    for result in results:
        name = result['strategy_name']
        metrics = result['metrics']

        print(
            f"{name:<20} "
            f"{metrics['CAGR']:>8.2f}% "
            f"{metrics['Sharpe']:>9.2f} "
            f"{metrics['MaxDD']:>8.2f}% "
            f"{metrics['WinRate']:>8.2f}% "
            f"{metrics['TotalTrades']:>9}"
        )

    # 최고 성과 전략 강조
    print("\n" + "=" * 80)
    print(f"🏆 최고 성과 전략 (CAGR 기준): {best_strategy.upper()}")

    best_result = next((r for r in results if r['strategy_name'] == best_strategy), None)
    if best_result:
        print(f"\n📊 {best_strategy.upper()} 상세 성과:")
        print(f"   - 최종 자본: {best_result['final_equity']:,.0f}원")
        print(f"   - 총 수익률: {best_result['total_return_pct']:.2f}%")
        print(f"   - CAGR: {best_result['metrics']['CAGR']:.2f}%")
        print(f"   - 샤프 비율: {best_result['metrics']['Sharpe']:.2f}")
        print(f"   - 최대 낙폭: {best_result['metrics']['MaxDD']:.2f}%")
        print(f"   - 승률: {best_result['metrics']['WinRate']:.2f}%")
        print(f"   - 총 거래 수: {best_result['metrics']['TotalTrades']}회")

    print("=" * 80)

    # 요약 저장
    save_summary(data)


def save_summary(data: dict):
    """결과 요약 저장"""
    summary_file = RESULTS_DIR / "summary.txt"

    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("삼성전자 전략 비교 테스트 결과 요약 (2024년)\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"테스트 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"종목: 삼성전자 (005930.KS)\n")
        f.write(f"기간: {data['comparison_period']['start']} ~ {data['comparison_period']['end']}\n")
        f.write(f"초기 자본: 1,000,000원\n\n")

        f.write("-" * 80 + "\n")
        f.write(f"{'전략명':<20} {'CAGR':<10} {'Sharpe':<10} {'MaxDD':<10} {'승률':<10}\n")
        f.write("-" * 80 + "\n")

        for result in data['results']:
            name = result['strategy_name']
            metrics = result['metrics']
            f.write(
                f"{name:<20} "
                f"{metrics['CAGR']:>8.2f}% "
                f"{metrics['Sharpe']:>9.2f} "
                f"{metrics['MaxDD']:>8.2f}% "
                f"{metrics['WinRate']:>8.2f}%\n"
            )

        f.write("\n" + "=" * 80 + "\n")
        f.write(f"🏆 최고 성과 전략: {data['best_strategy'].upper()}\n")
        f.write("=" * 80 + "\n")

    print(f"\n📄 요약 파일 저장: {summary_file}")


def compare_performance(first_time: float, second_time: float):
    """캐싱 성능 비교"""
    if first_time is None or second_time is None:
        return

    print_section("캐싱 성능 비교")

    speedup = first_time / second_time if second_time > 0 else 0
    time_saved = first_time - second_time

    print(f"\n⏱️  실행 시간 비교:")
    print(f"   - 1차 실행 (백테스트): {first_time:.2f}초")
    print(f"   - 2차 실행 (캐시): {second_time:.2f}초")
    print(f"   - 속도 향상: {speedup:.1f}배 빠름")
    print(f"   - 절약된 시간: {time_saved:.2f}초")

    if speedup > 10:
        print(f"\n✅ 캐싱이 매우 효과적입니다! ({speedup:.1f}배 빠름)")
    elif speedup > 5:
        print(f"\n✅ 캐싱이 효과적입니다! ({speedup:.1f}배 빠름)")
    else:
        print(f"\n⚠️  캐싱 효과가 제한적입니다. ({speedup:.1f}배 빠름)")


def run_full_test():
    """전체 테스트 실행"""
    print("\n" + "🚀" * 30)
    print("  삼성전자 전략 비교 테스트 (2024년, 100만원)")
    print("🚀" * 30)

    print(f"\n📅 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1차 실행: 백테스트 + 캐싱
    first_data, first_time = test_samsung_strategy_comparison()

    if first_data is None:
        print("\n❌ 1차 실행 실패로 테스트 중단")
        return

    # 결과 분석
    analyze_results(first_data)

    # 잠시 대기
    print("\n⏳ 2초 대기 후 캐싱 테스트 시작...")
    time.sleep(2)

    # 2차 실행: 캐시 검증
    second_data, second_time = test_cached_request()

    # 성능 비교
    if first_time and second_time:
        compare_performance(first_time, second_time)

    print_section("테스트 완료")
    print(f"\n✅ 모든 테스트가 완료되었습니다!")
    print(f"📁 결과 저장 위치: {RESULTS_DIR.absolute()}")
    print(f"📅 테스트 종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n⚠️  주의사항:")
    print("   1. 백엔드 서버가 실행 중이어야 합니다 (http://localhost:8000)")
    print("   2. START.bat을 실행한 후 이 스크립트를 실행하세요.")
    print("   3. 첫 실행은 시간이 걸릴 수 있습니다 (백테스트 수행)")
    print("   4. 두 번째 실행은 캐시를 사용하여 즉시 반환됩니다.\n")

    input("계속하려면 Enter를 누르세요...")

    run_full_test()

    print("\n\n💡 추가 정보:")
    print("   - Swagger UI: http://localhost:8000/docs")
    print("   - 캐시 위치: backend/cache/backtest_results/")
    print("   - 결과 위치: tests/test_results/samsung_2024/")

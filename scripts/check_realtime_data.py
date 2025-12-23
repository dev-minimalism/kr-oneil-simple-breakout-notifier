#!/usr/bin/env python3
"""
pykrx 실시간 데이터 테스트 스크립트

장중(09:00~15:30)에 실행하여 pykrx가 실시간 데이터를 반환하는지 확인합니다.

사용법:
    python test_pykrx_realtime.py
"""
from datetime import datetime, timedelta
from pykrx import stock

def test_realtime_data():
    """pykrx 실시간 데이터 테스트"""
    ticker = "005930"  # 삼성전자

    now = datetime.now()
    print(f"=" * 60)
    print(f"🕐 현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 테스트 종목: {ticker} (삼성전자)")
    print(f"=" * 60)

    # 최근 7일 데이터 조회
    end_date = now
    start_date = end_date - timedelta(days=7)

    df = stock.get_market_ohlcv_by_date(
        start_date.strftime("%Y%m%d"),
        end_date.strftime("%Y%m%d"),
        ticker
    )

    print(f"\n📅 조회 범위: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"\n📈 반환된 데이터 (최근 5일):")
    print("-" * 60)

    if df.empty:
        print("❌ 데이터가 비어있습니다!")
        return

    # 최근 5일 데이터 출력
    print(df.tail(5).to_string())

    print(f"\n" + "-" * 60)
    print(f"📊 마지막 행 (df.iloc[-1]) 분석:")
    print(f"   날짜: {df.index[-1]}")
    print(f"   종가: {df['종가'].iloc[-1]:,}원")
    print(f"   거래량: {df['거래량'].iloc[-1]:,}")

    # 오늘 데이터 존재 여부 확인
    today = now.strftime('%Y-%m-%d')
    last_date = df.index[-1].strftime('%Y-%m-%d') if hasattr(df.index[-1], 'strftime') else str(df.index[-1])[:10]

    print(f"\n🔍 분석:")
    if last_date == today:
        print(f"   ✅ 오늘({today}) 데이터가 존재합니다.")
        print(f"   ⚠️  하지만 이게 실시간 가격인지 확인 필요!")
        print(f"   (네이버/다음 금융에서 현재가와 비교해보세요)")
    else:
        print(f"   ❌ 오늘({today}) 데이터가 없습니다!")
        print(f"   마지막 데이터 날짜: {last_date}")
        print(f"   → 장중에도 실시간 데이터가 반환되지 않습니다!")

    # 장중 여부 확인
    hour = now.hour
    minute = now.minute
    is_market_open = 9 <= hour < 16 and now.weekday() < 5

    print(f"\n⏰ 현재 장 상태:")
    if is_market_open:
        print(f"   🟢 장중 (09:00~15:30)")
    else:
        print(f"   🔴 장외 시간")

    # 추가 테스트: 실시간 시세 조회 시도
    print(f"\n" + "=" * 60)
    print("📡 추가 테스트: 실시간 시세 조회")
    print("-" * 60)

    try:
        # 오늘 날짜로만 조회
        today_str = now.strftime("%Y%m%d")
        df_today = stock.get_market_ohlcv_by_date(today_str, today_str, ticker)

        if df_today.empty:
            print(f"   ❌ 오늘 데이터만 조회 시 비어있음")
        else:
            print(f"   📊 오늘 데이터:")
            print(f"   {df_today.to_string()}")
    except Exception as e:
        print(f"   ❌ 조회 실패: {e}")

    # 결론
    print(f"\n" + "=" * 60)
    print("📋 결론:")
    print("-" * 60)
    print("""
pykrx는 KRX(한국거래소) 공시 데이터를 스크래핑하는 라이브러리입니다.
- 장중에는 오늘 데이터가 없거나, 있어도 시가/저가/고가만 있을 수 있음
- 실시간 현재가를 얻으려면 다른 방법이 필요합니다:
  1. 증권사 API (키움, 이베스트, 한투 등)
  2. 네이버/다음 금융 스크래핑
  3. Yahoo Finance API (yfinance)
""")


if __name__ == "__main__":
    test_realtime_data()

#!/usr/bin/env python3
"""
전체 워치리스트 백테스트

최근 3주간 각 종목에서 신호가 발생할 수 있었는지 확인합니다.

사용법:
    python test_backtest_all.py
"""
from datetime import datetime, timedelta
import numpy as np
from pykrx import stock


def backtest_signals():
    """전체 워치리스트 백테스트"""
    # .env의 기본 워치리스트
    tickers = [
        "005930", "000660", "035420", "035720",
        "373220", "086520", "247540", "066970",
        "068270", "091990", "207940", "326030",
        "005380", "000270", "051910", "006400",
        "096770", "009540", "010140"
    ]

    volume_surge_min = 50  # 기본값
    breakout_max = 5  # 기본값

    print(f"=" * 70)
    print(f"📜 최근 21일(3주) 백테스트")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⚙️  조건: 거래량 ≥{volume_surge_min}%, 돌파율 0~{breakout_max}%")
    print(f"=" * 70)

    total_signals = 0
    signal_details = []

    for ticker in tickers:
        name = stock.get_market_ticker_name(ticker)
        print(f"\n🔍 {name} ({ticker})...", end=" ", flush=True)

        # 데이터 조회 (60일 + 21일 = 81일)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        df = stock.get_market_ohlcv_by_date(
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
            ticker
        )

        if df.empty or len(df) < 50:
            print("❌ 데이터 부족")
            continue

        df = df.rename(columns={
            '시가': 'Open', '고가': 'High', '저가': 'Low',
            '종가': 'Close', '거래량': 'Volume'
        })

        signals = 0
        # 최근 21일 백테스트
        for i in range(len(df) - 21, len(df)):
            if i < 30:
                continue

            window = df.iloc[i-30:i+1]
            recent = window.copy()

            avg_volume = recent['Volume'].iloc[:-1].mean()
            current_volume = recent['Volume'].iloc[-1]
            volume_surge = (current_volume / avg_volume - 1) * 100

            close = recent['Close'].values
            current_price = close[-1]
            resistance = np.max(close[-20:-1])

            breakout = current_price > resistance
            breakout_pct = ((current_price - resistance) / resistance) * 100

            is_signal = (
                breakout and
                volume_surge >= volume_surge_min and
                0 < breakout_pct <= breakout_max
            )

            if is_signal:
                date = df.index[i].strftime('%Y-%m-%d')
                signal_details.append({
                    'date': date,
                    'ticker': ticker,
                    'name': name,
                    'breakout_pct': breakout_pct,
                    'volume_surge': volume_surge,
                })
                signals += 1

        if signals > 0:
            print(f"✅ {signals}회 신호 발생")
        else:
            print(f"⚪ 신호 없음")

        total_signals += signals

    print(f"\n{'=' * 70}")
    print(f"📊 요약")
    print(f"{'=' * 70}")
    print(f"   총 {len(tickers)}개 종목에서 3주간 {total_signals}회 신호 발생")

    if signal_details:
        print(f"\n📋 발생한 신호 상세:")
        for s in signal_details:
            print(f"   {s['date']}: {s['name']}({s['ticker']}) "
                  f"돌파 {s['breakout_pct']:+.2f}%, 거래량 {s['volume_surge']:+.1f}%")
    else:
        print(f"\n⚠️  3주간 신호가 전혀 없었습니다!")
        print(f"   → 조건이 너무 엄격합니다. 조정이 필요합니다.")

    # 조건 완화 테스트
    print(f"\n{'=' * 70}")
    print(f"🔧 조건 완화 테스트 (거래량 20%, 돌파율 0~10%)")
    print(f"{'=' * 70}")

    relaxed_volume_min = 20
    relaxed_breakout_max = 10
    relaxed_signals = 0

    for ticker in tickers:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        df = stock.get_market_ohlcv_by_date(
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
            ticker
        )

        if df.empty or len(df) < 50:
            continue

        df = df.rename(columns={
            '시가': 'Open', '고가': 'High', '저가': 'Low',
            '종가': 'Close', '거래량': 'Volume'
        })

        for i in range(len(df) - 21, len(df)):
            if i < 30:
                continue

            window = df.iloc[i-30:i+1]
            recent = window.copy()

            avg_volume = recent['Volume'].iloc[:-1].mean()
            current_volume = recent['Volume'].iloc[-1]
            volume_surge = (current_volume / avg_volume - 1) * 100

            close = recent['Close'].values
            current_price = close[-1]
            resistance = np.max(close[-20:-1])

            breakout = current_price > resistance
            breakout_pct = ((current_price - resistance) / resistance) * 100

            is_signal = (
                breakout and
                volume_surge >= relaxed_volume_min and
                0 < breakout_pct <= relaxed_breakout_max
            )

            if is_signal:
                relaxed_signals += 1

    print(f"   완화된 조건으로 3주간 {relaxed_signals}회 신호 발생")


if __name__ == "__main__":
    backtest_signals()

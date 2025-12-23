#!/usr/bin/env python3
"""
신호 감지 테스트 스크립트

실제로 신호 감지 로직이 어떻게 동작하는지 확인합니다.

사용법:
    python test_signal_detection.py
"""
from datetime import datetime, timedelta
import numpy as np
from pykrx import stock


def test_signal_detection():
    """신호 감지 로직 테스트"""
    tickers = ["005930", "000660", "035720"]  # 삼성전자, SK하이닉스, 카카오
    volume_surge_min = 50  # 설정값
    breakout_max = 5  # 설정값

    print(f"=" * 70)
    print(f"🔍 신호 감지 로직 테스트")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 70)

    for ticker in tickers:
        print(f"\n{'─' * 70}")
        name = stock.get_market_ticker_name(ticker)
        print(f"📊 {name} ({ticker})")
        print(f"{'─' * 70}")

        # 데이터 조회
        end_date = datetime.now()
        start_date = end_date - timedelta(days=120)
        df = stock.get_market_ohlcv_by_date(
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
            ticker
        )

        if df.empty or len(df) < 30:
            print(f"   ❌ 데이터 부족")
            continue

        # 컬럼명 변환
        df = df.rename(columns={
            '시가': 'Open', '고가': 'High', '저가': 'Low',
            '종가': 'Close', '거래량': 'Volume'
        })

        recent = df.tail(30).copy()

        # 거래량 분석
        avg_volume = recent['Volume'].iloc[:-1].mean()
        current_volume = recent['Volume'].iloc[-1]
        volume_surge = (current_volume / avg_volume - 1) * 100

        print(f"\n   📈 거래량 분석:")
        print(f"      오늘 거래량: {current_volume:,.0f}")
        print(f"      29일 평균: {avg_volume:,.0f}")
        print(f"      거래량 증가율: {volume_surge:+.1f}%")
        print(f"      필요 증가율: ≥{volume_surge_min}%")
        if volume_surge >= volume_surge_min:
            print(f"      ✅ 거래량 조건 충족")
        else:
            print(f"      ❌ 거래량 조건 미충족 (차이: {volume_surge_min - volume_surge:.1f}%p)")

        # 돌파 분석
        close = recent['Close'].values
        current_price = close[-1]
        resistance = np.max(close[-20:-1])  # 최근 19일 최고가

        breakout = current_price > resistance
        breakout_pct = ((current_price - resistance) / resistance) * 100

        print(f"\n   📊 돌파 분석:")
        print(f"      현재가: {current_price:,.0f}원")
        print(f"      저항선 (19일 최고): {resistance:,.0f}원")
        print(f"      돌파 여부: {'✅ 돌파' if breakout else '❌ 미돌파'}")
        print(f"      돌파율: {breakout_pct:+.2f}%")
        print(f"      필요 조건: 0% < 돌파율 ≤ {breakout_max}%")
        if breakout and 0 < breakout_pct <= breakout_max:
            print(f"      ✅ 돌파 조건 충족")
        else:
            if not breakout:
                print(f"      ❌ 아직 저항선 아래")
            elif breakout_pct > breakout_max:
                print(f"      ❌ 돌파율 초과 ({breakout_pct:.1f}% > {breakout_max}%)")
            else:
                print(f"      ❌ 돌파 조건 미충족")

        # 최종 신호 판정
        print(f"\n   🎯 최종 판정:")
        is_signal = (
            breakout and
            volume_surge >= volume_surge_min and
            0 < breakout_pct <= breakout_max
        )

        if is_signal:
            print(f"      ✅ 신호 발생!")
        else:
            reasons = []
            if not breakout:
                reasons.append("저항선 미돌파")
            if volume_surge < volume_surge_min:
                reasons.append(f"거래량 부족 ({volume_surge:+.1f}% < {volume_surge_min}%)")
            if breakout and (breakout_pct <= 0 or breakout_pct > breakout_max):
                reasons.append(f"돌파율 범위 벗어남 ({breakout_pct:.1f}%)")
            print(f"      ❌ 신호 없음: {', '.join(reasons)}")

    # 최근 30일간 신호가 발생할 수 있었는지 백테스트
    print(f"\n{'=' * 70}")
    print(f"📜 최근 30일 백테스트 (삼성전자)")
    print(f"{'=' * 70}")

    ticker = "005930"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    df = stock.get_market_ohlcv_by_date(
        start_date.strftime("%Y%m%d"),
        end_date.strftime("%Y%m%d"),
        ticker
    )
    df = df.rename(columns={
        '시가': 'Open', '고가': 'High', '저가': 'Low',
        '종가': 'Close', '거래량': 'Volume'
    })

    signals_found = 0
    for i in range(30, len(df)):
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
            print(f"   ✅ {date}: 돌파 {breakout_pct:+.2f}%, 거래량 {volume_surge:+.1f}%")
            signals_found += 1

    print(f"\n   📊 최근 60일간 삼성전자 신호 횟수: {signals_found}회")
    if signals_found == 0:
        print(f"   ⚠️  조건이 너무 엄격할 수 있습니다!")


if __name__ == "__main__":
    test_signal_detection()

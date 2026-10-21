"""한국 주식 데이터 수집"""
from datetime import datetime, timedelta

import pandas as pd
from pykrx import stock


def get_kr_stock_name(ticker: str) -> str:
    """
    한국 주식 종목명 가져오기

    Args:
        ticker: 종목 코드 (예: "005930")

    Returns:
        종목명 또는 ticker
    """
    try:
        name = stock.get_market_ticker_name(ticker)
        return name if name else ticker
    except:
        return ticker


def get_kr_stock_data(ticker: str, days: int = 120) -> pd.DataFrame | None:
    """
    한국 주식 데이터 가져오기

    Args:
        ticker: 종목 코드 (예: "005930")
        days: 조회할 일수

    Returns:
        OHLCV 데이터프레임 또는 None
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        df = stock.get_market_ohlcv_by_date(
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
            ticker
        )

        if df.empty:
            return None

        column_mapping = {
            '시가': 'Open',
            '고가': 'High',
            '저가': 'Low',
            '종가': 'Close',
            '거래량': 'Volume'
        }

        df = df.rename(columns=column_mapping)
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df = df[required_columns]

        return df
    except Exception as e:
        print(f"❌ {ticker} 데이터 조회 실패: {e}")
        return None


def get_kr_stock_data_by_date(ticker: str, start_date: str, end_date: str) -> pd.DataFrame | None:
    """
    한국 주식 데이터 기간별 조회

    Args:
        ticker: 종목 코드
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)

    Returns:
        OHLCV 데이터프레임 또는 None
    """
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').strftime("%Y%m%d")
        end = datetime.strptime(end_date, '%Y-%m-%d').strftime("%Y%m%d")

        df = stock.get_market_ohlcv_by_date(start, end, ticker)
        if df.empty:
            return None

        column_mapping = {
            '시가': 'Open',
            '고가': 'High',
            '저가': 'Low',
            '종가': 'Close',
            '거래량': 'Volume'
        }
        df = df.rename(columns=column_mapping)
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        print(f"❌ {ticker} 데이터 조회 실패: {e}")
        return None

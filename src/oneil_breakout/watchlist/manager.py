"""워치리스트 관리자"""
import json
import os
from datetime import datetime
from typing import List

from pykrx import stock


class WatchlistManager:
    """감시 종목 관리 클래스"""

    def __init__(
        self,
        watchlist_file: str = "watchlist.json",
        default_stocks: List[str] | None = None
    ):
        """
        Args:
            watchlist_file: 감시 종목 저장 파일 경로
            default_stocks: 기본 종목 리스트
        """
        self.watchlist_file = watchlist_file
        self.default_stocks = default_stocks or ["005930", "000660", "035420"]
        self.watchlist = self._load()

    def _load(self) -> List[str]:
        """감시 종목 파일에서 로드"""
        if os.path.exists(self.watchlist_file):
            try:
                with open(self.watchlist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 기존 형식 호환 (kr 키가 있으면 사용, 없으면 stocks 사용)
                    return data.get('kr', data.get('stocks', []))
            except Exception as e:
                print(f"⚠️  감시 종목 로드 실패: {e}")

        return self.default_stocks.copy()

    def _save(self) -> bool:
        """감시 종목 파일에 저장"""
        try:
            data = {
                'kr': self.watchlist,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.watchlist_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 감시 종목 저장 실패: {e}")
            return False

    def add(self, ticker: str) -> str:
        """
        종목 추가

        Args:
            ticker: 종목 코드

        Returns:
            결과 메시지
        """
        ticker = ticker.strip()
        if ticker in self.watchlist:
            try:
                name = stock.get_market_ticker_name(ticker)
                return f"⚠️  {name}({ticker})는 이미 감시 중입니다."
            except:
                return f"⚠️  {ticker}는 이미 감시 중입니다."

        self.watchlist.append(ticker)
        if self._save():
            try:
                name = stock.get_market_ticker_name(ticker)
                return f"✅ 🇰🇷 {name}({ticker}) 추가 완료!\n현재 감시 종목: {len(self.watchlist)}개"
            except:
                return f"✅ 🇰🇷 {ticker} 추가 완료!\n현재 감시 종목: {len(self.watchlist)}개"
        else:
            self.watchlist.remove(ticker)
            return "❌ 저장 실패"

    # Alias for backward compatibility
    def add_kr(self, ticker: str) -> str:
        return self.add(ticker)

    def remove(self, ticker: str) -> str:
        """
        종목 삭제

        Args:
            ticker: 종목 코드

        Returns:
            결과 메시지
        """
        ticker = ticker.strip()
        if ticker not in self.watchlist:
            return f"⚠️  {ticker}는 감시 목록에 없습니다."

        try:
            name = stock.get_market_ticker_name(ticker)
            stock_display = f"{name}({ticker})"
        except:
            stock_display = ticker

        self.watchlist.remove(ticker)
        if self._save():
            return f"✅ 🇰🇷 {stock_display} 삭제 완료!\n현재 감시 종목: {len(self.watchlist)}개"
        else:
            self.watchlist.append(ticker)
            return "❌ 저장 실패"

    # Alias for backward compatibility
    def remove_kr(self, ticker: str) -> str:
        return self.remove(ticker)

    def get_all(self) -> List[str]:
        """모든 감시 종목 조회"""
        return self.watchlist.copy()

    # Alias for backward compatibility
    def get_kr(self) -> List[str]:
        return self.get_all()

    def count(self) -> int:
        """종목 개수"""
        return len(self.watchlist)

    # Alias for backward compatibility
    def count_kr(self) -> int:
        return self.count()

    def format_list_message(self) -> str:
        """
        감시 종목 목록 메시지 포맷팅

        Returns:
            포맷된 HTML 메시지
        """
        msg = f"📊 <b>현재 감시 종목</b> ({len(self.watchlist)}개)\n\n"

        if self.watchlist:
            kr_names = []
            for ticker in self.watchlist:
                try:
                    name = stock.get_market_ticker_name(ticker)
                    kr_names.append(f"{name}({ticker})")
                except:
                    kr_names.append(ticker)
            msg += ", ".join(kr_names)
        else:
            msg += "없음"

        return msg
"""포지션 관리자 - DB 또는 JSON 파일 지원"""
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Callable, Optional

from ..database import DatabaseConnection, Position, Signal, PositionStatus
from ..config import DatabaseSettings


class BasePositionManager(ABC):
    """포지션 관리자 추상 베이스 클래스"""

    def __init__(
        self,
        stop_loss_pct: float = -8.0,
        take_profit_pct: float = 20.0,
        max_holding_days: int = 30
    ):
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_holding_days = max_holding_days

    @abstractmethod
    def add(self, ticker: str, name: str, entry_price: float, pattern: str, signal: Dict) -> bool:
        """포지션 추가"""
        pass

    @abstractmethod
    def remove(self, ticker: str) -> bool:
        """포지션 제거"""
        pass

    @abstractmethod
    def get(self, ticker: str) -> Optional[Dict]:
        """포지션 조회"""
        pass

    @abstractmethod
    def has_position(self, ticker: str) -> bool:
        """포지션 보유 여부"""
        pass

    @abstractmethod
    def get_all(self) -> List[Dict]:
        """모든 포지션 조회"""
        pass

    @abstractmethod
    def count(self) -> int:
        """포지션 개수"""
        pass

    @abstractmethod
    def close_position(self, ticker: str, exit_price: float, reason: str) -> bool:
        """포지션 청산"""
        pass

    @abstractmethod
    def has_signal_today(self, ticker: str) -> bool:
        """오늘 이미 신호 발생 여부 (중복 알림 방지)"""
        pass

    @abstractmethod
    def record_signal(self, signal: Dict) -> bool:
        """신호 기록"""
        pass

    @abstractmethod
    def get_trades(self, limit: int = 15) -> List[Dict]:
        """최근 거래 내역 조회"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict:
        """거래 통계 조회"""
        pass

    def calculate_stop_loss(self, entry_price: float) -> float:
        """손절가 계산"""
        return entry_price * (1 + self.stop_loss_pct / 100)

    def calculate_take_profit(self, entry_price: float) -> float:
        """익절가 계산"""
        return entry_price * (1 + self.take_profit_pct / 100)

    def calculate_profit(self, entry_price: float, current_price: float) -> float:
        """수익률 계산"""
        return ((current_price - entry_price) / entry_price) * 100

    def check_exit_conditions(
        self,
        position: Dict,
        current_price: float
    ) -> tuple[bool, float, str, PositionStatus]:
        """
        청산 조건 확인

        Returns:
            (청산여부, 청산가, 청산사유, 상태)
        """
        entry_date = position.get('entry_date')
        if isinstance(entry_date, str):
            entry_date = datetime.fromisoformat(entry_date.replace('Z', '+00:00'))
        elif isinstance(entry_date, datetime):
            pass
        else:
            entry_date = datetime.now()

        holding_days = (datetime.now() - entry_date.replace(tzinfo=None)).days
        stop_loss = position.get('stop_loss', self.calculate_stop_loss(position['entry_price']))
        take_profit = position.get('take_profit', self.calculate_take_profit(position['entry_price']))

        # 손절 확인
        if current_price <= stop_loss:
            return True, stop_loss, f'손절 ({self.stop_loss_pct}%)', PositionStatus.STOP_LOSS

        # 익절 확인
        if current_price >= take_profit:
            return True, current_price, f'익절 (+{self.take_profit_pct}%)', PositionStatus.TAKE_PROFIT

        # 보유기간 만료 확인
        if holding_days >= self.max_holding_days:
            return True, current_price, f'보유기간 만료 ({holding_days}일)', PositionStatus.EXPIRED

        return False, current_price, '', PositionStatus.OPEN

    def format_list_message(
        self,
        get_current_price: Callable[[str], float | None]
    ) -> str:
        """포지션 목록 메시지 포맷팅"""
        positions = self.get_all()
        if not positions:
            return "📊 <b>현재 포지션</b>\n\n보유 중인 포지션이 없습니다."

        msg = f"📊 <b>현재 포지션</b> ({len(positions)}개)\n\n"

        for i, pos in enumerate(positions, 1):
            ticker = pos['ticker']
            name = pos.get('name', ticker)
            entry_date = pos.get('entry_date')

            if isinstance(entry_date, str):
                entry_date = datetime.fromisoformat(entry_date.replace('Z', '+00:00'))
            elif not isinstance(entry_date, datetime):
                entry_date = datetime.now()

            holding_days = (datetime.now() - entry_date.replace(tzinfo=None)).days

            # 현재가 조회
            try:
                current_price = get_current_price(ticker)
                if current_price:
                    profit_pct = self.calculate_profit(pos['entry_price'], current_price)
                    profit_icon = "📈" if profit_pct > 0 else "📉"
                    current_info = f"{current_price:,.0f}원 ({profit_icon}{profit_pct:+.2f}%)"
                else:
                    current_info = "조회 실패"
            except:
                current_info = "조회 실패"

            msg += f"""
{i}. 🇰🇷 <b>{name}</b> ({ticker})
   진입: {pos['entry_price']:,.0f}원
   현재: {current_info}
   패턴: {pos.get('pattern', '-')}
   보유: {holding_days}일
   손절: {pos.get('stop_loss', 0):,.0f}원
   익절: {pos.get('take_profit', 0):,.0f}원
"""
        return msg


class DatabasePositionManager(BasePositionManager):
    """DB 기반 포지션 관리자"""

    def __init__(
        self,
        db_settings: DatabaseSettings,
        stop_loss_pct: float = -8.0,
        take_profit_pct: float = 20.0,
        max_holding_days: int = 30
    ):
        super().__init__(stop_loss_pct, take_profit_pct, max_holding_days)
        self.db = DatabaseConnection(db_settings)
        self._connected = False

    def connect(self) -> bool:
        """DB 연결"""
        if self._connected:
            return True
        self._connected = self.db.connect()
        if self._connected:
            self.db.init_tables()
        return self._connected

    def disconnect(self):
        """DB 연결 종료"""
        self.db.disconnect()
        self._connected = False

    def add(self, ticker: str, name: str, entry_price: float, pattern: str, signal: Dict) -> bool:
        """포지션 추가"""
        if not self.connect():
            return False

        position = Position(
            ticker=ticker,
            name=name,
            entry_price=entry_price,
            entry_date=datetime.now(),
            pattern=pattern,
            stop_loss=self.calculate_stop_loss(entry_price),
            take_profit=self.calculate_take_profit(entry_price),
            status=PositionStatus.OPEN,
            signal_data=signal,
        )

        result = self.db.add_position(position)
        if result:
            print(f"  📝 포지션 추가 (DB): {name}({ticker}) @ {entry_price:,.0f}원")
            return True
        return False

    def remove(self, ticker: str) -> bool:
        """포지션 제거 (청산)"""
        return self.close_position(ticker, 0, "수동 제거")

    def get(self, ticker: str) -> Optional[Dict]:
        """포지션 조회"""
        if not self.connect():
            return None

        position = self.db.get_position(ticker)
        if position:
            return position.to_dict()
        return None

    def has_position(self, ticker: str) -> bool:
        """포지션 보유 여부"""
        if not self.connect():
            return False
        return self.db.has_open_position(ticker)

    def get_all(self) -> List[Dict]:
        """모든 열린 포지션 조회"""
        if not self.connect():
            return []
        positions = self.db.get_open_positions()
        return [p.to_dict() for p in positions]

    def count(self) -> int:
        """열린 포지션 개수"""
        if not self.connect():
            return 0
        return self.db.count_open_positions()

    def close_position(self, ticker: str, exit_price: float, reason: str) -> bool:
        """포지션 청산"""
        if not self.connect():
            return False

        position = self.db.get_position(ticker)
        if not position:
            return False

        profit_pct = self.calculate_profit(position.entry_price, exit_price)

        # 청산 사유에 따른 상태 결정
        if "손절" in reason:
            status = PositionStatus.STOP_LOSS
        elif "익절" in reason:
            status = PositionStatus.TAKE_PROFIT
        elif "만료" in reason:
            status = PositionStatus.EXPIRED
        else:
            status = PositionStatus.CLOSED

        return self.db.close_position(ticker, exit_price, status, profit_pct)

    def has_signal_today(self, ticker: str) -> bool:
        """오늘 이미 신호 발생 여부"""
        if not self.connect():
            return False
        return self.db.has_signal_today(ticker)

    def record_signal(self, signal: Dict) -> bool:
        """신호 기록"""
        if not self.connect():
            return False

        signal_obj = Signal(
            ticker=signal.get('ticker', ''),
            name=signal.get('name', ''),
            pattern=signal.get('pattern', ''),
            price=signal.get('current_price', 0),
            volume_surge=signal.get('volume_ratio', 0) * 100 - 100,
            breakout_pct=signal.get('breakout_pct', 0),
            resistance_price=signal.get('resistance', 0),
            signal_date=datetime.now().date(),
            notified=True,
            position_opened=False,
            signal_data=signal,
        )

        result = self.db.add_signal(signal_obj)
        return result is not None

    def get_trades(self, limit: int = 15) -> List[Dict]:
        """최근 거래 내역 조회"""
        if not self.connect():
            return []
        positions = self.db.get_closed_positions(limit)
        return [p.to_dict() for p in positions]

    def get_stats(self) -> Dict:
        """거래 통계 조회"""
        if not self.connect():
            return {}
        return self.db.get_trade_stats()

    def mark_position_opened(self, ticker: str) -> bool:
        """신호에 포지션 오픈 완료 표시"""
        if not self.connect():
            return False
        return self.db.mark_signal_position_opened(ticker)


class JsonPositionManager(BasePositionManager):
    """JSON 파일 기반 포지션 관리자 (기존 방식)"""

    def __init__(
        self,
        positions_file: str = "positions.json",
        signals_file: str = "signals.json",
        stop_loss_pct: float = -8.0,
        take_profit_pct: float = 20.0,
        max_holding_days: int = 30
    ):
        super().__init__(stop_loss_pct, take_profit_pct, max_holding_days)
        self.positions_file = positions_file
        self.signals_file = signals_file
        self.positions: List[Dict] = self._load_positions()
        self.signals: Dict[str, str] = self._load_signals()  # {ticker: date}

    def _load_positions(self) -> List[Dict]:
        """포지션 파일에서 로드"""
        if os.path.exists(self.positions_file):
            try:
                with open(self.positions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('positions', [])
            except Exception as e:
                print(f"⚠️  포지션 로드 실패: {e}")
        return []

    def _save_positions(self) -> bool:
        """포지션 파일에 저장"""
        try:
            data = {
                'positions': self.positions,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 포지션 저장 실패: {e}")
            return False

    def _load_signals(self) -> Dict[str, str]:
        """신호 기록 로드"""
        if os.path.exists(self.signals_file):
            try:
                with open(self.signals_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_signals(self) -> bool:
        """신호 기록 저장"""
        try:
            with open(self.signals_file, 'w', encoding='utf-8') as f:
                json.dump(self.signals, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

    def add(self, ticker: str, name: str, entry_price: float, pattern: str, signal: Dict) -> bool:
        """포지션 추가"""
        position = {
            'ticker': ticker,
            'name': name,
            'entry_price': entry_price,
            'entry_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'pattern': pattern,
            'stop_loss': self.calculate_stop_loss(entry_price),
            'take_profit': self.calculate_take_profit(entry_price),
            'signal': signal
        }
        self.positions.append(position)
        self._save_positions()
        print(f"  📝 포지션 추가: {name}({ticker}) @ {entry_price:,.0f}원")
        return True

    def remove(self, ticker: str) -> bool:
        """포지션 제거"""
        for pos in self.positions:
            if pos['ticker'] == ticker:
                self.positions.remove(pos)
                self._save_positions()
                return True
        return False

    def get(self, ticker: str) -> Optional[Dict]:
        """포지션 조회"""
        return next((p for p in self.positions if p['ticker'] == ticker), None)

    def has_position(self, ticker: str) -> bool:
        """포지션 보유 여부"""
        return any(p['ticker'] == ticker for p in self.positions)

    def get_all(self) -> List[Dict]:
        """모든 포지션 조회"""
        return self.positions.copy()

    def count(self) -> int:
        """포지션 개수"""
        return len(self.positions)

    def close_position(self, ticker: str, exit_price: float, reason: str) -> bool:
        """포지션 청산"""
        return self.remove(ticker)

    def has_signal_today(self, ticker: str) -> bool:
        """오늘 이미 신호 발생 여부"""
        today = datetime.now().strftime('%Y-%m-%d')
        return self.signals.get(ticker) == today

    def record_signal(self, signal: Dict) -> bool:
        """신호 기록"""
        ticker = signal.get('ticker', '')
        today = datetime.now().strftime('%Y-%m-%d')
        self.signals[ticker] = today
        return self._save_signals()

    def get_trades(self, limit: int = 15) -> List[Dict]:
        """최근 거래 내역 조회 (JSON 모드에서는 미지원)"""
        return []

    def get_stats(self) -> Dict:
        """거래 통계 조회 (JSON 모드에서는 미지원)"""
        return {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'avg_profit': 0.0,
            'max_profit': 0.0,
            'max_loss': 0.0,
            'total_profit': 0.0,
        }

    def mark_position_opened(self, ticker: str) -> bool:
        """신호에 포지션 오픈 완료 표시 (JSON 모드에서는 미지원)"""
        return True


class PositionManager(BasePositionManager):
    """포지션 관리자 - 설정에 따라 DB 또는 JSON 사용"""

    def __init__(
        self,
        positions_file: str = "positions.json",
        stop_loss_pct: float = -8.0,
        take_profit_pct: float = 20.0,
        max_holding_days: int = 30,
        db_settings: Optional[DatabaseSettings] = None
    ):
        super().__init__(stop_loss_pct, take_profit_pct, max_holding_days)

        # DB 설정이 있고 use_database가 True면 DB 사용
        if db_settings and db_settings.use_database:
            print("📊 DB 모드로 포지션 관리")
            self._manager = DatabasePositionManager(
                db_settings, stop_loss_pct, take_profit_pct, max_holding_days
            )
        else:
            print("📁 JSON 파일 모드로 포지션 관리")
            self._manager = JsonPositionManager(
                positions_file, "signals.json",
                stop_loss_pct, take_profit_pct, max_holding_days
            )

    def add(self, ticker: str, name: str, entry_price: float, pattern: str, signal: Dict) -> bool:
        return self._manager.add(ticker, name, entry_price, pattern, signal)

    def remove(self, ticker: str) -> bool:
        return self._manager.remove(ticker)

    def get(self, ticker: str) -> Optional[Dict]:
        return self._manager.get(ticker)

    def has_position(self, ticker: str) -> bool:
        return self._manager.has_position(ticker)

    def get_all(self) -> List[Dict]:
        return self._manager.get_all()

    def count(self) -> int:
        return self._manager.count()

    def close_position(self, ticker: str, exit_price: float, reason: str) -> bool:
        return self._manager.close_position(ticker, exit_price, reason)

    def has_signal_today(self, ticker: str) -> bool:
        return self._manager.has_signal_today(ticker)

    def record_signal(self, signal: Dict) -> bool:
        return self._manager.record_signal(signal)

    def get_trades(self, limit: int = 15) -> List[Dict]:
        return self._manager.get_trades(limit)

    def get_stats(self) -> Dict:
        return self._manager.get_stats()

    def mark_position_opened(self, ticker: str) -> bool:
        return self._manager.mark_position_opened(ticker)

    def calculate_profit_from_position(self, position: Dict, current_price: float) -> tuple[float, int]:
        """수익률과 보유일수 계산"""
        entry_price = position['entry_price']
        profit_pct = self.calculate_profit(entry_price, current_price)

        entry_date = position.get('entry_date')
        if isinstance(entry_date, str):
            entry_date = datetime.fromisoformat(entry_date.replace('Z', '+00:00'))
        elif not isinstance(entry_date, datetime):
            entry_date = datetime.now()

        holding_days = (datetime.now() - entry_date.replace(tzinfo=None)).days
        return profit_pct, holding_days
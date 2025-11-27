"""데이터베이스 모델 정의"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import json


class PositionStatus(Enum):
    """포지션 상태"""
    OPEN = "open"           # 보유 중
    CLOSED = "closed"       # 청산됨
    STOP_LOSS = "stop_loss" # 손절
    TAKE_PROFIT = "take_profit"  # 익절
    EXPIRED = "expired"     # 만료


@dataclass
class Position:
    """포지션 모델"""
    id: Optional[int] = None
    ticker: str = ""
    name: str = ""
    entry_price: float = 0.0
    entry_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_date: Optional[datetime] = None
    quantity: int = 0
    pattern: str = ""
    stop_loss: float = 0.0
    take_profit: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    profit_pct: Optional[float] = None
    signal_data: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'ticker': self.ticker,
            'name': self.name,
            'entry_price': self.entry_price,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'exit_price': self.exit_price,
            'exit_date': self.exit_date.isoformat() if self.exit_date else None,
            'quantity': self.quantity,
            'pattern': self.pattern,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'status': self.status.value,
            'profit_pct': self.profit_pct,
            'signal_data': self.signal_data,
        }

    @classmethod
    def from_db_row(cls, row: tuple, columns: list) -> 'Position':
        """DB 행에서 Position 객체 생성"""
        data = dict(zip(columns, row))
        return cls(
            id=data.get('id'),
            ticker=data.get('ticker', ''),
            name=data.get('name', ''),
            entry_price=float(data.get('entry_price', 0)),
            entry_date=data.get('entry_date'),
            exit_price=float(data['exit_price']) if data.get('exit_price') else None,
            exit_date=data.get('exit_date'),
            quantity=int(data.get('quantity', 0)),
            pattern=data.get('pattern', ''),
            stop_loss=float(data.get('stop_loss', 0)),
            take_profit=float(data.get('take_profit', 0)),
            status=PositionStatus(data.get('status', 'open')),
            profit_pct=float(data['profit_pct']) if data.get('profit_pct') else None,
            signal_data=json.loads(data['signal_data']) if data.get('signal_data') else None,
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )


@dataclass
class Signal:
    """신호 기록 모델"""
    id: Optional[int] = None
    ticker: str = ""
    name: str = ""
    pattern: str = ""
    price: float = 0.0
    volume_surge: float = 0.0
    breakout_pct: float = 0.0
    resistance_price: float = 0.0
    signal_date: Optional[datetime] = None
    notified: bool = False
    position_opened: bool = False
    signal_data: Optional[dict] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'ticker': self.ticker,
            'name': self.name,
            'pattern': self.pattern,
            'price': self.price,
            'volume_surge': self.volume_surge,
            'breakout_pct': self.breakout_pct,
            'resistance_price': self.resistance_price,
            'signal_date': self.signal_date.isoformat() if self.signal_date else None,
            'notified': self.notified,
            'position_opened': self.position_opened,
            'signal_data': self.signal_data,
        }

    @classmethod
    def from_db_row(cls, row: tuple, columns: list) -> 'Signal':
        """DB 행에서 Signal 객체 생성"""
        data = dict(zip(columns, row))
        return cls(
            id=data.get('id'),
            ticker=data.get('ticker', ''),
            name=data.get('name', ''),
            pattern=data.get('pattern', ''),
            price=float(data.get('price', 0)),
            volume_surge=float(data.get('volume_surge', 0)),
            breakout_pct=float(data.get('breakout_pct', 0)),
            resistance_price=float(data.get('resistance_price', 0)),
            signal_date=data.get('signal_date'),
            notified=bool(data.get('notified', False)),
            position_opened=bool(data.get('position_opened', False)),
            signal_data=json.loads(data['signal_data']) if data.get('signal_data') else None,
            created_at=data.get('created_at'),
        )
"""
윌리엄 오닐 돌파매매(CAN SLIM) 알림 시스템 - 한국 주식 전용
- 한국 장중 자동 스캔 (피벗 포인트 돌파 감지)
- 텔레그램 명령어로 종목 관리
- 신호 발생 시 포지션 자동 추적 (손절/익절/보유기간 만료)
- 백테스트: 컵앤핸들, 피벗 포인트, 베이스 돌파 패턴
"""

__version__ = "3.0.0"
__author__ = "dev-minimalism"

# 주요 클래스 노출
from .bot import BreakoutDetector
from .backtest import BacktestEngine
from .config import Settings, load_settings
from .positions import PositionManager
from .watchlist import WatchlistManager

__all__ = [
    'BreakoutDetector',
    'BacktestEngine',
    'Settings',
    'load_settings',
    'PositionManager',
    'WatchlistManager',
]

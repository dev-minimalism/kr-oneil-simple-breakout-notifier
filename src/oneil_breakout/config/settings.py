"""설정 관리 - .env 파일에서 로드"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv


@dataclass
class TelegramSettings:
    """텔레그램 설정"""
    token: str = ""
    chat_id: str = ""


@dataclass
class PatternSettings:
    """패턴 감지 설정"""
    # 컵앤핸들
    cup_depth_min: float = 12.0
    cup_depth_max: float = 40.0
    handle_depth_max: float = 12.0

    # 피벗 돌파
    volume_surge_min: float = 50.0
    breakout_max: float = 5.0

    # 베이스 돌파
    base_volatility_max: float = 15.0
    base_volume_surge_min: float = 40.0
    base_breakout_max: float = 7.0


@dataclass
class TradingSettings:
    """거래 설정"""
    stop_loss_pct: float = -8.0
    take_profit_pct: float = 20.0
    max_holding_days: int = 30
    max_positions: int = 5
    position_size_pct: float = 20.0  # 각 포지션 크기 (자본 대비 %)


@dataclass
class ScanSettings:
    """스캔 설정"""
    interval_seconds: int = 1800  # 30분
    request_delay: float = 1.0


@dataclass
class DataSettings:
    """데이터 설정"""
    analysis_period_days: int = 120  # 한국 주식


@dataclass
class WatchlistSettings:
    """워치리스트 기본값"""
    kr_stocks: List[str] = field(default_factory=lambda: [
        "005930", "000660", "035420", "035720",
        "373220", "086520", "247540", "066970",
        "068270", "091990", "207940", "326030",
        "005380", "000270",
        "051910", "006400", "096770",
        "009540", "010140"
    ])


@dataclass
class Settings:
    """전체 설정"""
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    pattern: PatternSettings = field(default_factory=PatternSettings)
    trading: TradingSettings = field(default_factory=TradingSettings)
    scan: ScanSettings = field(default_factory=ScanSettings)
    data: DataSettings = field(default_factory=DataSettings)
    watchlist: WatchlistSettings = field(default_factory=WatchlistSettings)

    # 파일 경로
    watchlist_file: str = "watchlist.json"
    positions_file: str = "positions.json"


def _get_env_float(key: str, default: float) -> float:
    """환경 변수에서 float 값 로드"""
    value = os.environ.get(key)
    if value:
        try:
            return float(value)
        except ValueError:
            pass
    return default


def _get_env_int(key: str, default: int) -> int:
    """환경 변수에서 int 값 로드"""
    value = os.environ.get(key)
    if value:
        try:
            return int(value)
        except ValueError:
            pass
    return default


def _get_env_list(key: str, default: List[str]) -> List[str]:
    """환경 변수에서 리스트 값 로드 (쉼표 구분)"""
    value = os.environ.get(key)
    if value:
        return [item.strip() for item in value.split(',') if item.strip()]
    return default


def load_settings() -> Settings:
    """
    설정 로드 (.env 파일에서)

    .env 파일 위치:
        1. 현재 작업 디렉토리
        2. 프로젝트 루트 디렉토리

    Returns:
        Settings 인스턴스
    """
    # .env 파일 로드 (현재 디렉토리 또는 프로젝트 루트)
    env_loaded = load_dotenv()

    # 프로젝트 루트에서도 시도
    if not env_loaded:
        project_root = Path(__file__).parent.parent.parent.parent
        env_path = project_root / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            env_loaded = True

    settings = Settings()

    # 텔레그램 설정
    settings.telegram.token = os.environ.get('TELEGRAM_TOKEN', '')
    settings.telegram.chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')

    # 스캔 설정
    settings.scan.interval_seconds = _get_env_int('SCAN_INTERVAL', 1800)

    # 패턴 설정
    settings.pattern.volume_surge_min = _get_env_float('VOLUME_SURGE_MIN', 50.0)
    settings.pattern.breakout_max = _get_env_float('BREAKOUT_MAX', 5.0)
    settings.pattern.cup_depth_min = _get_env_float('CUP_DEPTH_MIN', 12.0)
    settings.pattern.cup_depth_max = _get_env_float('CUP_DEPTH_MAX', 40.0)
    settings.pattern.handle_depth_max = _get_env_float('HANDLE_DEPTH_MAX', 12.0)
    settings.pattern.base_volatility_max = _get_env_float('BASE_VOLATILITY_MAX', 15.0)
    settings.pattern.base_volume_surge_min = _get_env_float('BASE_VOLUME_SURGE_MIN', 40.0)
    settings.pattern.base_breakout_max = _get_env_float('BASE_BREAKOUT_MAX', 7.0)

    # 거래 설정
    settings.trading.stop_loss_pct = _get_env_float('STOP_LOSS_PERCENT', -8.0)
    settings.trading.take_profit_pct = _get_env_float('TAKE_PROFIT_PERCENT', 20.0)
    settings.trading.max_holding_days = _get_env_int('MAX_HOLDING_DAYS', 30)

    # 데이터 설정
    settings.data.analysis_period_days = _get_env_int('ANALYSIS_PERIOD_DAYS', 120)

    # 워치리스트
    default_stocks = [
        "005930", "000660", "035420", "035720",
        "373220", "086520", "247540", "066970",
        "068270", "091990", "207940", "326030",
        "005380", "000270", "051910", "006400",
        "096770", "009540", "010140"
    ]
    settings.watchlist.kr_stocks = _get_env_list('KR_WATCH_LIST', default_stocks)

    if env_loaded:
        print("✅ .env 파일에서 설정을 불러왔습니다.")
    else:
        print("ℹ️  .env 파일 없음 - 기본 설정 사용")

    return settings
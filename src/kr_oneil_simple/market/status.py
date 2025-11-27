"""시장 상태 확인"""
from datetime import datetime, time as dt_time
from typing import Dict


def get_market_status() -> Dict[str, bool | str | int]:
    """
    현재 시간에 따른 한국 시장 상태 확인

    Returns:
        {
            'kr': bool - 한국 장중 여부,
            'time': str - 현재 시간,
            'weekday': int - 요일 (0=월요일, 6=일요일)
        }
    """
    now = datetime.now()
    current_time = now.time()
    weekday = now.weekday()

    # 주말 체크
    is_weekend = weekday >= 5

    # 한국 장중: 08:00 - 17:00 (평일)
    kr_open = dt_time(8, 0)
    kr_close = dt_time(17, 0)
    is_kr_market = (not is_weekend) and (kr_open <= current_time <= kr_close)

    return {
        'kr': is_kr_market,
        'time': now.strftime('%H:%M:%S'),
        'weekday': weekday
    }


def format_market_status_message(market_status: Dict, stock_count: int, _unused: int = 0, is_scanning: bool = False) -> str:
    """
    시장 상태 메시지 포맷팅

    Args:
        market_status: get_market_status() 결과
        stock_count: 감시 종목 수
        _unused: (호환성 유지용, 사용하지 않음)
        is_scanning: 스캔 진행 중 여부

    Returns:
        포맷된 메시지
    """
    msg = "📊 <b>시장 상태</b>\n\n"
    msg += f"⏰ 현재 시간: {market_status['time']}\n\n"

    if market_status['kr']:
        msg += "🇰🇷 한국 장중 (09:00-15:30)\n"
        msg += f"   감시 중: {stock_count}개 종목\n"
    else:
        msg += "🇰🇷 한국 장 마감\n"
        msg += "\n⏸️  현재 휴장 시간입니다"

    if is_scanning:
        msg += "\n\n🔄 현재 스캔 진행 중..."

    return msg
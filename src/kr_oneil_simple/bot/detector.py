"""한국 주식 돌파매매 감지 봇"""
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List

from ..config import Settings, load_settings
from ..data.kr_stock import get_kr_stock_data, get_kr_stock_name
from ..patterns.pivot import detect_pivot_breakout
from ..market.status import get_market_status, format_market_status_message
from ..positions import PositionManager
from ..watchlist import WatchlistManager
from ..telegram.client import TelegramClient
from ..telegram.formatter import (
    format_signal_message,
    format_close_position_message,
    format_no_signal_message
)
from ..database import PositionStatus


class BreakoutDetector:
    """한국 주식 돌파매매 패턴 감지 봇"""

    def __init__(self, settings: Settings | None = None):
        """
        Args:
            settings: 설정 객체 (None이면 자동 로드)
        """
        self.settings = settings or load_settings()

        # 텔레그램 클라이언트
        self.telegram = TelegramClient(
            self.settings.telegram.token,
            self.settings.telegram.chat_id,
            self.settings.telegram.poll_timeout
        )

        # 워치리스트 관리자
        self.watchlist = WatchlistManager(
            self.settings.watchlist_file,
            self.settings.watchlist.kr_stocks
        )

        # 포지션 관리자 (DB 설정에 따라 DB 또는 JSON 사용)
        self.positions = PositionManager(
            self.settings.positions_file,
            self.settings.trading.stop_loss_pct,
            self.settings.trading.take_profit_pct,
            self.settings.trading.max_holding_days,
            db_settings=self.settings.database
        )

        # 스캔 락
        self.scan_lock = threading.Lock()
        self.is_scanning = False

        print(f"✅ 감시 종목 로드 완료: {self.watchlist.count_kr()}개")
        print(f"✅ 포지션 로드 완료: {self.positions.count()}개")

    # ========================================
    # 텔레그램 명령어 처리
    # ========================================

    def process_command(self, message: str) -> str | None:
        """텔레그램 명령어 처리"""
        parts = message.strip().split()
        if not parts:
            return None

        command = parts[0].lower()

        if command in ('/help', '/start'):
            return self._get_help_message()

        elif command in ('/add', '/add_kr'):
            if len(parts) < 2:
                return "❌ 사용법: /add [종목코드]\n예: /add 005930"
            return self.watchlist.add_kr(parts[1])

        elif command in ('/remove', '/remove_kr'):
            if len(parts) < 2:
                return "❌ 사용법: /remove [종목코드]\n예: /remove 005930"
            return self.watchlist.remove_kr(parts[1])

        elif command == '/list':
            return self.watchlist.format_list_message()

        elif command == '/status':
            market_status = get_market_status()
            return format_market_status_message(
                market_status,
                self.watchlist.count_kr(),
                0,
                self.is_scanning
            )

        elif command in ('/scan', '/scan_kr'):
            return 'SCAN_KR'

        elif command == '/positions':
            return self.positions.format_list_message(self._get_current_price)

        elif command == '/close':
            if len(parts) < 2:
                return "❌ 사용법: /close [종목코드]\n예: /close 005930"
            return self._close_position_command(parts[1])

        elif command == '/trades':
            return self._get_trades_message()

        elif command == '/stats':
            return self._get_stats_message()

        return None

    def _get_help_message(self) -> str:
        """도움말 메시지"""
        return """
🤖 <b>윌리엄 오닐 돌파매매 봇 명령어</b>

<b>스캔:</b>
/scan - 즉시 스캔

<b>감시 종목:</b>
/list - 현재 감시 종목 보기
/add [종목코드] - 종목 추가
/remove [종목코드] - 종목 삭제

<b>포지션 관리:</b>
/positions - 현재 보유 포지션 보기
/close [종목코드] - 포지션 수동 청산

<b>거래 내역:</b>
/trades - 최근 거래 내역 (최대 15건)
/stats - 거래 통계 (승률, 평균수익률 등)

<b>상태:</b>
/status - 시장 상태 확인
/help - 도움말

<b>팁:</b>
• 매수 신호 발생 시 자동으로 포지션 추적
• 손절(-8%), 익절(+20%), 30일 만료 시 알림
• 장 시간 (09:00-15:30) 자동 스캔
"""

    def _close_position_command(self, ticker: str) -> str:
        """포지션 청산 명령 처리"""
        pos = self.positions.get(ticker)
        if not pos:
            return f"❌ {ticker} 포지션을 찾을 수 없습니다."

        try:
            current_price = self._get_current_price(ticker)
            if current_price:
                self._close_position(pos, current_price, "수동 청산")
                return f"✅ {ticker} 포지션이 청산되었습니다."
            else:
                return f"❌ {ticker} 현재가 조회 실패"
        except Exception as e:
            return f"❌ 청산 중 오류: {e}"

    def _get_trades_message(self) -> str:
        """최근 거래 내역 메시지"""
        trades = self.positions.get_trades(15)
        if not trades:
            return "📜 <b>최근 거래 내역</b>\n\n거래 내역이 없습니다."

        msg = f"📜 <b>최근 거래 내역</b> ({len(trades)}건)\n\n"

        for i, trade in enumerate(trades, 1):
            ticker = trade['ticker']
            name = trade.get('name', ticker)
            entry_price = trade.get('entry_price', 0)
            exit_price = trade.get('exit_price', 0)
            profit_pct = trade.get('profit_pct', 0)
            status = trade.get('status', '')
            exit_date = trade.get('exit_date', '')

            # 상태 아이콘
            if status == 'take_profit':
                icon = "🎯"
                status_text = "익절"
            elif status == 'stop_loss':
                icon = "🛑"
                status_text = "손절"
            elif status == 'expired':
                icon = "⏰"
                status_text = "만료"
            else:
                icon = "📤"
                status_text = "청산"

            # 수익률 포맷
            profit_icon = "📈" if profit_pct > 0 else "📉"

            # 날짜 포맷
            if isinstance(exit_date, datetime):
                date_str = exit_date.strftime('%m/%d')
            elif exit_date:
                date_str = str(exit_date)[:10]
            else:
                date_str = "-"

            msg += f"{i}. {icon} <b>{name}</b> ({ticker})\n"
            msg += f"   {entry_price:,.0f} → {exit_price:,.0f}원 {profit_icon}{profit_pct:+.2f}%\n"
            msg += f"   {status_text} | {date_str}\n\n"

        return msg

    def _get_stats_message(self) -> str:
        """거래 통계 메시지"""
        stats = self.positions.get_stats()

        if stats.get('total_trades', 0) == 0:
            return "📊 <b>거래 통계</b>\n\n거래 기록이 없습니다."

        msg = f"""📊 <b>거래 통계</b>

<b>전체 성과</b>
총 거래: {stats['total_trades']}건
승/패: {stats['wins']}승 {stats['losses']}패
승률: {stats['win_rate']:.1f}%

<b>수익률</b>
평균: {stats['avg_profit']:+.2f}%
최대 수익: {stats['max_profit']:+.2f}%
최대 손실: {stats['max_loss']:+.2f}%
누적: {stats['total_profit']:+.2f}%

<b>청산 유형</b>
🎯 익절: {stats.get('take_profit_count', 0)}건
🛑 손절: {stats.get('stop_loss_count', 0)}건
⏰ 만료: {stats.get('expired_count', 0)}건
📤 수동: {stats.get('manual_close_count', 0)}건
"""
        return msg

    def _get_current_price(self, ticker: str) -> float | None:
        """현재가 조회"""
        df = get_kr_stock_data(ticker, days=7)
        if df is not None and len(df) > 0:
            return df['Close'].iloc[-1]
        return None

    # ========================================
    # 포지션 관리
    # ========================================

    def _close_position(self, position: Dict, exit_price: float, reason: str):
        """포지션 청산 처리"""
        profit_pct, holding_days = self.positions.calculate_profit_from_position(position, exit_price)

        msg = format_close_position_message(
            position['ticker'],
            position.get('pattern', ''),
            position['entry_price'],
            exit_price,
            profit_pct,
            holding_days,
            reason
        )
        self.telegram.send_message(msg)
        self.positions.close_position(position['ticker'], exit_price, reason)
        print(f"  ❌ 포지션 청산: {position['ticker']} ({reason}) {profit_pct:+.2f}%")

    def check_positions(self):
        """포지션 추적 및 청산 조건 확인"""
        if self.positions.count() == 0:
            return

        print(f"\n📊 포지션 추적 중... ({self.positions.count()}개)")

        for pos in self.positions.get_all():
            ticker = pos['ticker']
            name = pos.get('name', ticker)
            try:
                current_price = self._get_current_price(ticker)
                if current_price is None:
                    continue

                profit_pct, holding_days = self.positions.calculate_profit_from_position(pos, current_price)
                print(f"  🔍 {name}({ticker}): {current_price:,.0f}원 ({profit_pct:+.2f}%)", end="")

                should_exit, exit_price, reason, _ = self.positions.check_exit_conditions(pos, current_price)
                if should_exit:
                    print(f" ⚠️ {reason}!")
                    self._close_position(pos, exit_price, reason)
                else:
                    print(f" ⚪")

                time.sleep(1)

            except Exception as e:
                print(f" ❌ 오류: {e}")

    # ========================================
    # 종목 분석
    # ========================================

    def analyze_stock(self, ticker: str) -> List[Dict]:
        """한국 주식 분석"""
        df = get_kr_stock_data(ticker, self.settings.data.analysis_period_days)
        if df is None:
            return []

        signals = []
        stock_name = get_kr_stock_name(ticker)
        pivot_signal = detect_pivot_breakout(
            df, ticker, stock_name,
            volume_surge_min=self.settings.pattern.volume_surge_min,
            breakout_max=self.settings.pattern.breakout_max
        )
        if pivot_signal:
            signals.append(pivot_signal)

        return signals

    # ========================================
    # 스캔 실행
    # ========================================

    def run_scan(self) -> List[Dict]:
        """수동 스캔"""
        print(f"\n{'=' * 60}")
        print(f"🔍 스캔 시작")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🇰🇷 한국 주식 스캔 ({self.watchlist.count()}개)")
        print(f"{'=' * 60}\n")

        signals = self._scan_stocks()
        self._print_scan_summary(signals, send_no_signal_msg=True)
        return signals

    def run_smart_scan(self) -> List[Dict]:
        """시간대에 따라 자동으로 스캔"""
        if self.is_scanning:
            print("\n⏸️  수동 스캔이 진행 중입니다. 이번 주기는 건너뜁니다...\n")
            return []

        market_status = get_market_status()

        print(f"\n{'=' * 60}")
        print(f"🔍 윌리엄 오닐 simple 한국장 스캔")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not market_status['kr']:
            print("⏸️  휴장 시간입니다. 다음 장 시작까지 대기...")
            print(f"{'=' * 60}\n")
            self.check_positions()
            return []

        print(f"🇰🇷 한국 장중 - 한국 주식 스캔 ({self.watchlist.count()}개)")
        print(f"{'=' * 60}\n")

        # 먼저 포지션 추적
        self.check_positions()

        signals = self._scan_stocks()
        self._print_scan_summary(signals)
        return signals

    def _scan_stocks(self) -> List[Dict]:
        """한국 주식 스캔 (중복 알림 방지 포함)"""
        signals = []
        tickers = self.watchlist.get_all()

        if not tickers:
            print("⚠️  워치리스트가 비어있습니다.", flush=True)
            return signals

        total = len(tickers)
        print(f"🇰🇷 한국 주식 스캔 중... ({total}개)\n", flush=True)

        for i, ticker in enumerate(tickers, 1):
            try:
                name = get_kr_stock_name(ticker)
                print(f"  [{i}/{total}] 🔍 {name}({ticker})...", end=" ", flush=True)

                # 이미 포지션이 있으면 스킵
                if self.positions.has_position(ticker):
                    print("📍 포지션 보유중", flush=True)
                    continue

                # 오늘 이미 신호가 발생했으면 스킵 (중복 알림 방지)
                if self.positions.has_signal_today(ticker):
                    print("🔕 오늘 이미 알림 발송", flush=True)
                    continue

                stock_signals = self.analyze_stock(ticker)

                if stock_signals:
                    for signal in stock_signals:
                        # 먼저 신호 기록 (중복 방지용) - 이 시점에서 DB에 기록
                        self.positions.record_signal(signal)

                        # 포지션 추가 시도 (이미 있으면 실패)
                        added = self.positions.add(
                            ticker=ticker,
                            name=name,
                            entry_price=signal['current_price'],
                            pattern=signal['pattern'],
                            signal=signal
                        )

                        # 포지션이 성공적으로 추가된 경우에만 알림 발송
                        if added:
                            signals.append(signal)

                            # 신호에 포지션 오픈 완료 표시
                            self.positions.mark_position_opened(ticker)

                            # 텔레그램 알림
                            msg = format_signal_message(signal)
                            self.telegram.send_message(msg)

                            print(f"✅ 신호!", flush=True)
                            time.sleep(2)
                        else:
                            print(f"⚠️ 포지션 추가 실패 (이미 존재)", flush=True)
                else:
                    print("⚪", flush=True)

                # 종목 사이 짧은 딜레이 (API 부하 방지)
                time.sleep(0.5)

            except Exception as e:
                print(f"❌ 오류: {e}", flush=True)
                continue  # 에러 발생해도 다음 종목 계속 진행

        print(flush=True)
        return signals

    def _print_scan_summary(self, signals: List[Dict], send_no_signal_msg: bool = False):
        """스캔 결과 요약 출력

        Args:
            signals: 발견된 신호 목록
            send_no_signal_msg: 신호 없을 때 텔레그램 메시지 전송 여부 (수동 스캔 시 True)
        """
        if signals:
            print(f"📊 {len(signals)}개 신호 발견")
        else:
            print("⚪ 신호 없음")
            if send_no_signal_msg:
                msg = format_no_signal_message(self.watchlist.count())
                self.telegram.send_message(msg)

        print(f"\n{'=' * 60}\n")

    # ========================================
    # 스캔 스레드 관리
    # ========================================

    def _execute_scan_in_thread(self):
        """별도 스레드에서 스캔 실행"""
        if self.is_scanning:
            self.telegram.send_message("⚠️  이미 스캔이 진행 중입니다. 완료 후 다시 시도해주세요.")
            return

        if not self.scan_lock.acquire(blocking=False):
            self.telegram.send_message("⚠️  다른 스캔이 진행 중입니다. 잠시 후 다시 시도해주세요.")
            return

        try:
            self.is_scanning = True
            print(f"\n🔔 수동 스캔 명령어 수신 - 스캔 시작", flush=True)

            # 스캔 시작 알림
            count = self.watchlist.count()
            self.telegram.send_message(f"📊 {count}개 종목 스캔 중...")

            signals = self.run_scan()

            # 결과 알림
            if signals:
                self.telegram.send_message(f"✅ 스캔 완료! {len(signals)}개 신호 발견")
            else:
                self.telegram.send_message(f"✅ 스캔 완료! 신호 없음")
        except Exception as e:
            import traceback
            error_msg = f"❌ 스캔 중 오류: {e}"
            print(error_msg, flush=True)
            print(traceback.format_exc(), flush=True)
            self.telegram.send_message(error_msg)
        finally:
            self.is_scanning = False
            self.scan_lock.release()

    def check_telegram_updates(self):
        """텔레그램 메시지 확인 (명령어 처리)"""
        updates = self.telegram.get_updates()

        for update in updates:
            message_text = update['text']
            reply = self.process_command(message_text)

            if reply == 'SCAN_KR':
                self.telegram.send_message("🔍 스캔을 시작합니다...")
                scan_thread = threading.Thread(
                    target=self._execute_scan_in_thread,
                    daemon=True
                )
                scan_thread.start()

            elif reply:
                self.telegram.send_message(reply)

    def start_command_listener(self):
        """백그라운드에서 텔레그램 명령어 리스너 시작"""

        def listener_loop():
            while True:
                try:
                    self.check_telegram_updates()
                    time.sleep(2)
                except Exception as e:
                    print(f"⚠️  리스너 오류: {e}")
                    time.sleep(5)

        thread = threading.Thread(target=listener_loop, daemon=True)
        thread.start()
        print("✅ 텔레그램 명령어 리스너 시작")

    # ========================================
    # 메인 실행
    # ========================================

    def get_start_message(self) -> str:
        """시작 메시지 생성"""
        market_status = get_market_status()
        status_text = "🇰🇷 한국 장중" if market_status['kr'] else "⏸️ 휴장 중"

        interval_min = self.settings.scan.interval_seconds // 60

        return f"""
🤖 <b>윌리엄 오닐 돌파매매 봇 시작</b>

📊 감시 종목: {self.watchlist.count_kr()}개
📍 현재 포지션: {self.positions.count()}개

⏰ 스캔 주기: {interval_min}분
🕐 현재 상태: {status_text}

📈 자동 스캔: 장중 (09:00-15:30)

🎯 자동 포지션 추적:
   • 매수 신호 시 자동 기록
   • 손절({self.settings.trading.stop_loss_pct}%), 익절(+{self.settings.trading.take_profit_pct}%), {self.settings.trading.max_holding_days}일 만료 알림

💬 명령어:
   /scan - 즉시 스캔
   /positions - 현재 포지션 보기
   /help - 전체 명령어 보기

시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    def run(self):
        """메인 실행 루프"""
        # 텔레그램 명령어 리스너 시작
        self.start_command_listener()

        # 시작 메시지
        start_msg = self.get_start_message()
        self.telegram.send_message(start_msg)
        print(start_msg)

        scan_interval = self.settings.scan.interval_seconds

        try:
            while True:
                self.run_smart_scan()

                # 다음 스캔까지 대기
                next_scan = datetime.now() + timedelta(seconds=scan_interval)
                print(f"⏰ 다음 스캔: {next_scan.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"💤 {scan_interval // 60}분 대기 중...\n")
                time.sleep(scan_interval)

        except KeyboardInterrupt:
            print("\n\n⛔ 프로그램 종료")
            self.telegram.send_message("⛔ 윌리엄 오닐 스마트 돌파매매 봇 종료")
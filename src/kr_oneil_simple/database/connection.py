"""PostgreSQL SSH 터널 연결 관리"""
import json
import os
import socket
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Generator

import paramiko
import psycopg2
from psycopg2.extras import RealDictCursor

from ..config import DatabaseSettings
from .models import Position, Signal, PositionStatus


class SSHTunnel:
    """SSH 터널 관리 (paramiko 직접 사용)"""

    def __init__(
        self,
        ssh_host: str,
        ssh_port: int,
        ssh_user: str,
        ssh_key_path: str,
        remote_host: str,
        remote_port: int
    ):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_key_path = os.path.expanduser(ssh_key_path)
        self.remote_host = remote_host
        self.remote_port = remote_port

        self._ssh_client: Optional[paramiko.SSHClient] = None
        self._local_socket: Optional[socket.socket] = None
        self._local_port: int = 0
        self._running = False
        self._forward_thread: Optional[threading.Thread] = None

    @property
    def local_bind_port(self) -> int:
        return self._local_port

    def start(self):
        """SSH 터널 시작"""
        # SSH 클라이언트 생성
        self._ssh_client = paramiko.SSHClient()
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # RSA 키 로드
        pkey = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)

        # SSH 연결
        self._ssh_client.connect(
            hostname=self.ssh_host,
            port=self.ssh_port,
            username=self.ssh_user,
            pkey=pkey
        )

        # 로컬 소켓 바인딩 (자동 포트 할당)
        self._local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._local_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._local_socket.bind(('127.0.0.1', 0))
        self._local_port = self._local_socket.getsockname()[1]
        self._local_socket.listen(5)

        self._running = True
        self._forward_thread = threading.Thread(target=self._forward_loop, daemon=True)
        self._forward_thread.start()

    def _forward_loop(self):
        """포트 포워딩 루프"""
        while self._running:
            try:
                self._local_socket.settimeout(1.0)
                try:
                    client_socket, addr = self._local_socket.accept()
                except socket.timeout:
                    continue

                # SSH 채널을 통해 원격 연결
                transport = self._ssh_client.get_transport()
                channel = transport.open_channel(
                    'direct-tcpip',
                    (self.remote_host, self.remote_port),
                    addr
                )

                # 양방향 데이터 전송 스레드
                threading.Thread(
                    target=self._forward_data, args=(client_socket, channel), daemon=True
                ).start()
                threading.Thread(
                    target=self._forward_data, args=(channel, client_socket), daemon=True
                ).start()

            except Exception:
                if self._running:
                    continue
                break

    def _forward_data(self, src, dst):
        """데이터 포워딩"""
        try:
            while self._running:
                data = src.recv(4096)
                if not data:
                    break
                dst.sendall(data)
        except:
            pass

    def stop(self):
        """SSH 터널 종료"""
        self._running = False

        if self._local_socket:
            try:
                self._local_socket.close()
            except:
                pass
            self._local_socket = None

        if self._ssh_client:
            try:
                self._ssh_client.close()
            except:
                pass
            self._ssh_client = None


class DatabaseConnection:
    """SSH 터널을 통한 PostgreSQL 연결 관리"""

    # 테이블 생성 SQL
    CREATE_TABLES_SQL = """
    -- 포지션 테이블
    CREATE TABLE IF NOT EXISTS positions (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR(20) NOT NULL,
        name VARCHAR(100),
        entry_price DECIMAL(15, 2) NOT NULL,
        entry_date TIMESTAMP NOT NULL DEFAULT NOW(),
        exit_price DECIMAL(15, 2),
        exit_date TIMESTAMP,
        quantity INTEGER DEFAULT 0,
        pattern VARCHAR(50),
        stop_loss DECIMAL(15, 2),
        take_profit DECIMAL(15, 2),
        status VARCHAR(20) DEFAULT 'open',
        profit_pct DECIMAL(10, 4),
        signal_data JSONB,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    -- 신호 기록 테이블
    CREATE TABLE IF NOT EXISTS signals (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR(20) NOT NULL,
        name VARCHAR(100),
        pattern VARCHAR(50),
        price DECIMAL(15, 2) NOT NULL,
        volume_surge DECIMAL(10, 2),
        breakout_pct DECIMAL(10, 4),
        resistance_price DECIMAL(15, 2),
        signal_date DATE NOT NULL,
        notified BOOLEAN DEFAULT FALSE,
        position_opened BOOLEAN DEFAULT FALSE,
        signal_data JSONB,
        created_at TIMESTAMP DEFAULT NOW()
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_positions_ticker ON positions(ticker);
    CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
    CREATE INDEX IF NOT EXISTS idx_positions_entry_date ON positions(entry_date);
    CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker);
    CREATE INDEX IF NOT EXISTS idx_signals_signal_date ON signals(signal_date);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_ticker_date ON signals(ticker, signal_date);

    -- 같은 ticker에 대해 open 상태 포지션은 하나만 허용 (중복 방지)
    CREATE UNIQUE INDEX IF NOT EXISTS idx_positions_ticker_open
        ON positions(ticker) WHERE status = 'open';

    -- updated_at 트리거
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    DROP TRIGGER IF EXISTS update_positions_updated_at ON positions;
    CREATE TRIGGER update_positions_updated_at
        BEFORE UPDATE ON positions
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """

    def __init__(self, settings: DatabaseSettings):
        """
        Args:
            settings: 데이터베이스 설정
        """
        self.settings = settings
        self._tunnel: Optional[SSHTunnel] = None
        self._conn: Optional[psycopg2.extensions.connection] = None

    def connect(self) -> bool:
        """SSH 터널 생성 및 DB 연결"""
        try:
            # SSH 터널 생성
            self._tunnel = SSHTunnel(
                ssh_host=self.settings.ssh_host,
                ssh_port=self.settings.ssh_port,
                ssh_user=self.settings.ssh_user,
                ssh_key_path=self.settings.ssh_key_path,
                remote_host=self.settings.db_host,
                remote_port=self.settings.db_port
            )
            self._tunnel.start()

            # PostgreSQL 연결
            self._conn = psycopg2.connect(
                host='127.0.0.1',
                port=self._tunnel.local_bind_port,
                database=self.settings.db_name,
                user=self.settings.db_user,
                password=self.settings.db_password,
            )
            self._conn.autocommit = False

            print(f"✅ DB 연결 성공 (SSH: {self.settings.ssh_host})")
            return True

        except Exception as e:
            print(f"❌ DB 연결 실패: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        """연결 종료"""
        if self._conn:
            try:
                self._conn.close()
            except:
                pass
            self._conn = None

        if self._tunnel:
            try:
                self._tunnel.stop()
            except:
                pass
            self._tunnel = None

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        if not self._conn:
            return False
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except:
            return False

    def ensure_connected(self) -> bool:
        """연결 확인 및 재연결"""
        if not self.is_connected():
            return self.connect()
        return True

    def init_tables(self) -> bool:
        """테이블 초기화"""
        if not self.ensure_connected():
            return False

        try:
            with self._conn.cursor() as cur:
                cur.execute(self.CREATE_TABLES_SQL)
            self._conn.commit()
            print("✅ DB 테이블 초기화 완료")
            return True
        except Exception as e:
            print(f"❌ 테이블 초기화 실패: {e}")
            self._conn.rollback()
            return False

    @contextmanager
    def cursor(self) -> Generator:
        """커서 컨텍스트 매니저"""
        if not self.ensure_connected():
            raise ConnectionError("DB 연결 실패")

        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            raise e
        finally:
            cur.close()

    # ========================================
    # Position CRUD
    # ========================================

    def add_position(self, position: Position) -> Optional[int]:
        """포지션 추가 (이미 열린 포지션이 있으면 추가하지 않음)"""
        # 먼저 열린 포지션이 있는지 확인
        if self.has_open_position(position.ticker):
            print(f"⚠️ 이미 열린 포지션 존재: {position.ticker}")
            return None

        sql = """
        INSERT INTO positions (
            ticker, name, entry_price, entry_date, quantity, pattern,
            stop_loss, take_profit, status, signal_data
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        try:
            with self.cursor() as cur:
                cur.execute(sql, (
                    position.ticker,
                    position.name,
                    position.entry_price,
                    position.entry_date or datetime.now(),
                    position.quantity,
                    position.pattern,
                    position.stop_loss,
                    position.take_profit,
                    position.status.value,
                    json.dumps(position.signal_data) if position.signal_data else None,
                ))
                result = cur.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"❌ 포지션 추가 실패: {e}")
            return None

    def get_position(self, ticker: str) -> Optional[Position]:
        """열린 포지션 조회"""
        sql = """
        SELECT id, ticker, name, entry_price, entry_date, exit_price, exit_date,
               quantity, pattern, stop_loss, take_profit, status, profit_pct,
               signal_data, created_at, updated_at
        FROM positions
        WHERE ticker = %s AND status = 'open'
        ORDER BY entry_date DESC
        LIMIT 1
        """
        try:
            with self.cursor() as cur:
                cur.execute(sql, (ticker,))
                row = cur.fetchone()
                if row:
                    columns = [desc[0] for desc in cur.description]
                    return Position.from_db_row(row, columns)
        except Exception as e:
            print(f"❌ 포지션 조회 실패: {e}")
        return None

    def get_open_positions(self) -> List[Position]:
        """모든 열린 포지션 조회"""
        sql = """
        SELECT id, ticker, name, entry_price, entry_date, exit_price, exit_date,
               quantity, pattern, stop_loss, take_profit, status, profit_pct,
               signal_data, created_at, updated_at
        FROM positions
        WHERE status = 'open'
        ORDER BY entry_date DESC
        """
        positions = []
        try:
            with self.cursor() as cur:
                cur.execute(sql)
                columns = [desc[0] for desc in cur.description]
                for row in cur.fetchall():
                    positions.append(Position.from_db_row(row, columns))
        except Exception as e:
            print(f"❌ 포지션 목록 조회 실패: {e}")
        return positions

    def has_open_position(self, ticker: str) -> bool:
        """열린 포지션 존재 여부"""
        sql = "SELECT 1 FROM positions WHERE ticker = %s AND status = 'open' LIMIT 1"
        try:
            with self.cursor() as cur:
                cur.execute(sql, (ticker,))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"❌ 포지션 확인 실패: {e}")
        return False

    def close_position(
        self,
        ticker: str,
        exit_price: float,
        status: PositionStatus,
        profit_pct: float
    ) -> bool:
        """포지션 청산"""
        sql = """
        UPDATE positions
        SET exit_price = %s, exit_date = NOW(), status = %s, profit_pct = %s
        WHERE ticker = %s AND status = 'open'
        """
        try:
            with self.cursor() as cur:
                cur.execute(sql, (exit_price, status.value, profit_pct, ticker))
                return cur.rowcount > 0
        except Exception as e:
            print(f"❌ 포지션 청산 실패: {e}")
        return False

    def count_open_positions(self) -> int:
        """열린 포지션 개수"""
        sql = "SELECT COUNT(*) FROM positions WHERE status = 'open'"
        try:
            with self.cursor() as cur:
                cur.execute(sql)
                result = cur.fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"❌ 포지션 개수 조회 실패: {e}")
        return 0

    # ========================================
    # Signal CRUD
    # ========================================

    def add_signal(self, signal: Signal) -> Optional[int]:
        """신호 기록 추가"""
        sql = """
        INSERT INTO signals (
            ticker, name, pattern, price, volume_surge, breakout_pct,
            resistance_price, signal_date, notified, position_opened, signal_data
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ticker, signal_date) DO UPDATE SET
            notified = EXCLUDED.notified,
            position_opened = EXCLUDED.position_opened
        RETURNING id
        """
        try:
            with self.cursor() as cur:
                cur.execute(sql, (
                    signal.ticker,
                    signal.name,
                    signal.pattern,
                    signal.price,
                    signal.volume_surge,
                    signal.breakout_pct,
                    signal.resistance_price,
                    signal.signal_date or datetime.now().date(),
                    signal.notified,
                    signal.position_opened,
                    json.dumps(signal.signal_data) if signal.signal_data else None,
                ))
                result = cur.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"❌ 신호 기록 실패: {e}")
            return None

    def has_signal_today(self, ticker: str) -> bool:
        """오늘 이미 신호가 발생했는지 확인 (중복 알림 방지)"""
        sql = """
        SELECT 1 FROM signals
        WHERE ticker = %s AND signal_date = CURRENT_DATE AND notified = TRUE
        LIMIT 1
        """
        try:
            with self.cursor() as cur:
                cur.execute(sql, (ticker,))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"❌ 신호 확인 실패: {e}")
        return False

    def mark_signal_notified(self, ticker: str) -> bool:
        """신호 알림 완료 표시"""
        sql = """
        UPDATE signals
        SET notified = TRUE
        WHERE ticker = %s AND signal_date = CURRENT_DATE
        """
        try:
            with self.cursor() as cur:
                cur.execute(sql, (ticker,))
                return cur.rowcount > 0
        except Exception as e:
            print(f"❌ 신호 업데이트 실패: {e}")
        return False

    def mark_signal_position_opened(self, ticker: str) -> bool:
        """신호에 포지션 오픈 완료 표시"""
        sql = """
        UPDATE signals
        SET position_opened = TRUE
        WHERE ticker = %s AND signal_date = CURRENT_DATE
        """
        try:
            with self.cursor() as cur:
                cur.execute(sql, (ticker,))
                return cur.rowcount > 0
        except Exception as e:
            print(f"❌ 신호 position_opened 업데이트 실패: {e}")
        return False

    def get_recent_signals(self, days: int = 7) -> List[Signal]:
        """최근 신호 조회"""
        sql = """
        SELECT id, ticker, name, pattern, price, volume_surge, breakout_pct,
               resistance_price, signal_date, notified, position_opened,
               signal_data, created_at
        FROM signals
        WHERE signal_date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY signal_date DESC, created_at DESC
        """
        signals = []
        try:
            with self.cursor() as cur:
                cur.execute(sql, (days,))
                columns = [desc[0] for desc in cur.description]
                for row in cur.fetchall():
                    signals.append(Signal.from_db_row(row, columns))
        except Exception as e:
            print(f"❌ 신호 목록 조회 실패: {e}")
        return signals

    # ========================================
    # Trade History & Statistics
    # ========================================

    def get_closed_positions(self, limit: int = 15) -> List[Position]:
        """청산된 포지션 조회 (최근 거래 내역)"""
        sql = """
        SELECT id, ticker, name, entry_price, entry_date, exit_price, exit_date,
               quantity, pattern, stop_loss, take_profit, status, profit_pct,
               signal_data, created_at, updated_at
        FROM positions
        WHERE status != 'open'
        ORDER BY exit_date DESC
        LIMIT %s
        """
        positions = []
        try:
            with self.cursor() as cur:
                cur.execute(sql, (limit,))
                columns = [desc[0] for desc in cur.description]
                for row in cur.fetchall():
                    positions.append(Position.from_db_row(row, columns))
        except Exception as e:
            print(f"❌ 거래 내역 조회 실패: {e}")
        return positions

    def get_trade_stats(self) -> dict:
        """거래 통계 조회"""
        sql = """
        SELECT
            COUNT(*) as total_trades,
            COUNT(CASE WHEN profit_pct > 0 THEN 1 END) as wins,
            COUNT(CASE WHEN profit_pct <= 0 THEN 1 END) as losses,
            COALESCE(AVG(profit_pct), 0) as avg_profit,
            COALESCE(MAX(profit_pct), 0) as max_profit,
            COALESCE(MIN(profit_pct), 0) as max_loss,
            COALESCE(SUM(profit_pct), 0) as total_profit,
            COUNT(CASE WHEN status = 'stop_loss' THEN 1 END) as stop_loss_count,
            COUNT(CASE WHEN status = 'take_profit' THEN 1 END) as take_profit_count,
            COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired_count,
            COUNT(CASE WHEN status = 'closed' THEN 1 END) as manual_close_count
        FROM positions
        WHERE status != 'open'
        """
        stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'avg_profit': 0.0,
            'max_profit': 0.0,
            'max_loss': 0.0,
            'total_profit': 0.0,
            'stop_loss_count': 0,
            'take_profit_count': 0,
            'expired_count': 0,
            'manual_close_count': 0,
        }
        try:
            with self.cursor() as cur:
                cur.execute(sql)
                row = cur.fetchone()
                if row:
                    stats['total_trades'] = row[0] or 0
                    stats['wins'] = row[1] or 0
                    stats['losses'] = row[2] or 0
                    stats['avg_profit'] = float(row[3] or 0)
                    stats['max_profit'] = float(row[4] or 0)
                    stats['max_loss'] = float(row[5] or 0)
                    stats['total_profit'] = float(row[6] or 0)
                    stats['stop_loss_count'] = row[7] or 0
                    stats['take_profit_count'] = row[8] or 0
                    stats['expired_count'] = row[9] or 0
                    stats['manual_close_count'] = row[10] or 0

                    if stats['total_trades'] > 0:
                        stats['win_rate'] = (stats['wins'] / stats['total_trades']) * 100
        except Exception as e:
            print(f"❌ 통계 조회 실패: {e}")
        return stats

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
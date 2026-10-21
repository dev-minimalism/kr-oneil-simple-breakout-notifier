# William O'Neil Breakout Trading Bot

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![pykrx](https://img.shields.io/badge/pykrx-0A5BAA)](https://github.com/sharebook-kr/pykrx)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org/bots)

**윌리엄 오닐 돌파매매 봇 (CAN SLIM)**

한국 주식 감시 종목에서 피벗 포인트 돌파를 자동으로 감지해 텔레그램으로 알림을 보내고, 신호가 난 종목을 가상 포지션으로 추적하는 매매 신호 알림 봇입니다. 실제 주문은 넣지 않습니다.

## Features

- **패턴 감지**: 피벗 포인트 돌파 (실시간 봇). 백테스트는 컵앤핸들, 베이스 돌파 패턴도 지원합니다.
- **시장 지원**: 한국 주식 (pykrx)
- **텔레그램 통합**: 명령어로 감시 종목 관리, 신호 알림, 수동 스캔
- **포지션 추적**: 신호 발생 시 가상 포지션을 자동 등록하고 손절, 익절, 보유기간 만료 시 자동 청산 알림
- **중복 알림 방지**: 같은 종목은 하루에 한 번만 알림, 보유 중인 종목은 스캔에서 제외
- **저장소 선택**: JSON 파일(기본) 또는 SSH 터널을 통한 PostgreSQL
- **백테스트**: 과거 데이터로 전략 성과 검증 (승률, 수익률, 패턴별 통계)

## Installation

Python 3.12 이상이 필요합니다.

```bash
# 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 패키지 설치
pip install -e .

# 개발 도구 포함 설치 (pytest, black, ruff, mypy)
pip install -e ".[dev]"
```

## Quick Start

### 1. 설정

`.env.example`을 복사해 `.env` 파일을 만들고 텔레그램 정보를 입력합니다.

```bash
cp .env.example .env
```

```bash
TELEGRAM_TOKEN=your_bot_token      # @BotFather에서 발급
TELEGRAM_CHAT_ID=your_chat_id      # @userinfobot에서 확인
```

`.env`는 현재 작업 디렉토리에서 먼저 찾고, 없으면 프로젝트 루트에서 찾습니다. 전체 설정은 [Configuration](#configuration)을 참고하세요.

### 2. 봇 실행

```bash
python -m kr_oneil_simple
# 또는 설치된 콘솔 스크립트 사용
kr-oneil-simple
```

봇을 시작하면 텔레그램으로 시작 메시지를 보내고, `SCAN_INTERVAL`(기본 30분)마다 다음 작업을 반복합니다.

1. 보유 포지션의 현재가를 확인하고 손절, 익절, 만료 조건에 해당하면 청산 알림을 보냅니다.
2. 장중이면 감시 종목을 스캔하고, 신호가 나오면 포지션을 등록한 뒤 알림을 보냅니다.

텔레그램 명령어는 백그라운드 스레드에서 계속 받습니다.

### 3. 백그라운드 실행 (서버)

> ⚠️ 장중 판단은 서버의 로컬 시간을 기준으로 합니다. 서버 시간대가 KST가 아니면 `TZ=Asia/Seoul`을 지정하세요.

서버에서 봇을 백그라운드로 실행하려면 `nohup`을 사용합니다.

```bash
# 백그라운드 실행 (-u 옵션으로 버퍼링 없이 즉시 로그 기록)
nohup python -u -m kr_oneil_simple > bot.log 2>&1 &

# 날짜+시간 로그 파일명
nohup python -u -m kr_oneil_simple > bot_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# logs 폴더에 저장 (권장)
mkdir -p logs
nohup python -u -m kr_oneil_simple > logs/bot_$(date +%Y%m%d).log 2>&1 &

# 프로세스 ID 확인
echo $!

# 실행 중인 프로세스 확인
ps aux | grep kr_oneil_simple

# 로그 실시간 확인
tail -f logs/bot_*.log

# 봇 종료
pkill -f "python -m kr_oneil_simple"
```

**systemd 서비스로 등록 (권장)**

`/etc/systemd/system/oneil-bot.service` 파일 생성:

```ini
[Unit]
Description=William O'Neil Breakout Trading Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/kr-oneil-simple-breakout-notifier
Environment=PATH=/path/to/kr-oneil-simple-breakout-notifier/.venv/bin
Environment=TZ=Asia/Seoul
Environment=PYTHONUNBUFFERED=1
ExecStart=/path/to/kr-oneil-simple-breakout-notifier/.venv/bin/python -m kr_oneil_simple
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 등록 및 시작
sudo systemctl daemon-reload
sudo systemctl enable oneil-bot
sudo systemctl start oneil-bot

# 상태 확인
sudo systemctl status oneil-bot

# 로그 확인
sudo journalctl -u oneil-bot -f
```

`positions.json`, `signals.json`, `watchlist.json`은 작업 디렉토리(`WorkingDirectory`)에 저장됩니다.

### 4. 즉시 스캔 (1회)

```bash
python -m kr_oneil_simple scan
```

장 시간과 관계없이 감시 종목을 한 번 스캔합니다. 봇 실행과 같은 설정과 저장소를 쓰기 때문에, 신호가 나오면 **텔레그램 알림을 보내고 포지션도 등록**합니다.

### 5. 백테스트

```bash
python -m kr_oneil_simple backtest                                   # 최근 1년, 자본 1억
python -m kr_oneil_simple backtest --start 2024-01-01 --end 2024-12-31
python -m kr_oneil_simple backtest --capital 50000000
```

---

## Telegram Commands

| 명령어 | 설명 |
|--------|------|
| `/scan` | 즉시 스캔 (백그라운드에서 실행, 완료 시 결과 알림) |
| `/list` | 감시 종목 목록 |
| `/add CODE` | 감시 종목 추가 |
| `/remove CODE` | 감시 종목 삭제 |
| `/positions` | 현재 포지션과 평가 손익 |
| `/close CODE` | 포지션 수동 청산 (현재가 기준) |
| `/trades` | 최근 거래 내역 (최대 15건) |
| `/stats` | 거래 통계 (승률, 평균/최대/누적 수익률, 청산 유형별 건수) |
| `/status` | 시장 상태, 스캔 진행 여부 |
| `/help`, `/start` | 도움말 |

`/scan_kr`, `/add_kr`, `/remove_kr`도 각각 같은 명령어로 동작합니다(이전 버전 호환).

스캔이 이미 진행 중일 때 `/scan`을 보내면 거절 메시지가 옵니다. 수동 스캔 도중에 정기 스캔 차례가 오면 그 회차는 건너뜁니다.

### 사용 예시

```
/add 005930        → 삼성전자 추가
/list              → 감시 종목 확인
/positions         → 보유 포지션 손익 확인
/close 005930      → 삼성전자 포지션 수동 청산
```

---

## Market Hours

| 시간대 (서버 로컬 시간) | 동작 |
|--------|------|
| 평일 08:00 - 17:00 | 포지션 확인 + 감시 종목 스캔 |
| 그 외 (주말 포함) | 포지션 확인만 |

- 정규장(09:00-15:30) 앞뒤로 여유를 둔 시간대입니다.
- 공휴일은 따로 판단하지 않습니다.

---

## Pattern Detection

### 피벗 포인트 돌파 (실시간 봇)

최근 30거래일 일봉(pykrx) 기준으로 다음 조건을 모두 만족하면 신호가 납니다.

| 조건 | 기준 | 설정 |
|------|------|------|
| 저항선 돌파 | 오늘 종가(장중엔 현재가) > 직전 19거래일 최고 종가 | - |
| 거래량 증가 | 오늘 거래량이 직전 29거래일 평균보다 50% 이상 많음 | `VOLUME_SURGE_MIN` |
| 돌파율 | 저항선 대비 0% 초과 5% 이하 (과열 추격 방지) | `BREAKOUT_MAX` |

장중에는 오늘 거래량이 아직 누적 중이어서, 장 초반에는 거래량 조건을 만족하기 어렵습니다.

### 신호 이후 처리

1. 신호를 기록합니다. 같은 종목은 그날 다시 알리지 않습니다.
2. 현재가로 가상 포지션을 등록합니다. 이미 보유 중이면 알림을 보내지 않습니다.
3. 텔레그램으로 신호 알림을 보냅니다.

### 포지션 청산 조건

| 조건 | 기본값 | 설정 |
|------|--------|------|
| 손절 | 진입가 대비 -8% | `STOP_LOSS_PERCENT` |
| 익절 | 진입가 대비 +20% | `TAKE_PROFIT_PERCENT` |
| 보유기간 만료 | 30일 | `MAX_HOLDING_DAYS` |

---

## Backtest

`cup`(컵앤핸들), `pivot`(피벗 돌파), `base`(베이스 돌파) 세 가지 패턴으로 일봉 시뮬레이션을 합니다.

### CLI로 실행

```bash
python -m kr_oneil_simple backtest --start 2024-01-01 --end 2024-12-31 --capital 100000000
```

- 대상 종목: `KR_WATCH_LIST`(또는 기본 종목)의 **앞 20개** (`watchlist.json`이 아님)
- 기간 기본값: 오늘부터 1년 전까지
- 결과: 콘솔 성과 리포트 + `output/kr_backtest_results_{start}_{end}.csv`

### 백테스트 규칙

- 매매 조건: 손절 -8%, 익절 +20%, 보유 30일, 최대 5개 포지션, 포지션당 현재 자본의 20%
- 손절은 당일 **저가** 기준으로 판정하고, 손절가에 청산합니다.
- 패턴 임계값은 엔진에 고정되어 있습니다. `.env`의 패턴, 거래 설정은 CLI 백테스트에 적용되지 않습니다.
- 슬리피지와 수수료는 반영하지 않습니다.

### Python API로 실행

```python
from kr_oneil_simple import BacktestEngine

engine = BacktestEngine(
    initial_capital=100_000_000,
    stop_loss_pct=-7.5,
    take_profit_pct=20.0,
    max_holding_days=30,
    max_positions=5,
    position_size_pct=20.0,
)
engine.run_portfolio_backtest(
    tickers=['005930', '000660', '035720'],
    start_date='2024-01-01',
    end_date='2024-12-31',
    patterns=['pivot'],          # 생략하면 cup, pivot, base 모두
)
engine.print_performance_report()
engine.save_results('backtest_results.csv')
```

---

## Configuration

`.env`에서 설정합니다. 값이 없으면 아래 기본값을 사용합니다.

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TELEGRAM_TOKEN` | - | 텔레그램 봇 토큰 (**필수**) |
| `TELEGRAM_CHAT_ID` | - | 알림 받을 채팅 ID (**필수**) |
| `SCAN_INTERVAL` | `1800` | 스캔 주기 (초) |
| `KR_WATCH_LIST` | 대형주 19종목 | 기본 감시 종목 (쉼표 구분 6자리 코드) |
| `VOLUME_SURGE_MIN` | `50` | 피벗 돌파 최소 거래량 증가율 (%) |
| `BREAKOUT_MAX` | `5` | 피벗 돌파 최대 돌파율 (%) |
| `STOP_LOSS_PERCENT` | `-8.0` | 손절 기준 (%) — `.env.example`은 `-7.5` |
| `TAKE_PROFIT_PERCENT` | `20` | 익절 기준 (%) |
| `MAX_HOLDING_DAYS` | `30` | 최대 보유 기간 (일) |
| `ANALYSIS_PERIOD_DAYS` | `120` | 종목별 조회 기간 (일) |
| `WATCHLIST_FILE` | `watchlist.json` | 감시 종목 저장 파일 |
| `POSITIONS_FILE` | `positions.json` | 포지션 저장 파일 (JSON 모드) |
| `USE_DATABASE` | `false` | `true`면 PostgreSQL 사용 |

`.env.example`에 있는 `CUP_DEPTH_*`, `HANDLE_DEPTH_MAX`, `BASE_*` 값은 설정 객체로 읽기는 하지만, 현재 실시간 봇과 백테스트 어디에서도 쓰이지 않습니다.

### 감시 종목 우선순위

`watchlist.json`이 있으면 그 파일을 우선 사용합니다. `KR_WATCH_LIST`는 파일이 없을 때 쓰는 초기값입니다. 텔레그램 `/add`, `/remove`로 바꾼 내용은 `watchlist.json`에 저장되므로, `.env`의 `KR_WATCH_LIST`를 고쳐도 파일이 있으면 반영되지 않습니다. 반영하려면 `watchlist.json`을 지우거나 텔레그램 명령어로 바꾸세요.

### 저장소

| 모드 | 저장 위치 |
|------|-----------|
| JSON (기본) | 작업 디렉토리의 `positions.json`(포지션, 거래 내역), `signals.json`(당일 신호 기록) |
| PostgreSQL | `USE_DATABASE=true` + 아래 SSH/DB 설정 |

```bash
USE_DATABASE=true

# SSH 터널
SSH_HOST=your_ssh_host
SSH_PORT=22
SSH_USER=your_ssh_user
SSH_KEY_PATH=~/.ssh/id_rsa

# PostgreSQL (SSH 서버 기준 주소)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=oneil_breakout
DB_USER=your_db_user
DB_PASSWORD=your_db_password
```

---

## Project Structure

```
kr-oneil-simple-breakout-notifier/
├── src/kr_oneil_simple/
│   ├── __main__.py          # CLI (run / scan / backtest)
│   ├── bot/detector.py      # BreakoutDetector: 스캔 루프, 텔레그램 명령어, 포지션 추적
│   ├── backtest/engine.py   # BacktestEngine
│   ├── config/settings.py   # 설정 dataclass + .env 로드
│   ├── data/kr_stock.py     # pykrx 래퍼 (OHLCV, 종목명)
│   ├── patterns/
│   │   ├── pivot.py         # 피벗 돌파 (봇 + 백테스트)
│   │   ├── cup_handle.py    # 컵앤핸들 (현재 미사용)
│   │   └── base.py          # 베이스 돌파 (현재 미사용)
│   ├── positions/manager.py # PositionManager (JSON / DB 구현 선택)
│   ├── database/            # SSH 터널 + PostgreSQL 연결, 모델
│   ├── watchlist/manager.py # 감시 종목 (watchlist.json)
│   ├── market/status.py     # 장중 여부 판단
│   └── telegram/
│       ├── client.py        # 텔레그램 API (메시지 전송, 롱 폴링)
│       └── formatter.py     # 신호 메시지 포맷
├── scripts/                 # 신호 진단 스크립트
├── .env.example
├── pyproject.toml
└── README.md
```

---

## Python API

```python
from kr_oneil_simple import BreakoutDetector, load_settings

settings = load_settings()
detector = BreakoutDetector(settings)

detector.run()          # 봇 실행 (무한 루프)
# 또는
detector.run_scan()     # 1회 스캔 (신호 리스트 반환)
```

패키지에서 바로 가져올 수 있는 이름: `BreakoutDetector`, `BacktestEngine`, `Settings`, `load_settings`, `PositionManager`, `WatchlistManager`

---

## Development

```bash
pip install -e ".[dev]"

black src/
ruff check src/
mypy src/
```

### 신호 진단 스크립트

신호가 예상과 다르게 나오거나 안 나올 때 프로젝트 루트에서 실행합니다. 자세한 내용은 [scripts/README.md](scripts/README.md)를 참고하세요.

```bash
python scripts/check_realtime_data.py      # pykrx가 장중 실시간 데이터를 주는지 확인
python scripts/check_signal_conditions.py  # 종목별 신호 조건 충족 여부 상세 분석
python scripts/check_backtest_signals.py   # 최근 3주 동안 신호가 났어야 하는 날짜 찾기
```

---

## Troubleshooting

### ModuleNotFoundError: No module named 'pkg_resources'

```bash
pip install setuptools
```

### 텔레그램 메시지가 안 옴

1. 봇 토큰 확인
2. Chat ID 확인 (`@userinfobot`에서 확인)
3. 봇에게 먼저 `/start` 메시지 보내기

### 장중인데 스캔을 안 함

서버 시간대를 확인하세요. 장중 판단은 서버 로컬 시간(평일 08:00-17:00)을 기준으로 합니다. `TZ=Asia/Seoul`을 설정하세요.

### 신호가 안 나옴

- 이미 보유 중인 종목이나 오늘 알림을 보낸 종목은 스캔에서 건너뜁니다.
- `python scripts/check_signal_conditions.py`로 조건별 충족 여부를 확인하세요.

### 감시 종목을 바꿨는데 반영이 안 됨

`watchlist.json`이 `KR_WATCH_LIST`보다 우선합니다. [감시 종목 우선순위](#감시-종목-우선순위)를 참고하세요.

### 한국 주식 데이터 조회 실패

```bash
pip install --upgrade pykrx
```

종목 코드는 6자리 숫자입니다 (예: `005930`).

### SSL 인증서 오류 (macOS)

```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

### 너무 많은/잘못된 신호

`.env`에서 조건을 강화합니다.

```bash
VOLUME_SURGE_MIN=70     # 50 → 70으로 상향
BREAKOUT_MAX=3          # 5 → 3으로 하향
```

---

## Disclaimer

- 과거 성과는 미래를 보장하지 않습니다
- 백테스트 결과는 슬리피지, 수수료 미포함
- 실제 투자 전 충분한 검토 필요
- 본 소프트웨어 사용으로 인한 손실에 대해 책임지지 않습니다

---

## License

MIT License

## Author

Yungoo Park (ygpark@lendingmachine.co.kr)

## References

- 윌리엄 오닐 저서: "How to Make Money in Stocks"
- CAN SLIM 투자 전략

# William O'Neil Breakout Trading Bot

**윌리엄 오닐 돌파매매 봇 (CAN SLIM)**

한국 주식 시장에서 차트 돌파 패턴(피벗 포인트 돌파)을 자동 감지하고 텔레그램으로 알림을 보내는 자동화 트레이딩 신호 시스템입니다.

## Features

- **패턴 감지**: 피벗 포인트 돌파
- **시장 지원**: 한국 주식 (pykrx)
- **텔레그램 통합**: 명령어로 종목 관리, 실시간 알림
- **포지션 추적**: 자동 손절, 익절, 만료 알림
- **백테스트**: 과거 데이터로 전략 성과 검증

## Installation

```bash
# 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 패키지 설치
pip install -e .
```

## Quick Start

### 1. 설정

`.env.example`을 복사하여 `.env` 파일을 생성하고 텔레그램 설정을 입력합니다:

```bash
cp .env.example .env
```

`.env` 파일 내용:

```bash
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 2. 봇 실행

```bash
python -m kr_oneil_simple
```

### 3. 백그라운드 실행 (서버)

서버에서 봇을 백그라운드로 실행하려면 `nohup`을 사용합니다:

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

### 4. 즉시 스캔

```bash
python -m kr_oneil_simple scan
```

### 5. 백테스트

```bash
python -m kr_oneil_simple backtest --capital 100000000
```

---

## Telegram Commands

| 명령어 | 설명 |
|--------|------|
| `/scan` | 즉시 스캔 |
| `/list` | 감시 종목 목록 |
| `/add CODE` | 종목 추가 |
| `/remove CODE` | 종목 삭제 |
| `/positions` | 현재 포지션 보기 |
| `/close CODE` | 포지션 수동 청산 |
| `/trades` | 최근 거래 내역 (15건) |
| `/stats` | 거래 통계 (승률, 수익률) |
| `/status` | 시장 상태 확인 |
| `/help` | 도움말 |

### 사용 예시

```
/add 005930        → 삼성전자 추가
/list              → 감시 종목 확인
/status            → 시장 상태 확인
```

---

## Market Hours (KST)

| 시간대 | 동작 |
|--------|------|
| 09:00 - 15:30 (평일) | 한국 주식 스캔 |
| 그 외 | 대기 |

---

## Pattern Detection

### 피벗 포인트 돌파
- 20일 저항선 돌파
- 50% 이상 거래량 증가
- 돌파율 0~5%

---

## Backtest

### CLI로 실행

```bash
python -m kr_oneil_simple backtest --capital 100000000
python -m kr_oneil_simple backtest --start 2024-01-01 --end 2024-12-31
```

### Python API로 실행

```python
from kr_oneil_simple import BacktestEngine

engine = BacktestEngine(initial_capital=100_000_000)
engine.run_portfolio_backtest(
    tickers=['005930', '000660', '035720'],
    start_date='2024-01-01',
    end_date='2024-12-31'
)
engine.print_performance_report()
engine.save_results('backtest_results.csv')
```

---

## Configuration

`.env` 파일 주요 설정:

```bash
# 텔레그램 (필수)
TELEGRAM_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# 스캔 설정
SCAN_INTERVAL=1800              # 30분 (초)

# 워치리스트
KR_WATCH_LIST=005930,000660     # 한국 종목 코드 (쉼표 구분)

# 패턴 감지 설정
VOLUME_SURGE_MIN=50             # 최소 거래량 증가율 (%)

# 거래 설정
STOP_LOSS_PERCENT=-7.5          # 손절 기준 (%)
```

---

## Project Structure

```
oneil-breakout/
├── src/kr_oneil_simple/
│   ├── __init__.py          # 패키지 진입점
│   ├── __main__.py          # CLI
│   ├── bot/detector.py      # 메인 봇 클래스
│   ├── backtest/engine.py   # 백테스트 엔진
│   ├── config/settings.py   # 설정 관리
│   ├── data/kr_stock.py     # 한국 주식 데이터 (pykrx)
│   ├── patterns/pivot.py    # 피벗 돌파 패턴
│   ├── positions/manager.py # 포지션 관리
│   ├── watchlist/manager.py # 워치리스트 관리
│   ├── market/status.py     # 시장 상태 확인
│   └── telegram/
│       ├── client.py        # 텔레그램 API
│       └── formatter.py     # 메시지 포맷
├── .env.example             # 환경변수 예시
├── .env                     # 사용자 설정 (gitignore)
├── pyproject.toml
└── README.md
```

---

## Python API

```python
from kr_oneil_simple import (
    BreakoutDetector,
    BacktestEngine,
    Settings,
    load_settings,
    PositionManager,
    WatchlistManager
)

# 설정 로드
settings = load_settings()

# 봇 실행
detector = BreakoutDetector(settings)
detector.run()

# 또는 1회 스캔만
detector.run_scan()
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

### 한국 주식 데이터 조회 실패

```bash
pip install --upgrade pykrx
```

종목 코드는 6자리 숫자 (예: `005930`)

### SSL 인증서 오류 (macOS)

```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

### 너무 많은/잘못된 신호

`.env`에서 조건 강화:

```bash
VOLUME_SURGE_MIN=70     # 50 → 70으로 상향
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
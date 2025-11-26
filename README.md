# William O'Neil Breakout Trading Bot

**윌리엄 오닐 돌파매매 봇 (CAN SLIM)**

미국/한국 주식 시장에서 차트 돌파 패턴(컵앤핸들, 피벗 포인트 돌파, 베이스 돌파)을 자동 감지하고 텔레그램으로 알림을 보내는 자동화 트레이딩 신호 시스템입니다.

## Features

- **패턴 감지**: 컵앤핸들, 피벗 포인트 돌파, 베이스 돌파
- **시장 지원**: 미국 주식 (yfinance) + 한국 주식 (pykrx)
- **스마트 스캔**: 시간대별 자동 시장 선택 (한국 장중/미국 장중)
- **텔레그램 통합**: 명령어로 종목 관리, 실시간 알림
- **포지션 추적**: 자동 손절(-8%), 익절(+20%), 만료(30일) 알림
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

`config.py` 파일을 생성하고 텔레그램 설정을 입력합니다:

```python
TELEGRAM_TOKEN = "your_bot_token"
CHAT_ID = "your_chat_id"
```

또는 환경변수로 설정:

```bash
export TELEGRAM_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

### 2. 봇 실행

```bash
python -m oneil_breakout
```

### 3. 즉시 스캔

```bash
python -m oneil_breakout scan           # 전체 시장
python -m oneil_breakout scan --us      # 미국만
python -m oneil_breakout scan --kr      # 한국만
```

### 4. 백테스트

```bash
python -m oneil_breakout backtest --market US --capital 100000000
```

---

## Telegram Commands

| 명령어 | 설명 |
|--------|------|
| `/scan` | 전체 시장 즉시 스캔 |
| `/scan_kr` | 한국장만 스캔 |
| `/scan_us` | 미국장만 스캔 |
| `/positions` | 현재 포지션 보기 |
| `/close TICKER` | 포지션 수동 청산 |
| `/add_us TICKER` | 미국 종목 추가 |
| `/add_kr CODE` | 한국 종목 추가 |
| `/remove_us TICKER` | 미국 종목 삭제 |
| `/remove_kr CODE` | 한국 종목 삭제 |
| `/list` | 감시 종목 목록 |
| `/status` | 시장 상태 확인 |
| `/help` | 도움말 |

### 사용 예시

```
/add_us NVDA       → 미국 주식 추가
/add_kr 005930     → 한국 주식 추가 (삼성전자)
/list              → 감시 종목 확인
/status            → 시장 상태 확인
```

---

## Market Hours (KST)

봇은 시간대에 따라 자동으로 해당 시장을 스캔합니다:

| 시간대 | 동작 |
|--------|------|
| 09:00 - 15:30 (평일) | 한국 주식 스캔 |
| 22:30 - 06:00 (평일) | 미국 주식 스캔 |
| 그 외 | 대기 (스캔 안함) |

---

## Pattern Detection

### 1. 피벗 포인트 돌파
- 20일 저항선 돌파
- 50% 이상 거래량 증가
- 돌파율 0~5%

### 2. 컵앤핸들
- 12-40% 깊이의 컵 형성
- 12% 미만의 핸들
- 저항선 돌파

### 3. 베이스 돌파
- 횡보 구간(변동성 15% 미만) 후 돌파
- 40% 이상 거래량 증가
- 돌파율 0~7%

---

## Backtest

### CLI로 실행

```bash
python -m oneil_breakout backtest --market US --capital 100000000
python -m oneil_breakout backtest --market KR --start 2024-01-01 --end 2024-12-31
```

### Python API로 실행

```python
from oneil_breakout import BacktestEngine

engine = BacktestEngine(initial_capital=100_000_000)
engine.run_portfolio_backtest(
    tickers=['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA'],
    start_date='2024-01-01',
    end_date='2024-12-31',
    market='US',
    patterns=['pivot', 'base']
)
engine.print_performance_report()
engine.save_results('backtest_results.csv')
```

### 성과 보고서 예시

```
📊 백테스트 성과 보고서
============================================================

💰 자본
   초기 자본:         100,000,000원
   최종 자본:         112,500,000원
   총 수익:            12,500,000원
   수익률:                   12.50%
   연간 수익률:              12.50%

📈 거래 통계
   총 거래:                     25건
   수익 거래:                   16건
   손실 거래:                    9건
   승률:                       64.00%

📊 패턴별 성과
패턴          거래수     평균수익      승률
----------------------------------------
컵앤핸들          10건      7.20%    70.0%
피벗돌파           8건      9.50%    62.5%
베이스돌파         7건      6.80%    57.1%
```

### 리스크 관리

| 항목 | 기본값 |
|------|--------|
| 손절 | -8% |
| 익절 | +20% |
| 최대 보유 기간 | 30일 |
| 포지션 크기 | 자본의 20% |
| 최대 포지션 | 5개 |

---

## Configuration

`config.py` 주요 설정:

```python
# 텔레그램 (필수)
TELEGRAM_TOKEN = "your_token"
CHAT_ID = "your_chat_id"

# 스캔 설정
SCAN_INTERVAL = 1800      # 30분 (초)
SCAN_US_MARKET = True
SCAN_KR_MARKET = True

# 패턴 감지 설정
VOLUME_SURGE_MIN = 50     # 최소 거래량 증가율 (%)
BREAKOUT_MAX = 5          # 최대 돌파율 (%)
CUP_DEPTH_MIN = 12        # 컵 최소 깊이 (%)
CUP_DEPTH_MAX = 40        # 컵 최대 깊이 (%)

# 거래 설정
STOP_LOSS_PERCENT = -7.5  # 손절 기준 (%)
```

---

## Project Structure

```
oneil-breakout/
├── src/oneil_breakout/
│   ├── __init__.py          # 패키지 진입점
│   ├── __main__.py          # CLI
│   ├── bot/detector.py      # 메인 봇 클래스
│   ├── backtest/engine.py   # 백테스트 엔진
│   ├── config/settings.py   # 설정 관리
│   ├── data/
│   │   ├── us_stock.py      # 미국 주식 데이터
│   │   └── kr_stock.py      # 한국 주식 데이터
│   ├── patterns/
│   │   ├── pivot.py         # 피벗 돌파
│   │   ├── cup_handle.py    # 컵앤핸들
│   │   └── base.py          # 베이스 돌파
│   ├── positions/manager.py # 포지션 관리
│   ├── watchlist/manager.py # 워치리스트 관리
│   └── telegram/
│       ├── client.py        # 텔레그램 API
│       └── formatter.py     # 메시지 포맷
├── config.py                # 사용자 설정
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Python API

```python
from oneil_breakout import (
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
detector.run_manual_scan(scan_kr=True, scan_us=True)
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

`config.py`에서 조건 강화:

```python
VOLUME_SURGE_MIN = 70   # 50 → 70으로 상향
BREAKOUT_MAX = 3        # 5 → 3으로 하향
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
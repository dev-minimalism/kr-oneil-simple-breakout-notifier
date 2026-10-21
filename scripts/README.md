# 진단 스크립트

신호 감지 로직의 문제를 진단하기 위한 스크립트들입니다.

## 사용법

프로젝트 루트에서 실행:

```bash
# 가상환경 활성화
source .venv/bin/activate

# 스크립트 실행
python scripts/check_realtime_data.py
python scripts/check_signal_conditions.py
python scripts/check_backtest_signals.py
```

## 스크립트 설명

### check_realtime_data.py
pykrx가 장중에 실시간 데이터를 반환하는지 확인합니다.
- 장중(09:00~15:30)에 실행하여 오늘 데이터 존재 여부 확인
- 현재가가 실시간인지 확인

### check_signal_conditions.py
현재 시점에서 각 종목의 신호 조건 충족 여부를 상세 분석합니다.
- 거래량 증가율 계산
- 저항선 돌파 여부
- 각 조건별 충족/미충족 이유

### check_backtest_signals.py
최근 3주간 워치리스트 전체에서 신호가 발생했어야 하는 날짜를 찾습니다.
- 조건 완화 테스트 포함
- 실제 신호 발생 날짜/종목 출력

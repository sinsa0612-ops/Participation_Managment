# 사업비 인건비 배분 앱 (Participation Management)

정부 과제에 참여하는 연구원의 **인건비 분배**를 관리하는 웹 애플리케이션입니다.
연구원·사업(과제)·참여 정보를 입력하면, 제약 조건(참여율 상한, 동시 참여 과제 수,
고용형태별 예산 등)에 맞춰 인건비를 **자동 배분**합니다.

## 주요 기능

- **👥 멤버 관리** — 연구원 등록 (급여, 참여율 상한, 동시 참여 과제 수 제한 등)
- **📁 사업 관리** — 과제 등록 (고용형태별 연간 예산, 연구책임자, 기간, 필수 참여자)
- **📊 자동 배분** — 제약 조건을 반영해 연구원을 과제에 배분하고 인건비 계산
- **🔍 참여 현황** — 연구원별 동시 참여 과제·총 참여율·인건비 분석

## 기술 스택

| 구분 | 스택 |
|------|------|
| 프론트엔드 | React 19 · TypeScript · Vite |
| 백엔드 | FastAPI · SQLAlchemy · Uvicorn (Python 3.12+) |
| DB | SQLite (앱 첫 실행 시 자동 생성) |

## 사전 준비물

개발/실행하려면 아래 도구가 필요합니다.

- **[Node.js](https://nodejs.org/)** (프론트엔드)
- **[Python 3.12+](https://www.python.org/)** 와 **[uv](https://docs.astral.sh/uv/)** (백엔드 패키지 관리)

> macOS 예시: `brew install node uv`

## 설치 & 실행

먼저 저장소를 내려받습니다.

```bash
git clone https://github.com/sinsa0612-ops/Participation_Managment.git
cd Participation_Managment
```

백엔드와 프론트엔드를 **각각 다른 터미널**에서 실행합니다.

### 1) 백엔드 (FastAPI, 포트 8001)

```bash
cd salary-app/backend

# (선택) 샘플 데이터 투입 — 비어있는 상태로 시작하려면 생략
uv run python seed.py

# 서버 실행
uv run uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

- DB(`salary.db`)와 테이블은 첫 실행 시 자동 생성됩니다.
- `--reload`: 코드 변경 시 자동 재시작 (개발용)

### 2) 프론트엔드 (Vite + React, 포트 5173)

```bash
cd salary-app/frontend
npm install
npm run dev
```

### 접속 주소

| | 주소 |
|---|---|
| 프론트엔드 | http://localhost:5173 |
| 백엔드 API | http://localhost:8001 |
| API 문서 (Swagger) | http://localhost:8001/docs |

> 프론트엔드는 개발 시 API 요청을 백엔드(8001)로 프록시합니다. **두 서버를 함께 켜 두어야** 정상 동작합니다.

## 환경 설정 (선택)

기본값으로 바로 동작하며, 값을 바꾸려면 `.env`를 만들어 사용합니다.

```bash
cd salary-app/backend
cp .env.example .env   # 필요한 값만 수정
```

- `SERVER_PORT` — API 포트 (기본 8001)
- `CORS_ORIGINS` — 허용 출처 (기본 `["http://localhost:5173"]`)
- `BASE_DATE` — 배분 알고리즘 기준일 (미설정 시 실제 오늘)

## 프로젝트 구조

```
salary-app/
├── backend/          # FastAPI 백엔드
│   ├── app/          #   모델·라우터·서비스·배분 로직
│   ├── main.py       #   앱 진입점
│   └── seed.py       #   샘플 데이터 시드
└── frontend/         # React + Vite 프론트엔드
    └── src/          #   컴포넌트·화면
docs/                 # 프로토타입·설계 문서
```

## Windows 설치파일(.exe) 빌드 (선택)

일반 사용자에게 배포할 실행 파일이 필요하면, `salary-app/` 안의 `build.bat`,
`installer/salary-app.iss`, `배포_빌드방법.md`를 참고해 **Windows에서** 빌드할 수 있습니다.
(PyInstaller + Inno Setup 기반 — macOS/Linux에서는 사용하지 않습니다.)

## 데이터에 관하여

이 저장소에는 **실제 인건비/개인정보 데이터가 포함되어 있지 않습니다.**
내려받으면 빈 DB에서 시작하며, 필요하면 `seed.py`로 샘플 데이터를 넣을 수 있습니다.

## 라이선스

[MIT License](LICENSE)

# FastAPI 백엔드 마이그레이션 계획서

## 1. 배경 및 목적 (Background & Motivation)
현재 `docs/salary_distribution.tsx`에 구현된 React 기반의 프로토타입은 프론트엔드에서 모든 데이터 상태와 복잡한 분배 알고리즘을 처리하고 있습니다. 이를 구조화하고 영속성을 보장하며, 향후 확장성(예: 월별 슬라이딩 체크 정교화, 고용형태별 예산 매칭 등 고도화 사항 적용)을 확보하기 위해 Python 3.12, FastAPI, SQLite 기반의 백엔드로 마이그레이션합니다.

## 2. 범위 및 영향 (Scope & Impact)
- **데이터베이스:** 프로토타입의 메모리(useState) 상태를 SQLite 관계형 데이터베이스로 전환.
- **비즈니스 로직:** 프론트엔드의 `autoDistribute` 함수를 백엔드의 독립적인 서비스 레이어로 이관.
- **API 서버:** 클라이언트(React 등)에서 데이터를 조회, 생성, 수정, 삭제하고 배분 알고리즘을 트리거할 수 있는 RESTful API 제공.
- **영향:** 기존 단일 파일 프로토타입 구조에서 클라이언트-서버 구조로 전환되며, 데이터의 영속성이 보장됩니다.

## 3. 제안하는 솔루션 (Proposed Solution)
### 3.1 기술 스택
- **언어:** Python 3.12
- **프레임워크:** FastAPI (비동기 I/O, Pydantic을 이용한 자동 문서화 및 데이터 검증)
- **데이터베이스:** SQLite (가볍고 서버리스, 초기 구축에 적합)
- **ORM:** SQLAlchemy (데이터 모델링 및 쿼리 추상화)
- **패키지 관리:** Poetry 또는 pip (requirements.txt)

### 3.2 데이터 모델링 (SQLAlchemy)
1.  **Member (연구원)**
    - id (PK), name, employ_type, rank, salary, max_rate, max_projects
2.  **Project (사업)**
    - id (PK), name, start_date, end_date
3.  **ProjectBudget (연도별 예산)**
    - id (PK), project_id (FK), year, employ_type, amount
4.  **ProjectRequirement (필수 참여자)**
    - id (PK), project_id (FK), member_id (FK), role (chief, staff)
5.  **ProjectConstraint (사업 한정 참여율 상한)**
    - id (PK), project_id (FK), member_id (FK), max_rate
6.  **Participation (배분 결과/참여 내역)**
    - id (PK), project_id (FK), member_id (FK), role, start_date, end_date, rate, cost

### 3.3 핵심 알고리즘 구조화
`autoDistribute` 로직을 `DistributionService` 클래스로 추상화합니다.
- 사업 우선순위 정렬 (종료일 빠른 순 -> 예산 큰 순)
- 월별 동시 참여 수 계산 로직 (종료 6개월 미만 예외 규칙 적용)
- 잔여 예산 및 개인별 최대 참여율을 고려한 할당량(천원 단위 반올림) 계산

### 3.4 디렉토리 구조
```text
backend/
├── app/
│   ├── main.py            # FastAPI 애플리케이션 진입점
│   ├── database.py        # SQLite 및 SQLAlchemy 설정
│   ├── models/            # SQLAlchemy 데이터베이스 모델
│   ├── schemas/           # Pydantic Pydantic 모델 (요청/응답)
│   ├── routers/           # API 엔드포인트 라우터
│   └── services/          # 비즈니스 로직 (분배 알고리즘 등)
├── tests/                 # 단위 테스트 (pytest)
└── requirements.txt       # 의존성 패키지
```

## 4. 대안 고려 (Alternatives Considered)
- **PostgreSQL / MySQL:** 안정성과 동시성 처리가 뛰어나지만, 현재 프로토타입 단계 및 소규모 관리 인원(연구원 10여명, 사업 7개)을 고려할 때 설정과 운영 비용이 낮은 SQLite가 가장 합리적인 선택입니다. 향후 SQLAlchemy의 장점을 살려 접속 URL만 변경하여 RDBMS로 쉽게 전환할 수 있습니다.
- **Node.js (Express / NestJS API):** 프론트엔드와 언어 통일성을 가질 수 있으나, 향후 고도화될 데이터 연산 및 데이터 처리 스크립트 작성에 있어서는 Python 생태계가 유리합니다.

## 5. 단계별 구현 계획 (Implementation Plan)
- **Phase 0: 마이그레이션 계획 문서화**
  - 본 계획서 내용을 `docs/migration.md` 파일로 저장하여 프로젝트 문서로 남깁니다.
- **Phase 1: 프로젝트 셋업 및 모델링**
  - 가상환경 및 FastAPI 프로젝트 뼈대 구성
  - SQLite 연동 및 SQLAlchemy 데이터 모델(Member, Project 등) 작성
  - Alembic을 활용하거나 `create_all()`을 통한 초기 스키마 생성
- **Phase 2: CRUD API 구현**
  - Member 및 Project의 기본 CRUD API 엔드포인트 작성
  - Pydantic 스키마를 통한 요청 유효성 검증 적용
- **Phase 3: 배분 알고리즘 이식**
  - 프로토타입의 `autoDistribute` 함수를 Python으로 변환 (`services/distribute.py`)
  - DB에서 데이터를 읽어와 알고리즘 수행 후 `Participation` 테이블에 결과 저장하는 로직 구현
- **Phase 4: 조회 및 통계 API 구현**
  - 배분된 결과(`Participation`) 및 연구원별 참여 현황 통계를 반환하는 API 구현

## 6. 검증 및 테스트 (Verification)
- `pytest`를 활용하여 주요 서비스 로직에 대한 단위 테스트 작성.
- 프로토타입에서 사용된 초기 Mock 데이터(연구원 10명, 사업 7개)를 seed 데이터로 입력하여, 기존 React 프로토타입과 동일한 배분 결과(참여율, 인건비)가 도출되는지 교차 검증.
- FastAPI 내장 Swagger UI(`/docs`)를 통한 API 수동 테스트.

## 7. 마이그레이션 및 롤백 (Migration & Rollback)
- **마이그레이션:** 백엔드 API가 안정화되면 기존 프론트엔드 프로토타입의 상태 관리(`useState`, Mock 데이터)를 `fetch` 또는 `axios`를 활용한 API 호출로 교체합니다.
- **롤백:** 백엔드 도입 중 문제가 발생할 경우, 기존 단일 파일 형태의 `salary_distribution.tsx` 로 즉시 롤백하여 서비스를 유지할 수 있습니다.
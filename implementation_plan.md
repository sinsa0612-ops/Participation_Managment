# 구현 계획서 — salary-app 풀 코드 리뷰 & 리팩토링

> 작성: Amelia (Senior Software Engineer) · 작성일 2026-06-16
> 대상: `salary-app/` (FastAPI 백엔드 + React/Vite 프론트엔드)
> 기준 헌법: `AI-INSTRUCTIONS.md`
> 성격: **본 문서는 코드 변경 전 [구조 사전 이해 보고서](AI-INSTRUCTIONS.md) 단계 산출물입니다. 승인 후 착수합니다.**

---

## 진행 현황 (2026-06-16 업데이트)

- ✅ **Phase 0** 테스트 안전망 (pytest 17개, 배분 스냅샷)
- ✅ **Phase 1** 인건비 계산 SSOT (`calc.py`, 프론트 복붙 제거)
- ✅ **Phase 2** 백엔드 견고화 (config/.env, FK, 검증, UUID, logging)
- ✅ **Phase 3** 배분 알고리즘 (F4·F5·F17 반영, 2차 패스 분해)
- ✅ **Phase 4** 프론트엔드 분해 (App.tsx 1197→317줄, 12개 모듈)
- ✅ **Phase 5** 수동 조정 + 영속성 (F12)

**전체 완료.** 검증: 백엔드 pytest 20 · ruff clean · 프론트 tsc+build 성공. 상세 이력은 `HANDOFF-sub.md` 참조.
권장 후속: 브라우저 런타임 점검, Alembic 도입, git 커밋(사용자).

---

## 0. 한 줄 요약

뼈대(레이어 분리)는 이미 꽤 잘 잡혀 있다. 문제는 **(1) 안전망(테스트)이 0개**, **(2) 돈 계산 로직이 프론트·백엔드 5곳에 복붙**, **(3) 핵심 배분 알고리즘이 한 함수에 220줄로 뭉쳐 있고 하드코딩된 "오늘 날짜"가 시한폭탄**, **(4) 반쯤 만들다 만 "고용형태별 예산" 차원이 코드 곳곳에 유령처럼 남아 혼란을 키운다**는 것이다.

---

## 1. 현재 아키텍처 (있는 그대로)

```
salary-app/
├── backend/  (FastAPI + SQLAlchemy + SQLite)
│   ├── main.py                 앱 부트스트랩 + CORS + 라우터 등록
│   ├── app/
│   │   ├── database.py         엔진/세션/Base/get_db (DAL 진입점)
│   │   ├── models/             ORM: member, project(+4개 연관테이블), participation
│   │   ├── schemas/            Pydantic: member, project, participation
│   │   ├── routers/            members, projects, participations (HTTP 경계)
│   │   └── services/
│   │       └── distribute.py   ★ 자동 배분 알고리즘 (핵심 비즈니스 로직)
│   ├── seed.py                 초기 목업 데이터 주입
│   └── tests/                  ★ 비어 있음 (테스트 0개)
└── frontend/ (React 19 + Vite + xlsx)
    └── src/
        ├── api.ts              백엔드 호출 래퍼 + 타입
        └── App.tsx             ★ 1,197줄 단일 컴포넌트 (탭 6개 전부)
```

**좋은 점 (유지할 것):**
- `models / schemas / routers / services` 4계층이 이미 분리됨 → AI-INSTRUCTIONS 2장(1모듈 1R&R, DAL 격리, Pydantic 검증)의 의도와 부합.
- DB 접근이 라우터 안에서 SQLAlchemy ORM으로만 이뤄지고 raw SQL 오염이 없음.
- 프론트 API 호출이 `api.ts` 한 곳으로 모임.

---

## 2. 핵심 진단 (심각도순)

심각도: 🔴 치명(데이터/정합성 위험) · 🟠 높음(유지보수 큰 비용) · 🟡 중간 · ⚪ 낮음

| # | 심각도 | 위치 | 문제 | 근본 원인 |
|---|--------|------|------|-----------|
| F1 | 🔴 | `services/distribute.py:14` | `TODAY = date(2026, 5, 18)` 하드코딩. "잔여 6개월 미만 사업 제외"(`_months_to_end`, line 49·138) 규칙이 고정 날짜 기준이라 시간이 지날수록 오작동. | 하드코딩 금지(AI-INSTRUCTIONS 2-1) 위반 |
| F2 | 🔴 | `backend` 전역 | **테스트 0개.** 가장 복잡·고위험인 배분 알고리즘에 검증 그물이 전혀 없음 → 리팩토링하면 무엇이 깨졌는지 알 길이 없음. | AI-INSTRUCTIONS 5장 위반 |
| F3 | 🔴 | `App.tsx:198,235,445,459` + `distribute.py:250` | 인건비/참여율 "천원 단위 내림" 계산식이 프론트 4곳 + 백엔드에 각각 복붙. 백엔드가 이미 `cost`를 내려주는데 프론트가 무시하고 월별로 재계산. 규칙 1곳만 바뀌어도 5곳을 고쳐야 하고 값이 어긋날 수 있음. | 단일 진실 공급원(SSOT) 부재 |
| F4 | 🟠 | `models/project.py:21` · `routers/projects.py:57,167` · `distribute.py:82` | "고용형태별 예산"이 반쯤 구현됨. `ProjectBudget.employ_type` 컬럼·`distribute.py`의 `{year:{employ_type:amount}}` 주석은 있으나, 실제로는 항상 `"total"`로만 저장하고 전부 합산. 유령 차원이 알고리즘을 오해하게 만듦. | 미완성 기능 잔재(누더기) |
| F5 | 🟠 | `services/distribute.py:113-334` | `auto_distribute` 단일 함수 220줄 + 중첩 클로저 3개 + 2-pass. "사업 수 제한"이 두 가지 정의로 충돌: 하드 게이트(line 210)는 전체기간 중복, 월별 루프(217-224)는 6개월 필터. 같은 개념이 두 잣대. | 월별 슬라이딩 윈도우 미구현(CLAUDE.md) |
| F6 | 🟠 | `App.tsx` 전체 | 1,197줄 God Component. 탭 6개·모달 2개·CSV·엑셀 내보내기·파생계산(`summaryData`/`monthlyData`)·CRUD 핸들러가 한 컴포넌트에. 비즈니스 계산이 뷰에 박힘. | 관심사 분리 부재 |
| F7 | 🔴 | `models/participation.py:9-10` | `project_id`·`member_id`가 FK 없는 일반 String. 사업/연구원을 지워도 고아 참여 레코드가 남아 통계·표가 깨질 수 있음. | 참조 무결성 부재 |
| F8 | 🟠 | `routers/members.py:24` 등 전역 | ID가 `str(uuid.uuid4())[:7]` (28비트)로 잘림. 수천 건이면 충돌 가능. | 약한 키 생성 |
| F9 | 🟠 | `database.py:4` · `main.py:7,17` | DB URL·포트(8001)·CORS `*`가 코드에 하드코딩. 설정 계층(Settings)·`.env` 부재. `create_all`만 있고 마이그레이션(Alembic) 없음 → 스키마 변경 시 DB 수동 삭제 필요. | AI-INSTRUCTIONS 2-1 설정 중앙화 위반 |
| F10 | 🟡 | `schemas/member.py`, `schemas/project.py` | 값 범위 검증 없음: 음수 급여, `max_rate`>100, 빈/이상 날짜 문자열 모두 통과. 프론트 input엔 min/max 있으나 백엔드 경계 미검증. | 입구 검증(AI-INSTRUCTIONS 2장) 미흡 |
| F11 | 🟡 | `routers/projects.py:68-71` · `participations.py:25-49` | N+1 쿼리. 사업마다 연관 4테이블 개별 조회, 멤버/사업 매칭은 루프 안 선형 탐색(`next(... for ...)`). 데이터 적어 당장은 OK이나 비효율. | 조회 패턴 미정리 |
| F12 | 🟡 | `routers/participations.py:79` | 재배분이 기존 참여 전체 삭제 후 재계산 → 수동 조정(미구현 #3) 결과가 매번 소실. | 수동 조정 영속성 부재 |
| F13 | 🟡 | `api.ts:76` | 에러를 `${status} ${statusText}`로만 던져 백엔드의 한국어 `detail` 메시지가 사용자에게 안 보임. | 에러 표면화 손실 |
| F14 | ⚪ | `pyproject.toml:6` | `requires-python >=3.14`인데 헌법(3장)은 Python 3.12 명시. 불일치. | 규격 드리프트 |
| F15 | ⚪ | `CLAUDE.md` / `distribute.py:4` | 문서가 "메인 앱 = docs/*.tsx 프로토타입"이라 하나 실제론 FastAPI+React로 이전 완료. 문서 최신화 필요. | 문서 드리프트 |
| F16 | ⚪ | 전역 | `print`/임시 로그 산재, `logging` 모듈 미사용(헌법 3장). `seed.py:6` `sys.path` 해킹. | 로깅/실행 규약 미준수 |

---

## 3. 리팩토링 원칙 (이 작업에서 지킬 것)

- **폭발 반경 최소화(헌법 9장):** 동작하는 동작을 바꾸지 않는다. 같은 입력 → 같은 출력(배분 결과)을 보장하며 내부 구조만 정리한다.
- **안전망 먼저:** 코드를 옮기기 **전에** 현재 동작을 고정하는 특성화 테스트(characterization test)를 깐다. (Red→Green→Refactor)
- **단순함 우선(헌법 9장 KISS):** 경계(설정·DB·검증)는 규칙대로, 그 안쪽 로직은 단순하게. 100줄로 될 걸 1,000줄로 만들지 않는다.
- **단계별 검증:** 각 Phase 끝에 스모크 테스트로 "여전히 같은 결과"를 확인하고 사용자에게 보고.

---

## 4. 단계별 실행 계획

### Phase 0 — 안전망 구축 (리팩토링의 전제, 코드 동작 변경 0)
> "벽을 허물기 전에 천장을 받칠 임시 기둥부터 세운다."

- [ ] 0-1. `pytest` 도입 + 인메모리 SQLite fixture(`sqlite:///:memory:`) 구성 (헌법 5장).
- [ ] 0-2. **특성화 테스트**: 현재 `seed.py` 데이터로 `auto_distribute`를 돌린 결과(참여 건수/각 rate/각 cost/합계)를 스냅샷으로 고정. 이후 리팩토링은 이 스냅샷을 깨지 않아야 함.
- [ ] 0-3. 라우터 해피패스 API 테스트(멤버·사업 CRUD, distribute, stats) — FastAPI `TestClient`.
- [ ] 0-4. 프론트 빌드/타입체크(`tsc -b`)가 통과하는 기준선 확인.

**산출물:** `backend/tests/` 채워짐. 이후 모든 변경의 통과 기준.

### Phase 1 — 돈 계산 단일 진실 공급원 (F3)
- [ ] 1-1. 백엔드: 천원 내림·월별 인건비·기간겹침 계산을 `services/calc.py` 한 모듈로 추출(순수 함수). `distribute.py`와 라우터가 이걸 공유.
- [ ] 1-2. 백엔드: 참여 결과에 **월별 분해**(월별 rate·cost) 또는 충분한 필드를 응답에 포함시켜, 프론트가 재계산할 필요를 없앰.
- [ ] 1-3. 프론트: `App.tsx`의 4곳 재계산 제거 → 백엔드 값 소비. 불가피한 표시 계산은 `src/lib/calc.ts` 한 곳으로.
- [ ] 검증: 화면 숫자가 Phase 0 스냅샷과 동일.

### Phase 2 — 백엔드 견고화 (F1·F7·F8·F9·F10)
- [ ] 2-1. `app/config.py`에 `pydantic-settings` 기반 `Settings`(DB URL·포트·CORS·`TODAY` 기준일·매직넘버) 도입, `.env` + `.gitignore`. → F1·F9 동시 해결. `TODAY`는 기본 실제 오늘, 테스트에서만 주입.
- [ ] 2-2. `Participation`에 FK(+`ondelete`) 부여, 또는 삭제 시 연쇄 정리. 고아 레코드 차단(F7).
- [ ] 2-3. ID 생성 정책 통일: 전체 UUID 또는 정수 PK(F8).
- [ ] 2-4. Pydantic 필드 검증 추가: 급여≥0, 0≤rate≤100, 날짜 형식, max_projects≥1(F10).
- [ ] 2-5. Alembic 도입(또는 최소한 초기 마이그레이션) — 스키마 변경을 추적 가능하게(F9).
- [ ] 2-6. `logging` 표준화, `print`/`sys.path` 해킹 제거(F16).

### Phase 3 — 배분 알고리즘 분해 (F5, F4)
> 가장 신중한 단계. Phase 0 스냅샷이 방패.

- [ ] 3-1. `distribute.py`를 역할별로 분리: 날짜/기간 유틸 → `calc.py`(Phase 1과 통합), 제약 검사(참여율·사업수·재직·강제월) → `constraints.py`, 본체 → 1·2패스 함수로.
- [ ] 3-2. 중첩 클로저 3개를 명시적 상태 객체/함수로 승격, 매직넘버를 설정값(Phase 2-1)으로.
- [ ] 3-3. **F4 결정 반영**: "고용형태별 예산"이 진짜 요구사항이면 모델·알고리즘·UI에 제대로 구현, 아니면 `employ_type` 유령 차원 제거.
- [ ] 3-4. **F5 결정 반영**: "사업 수 제한"의 단일 정의 확정(월별 동시 기준 권장) → CLAUDE.md의 "월별 슬라이딩 윈도우" 미구현 항목 해결.
- [ ] 검증: 스냅샷 동일(또는 의도된 차이를 사용자 승인 후 새 스냅샷으로 갱신).

### Phase 4 — 프론트엔드 컴포넌트 분해 (F6)
- [ ] 4-1. 탭별 컴포넌트 분리: `MembersTab`, `ProjectsTab`, `SummaryTab`, `MonthlyTab`, `DistributionTab`, `StatsTab`.
- [ ] 4-2. 공용 추출: `Modal`/`SaveCancel`(이미 있음) + `MemberForm`, `ProjectForm`, 스타일 토큰을 `ui/` 또는 CSS 모듈로.
- [ ] 4-3. 데이터 로드/상태를 커스텀 훅(`useSalaryData`)으로, 파생계산을 `lib/`로.
- [ ] 4-4. 에러 표면화(F13): `api.ts`가 백엔드 `detail`을 파싱해 전달.
- [ ] 검증: 6개 탭 동작·엑셀/CSV 기능 회귀 없음.

### Phase 5 — 미구현 필수 기능 (CLAUDE.md 기준, 별도 승인 후)
- [ ] 5-1. 자동 배분 결과 **수동 조정 UI + 영속성**(F12) — 재배분이 수동 편집을 덮지 않도록.
- [ ] 5-2. (3-4와 연계) 월별 슬라이딩 참여율 검증 최종화.
- [ ] 5-3. 연구원·과제별 개별 참여 기간 설정 정교화(현 `member_months` 확장).

---

## 5. 착수 전 결정 필요 사항 (질문 우선 — 헌법 9장)

1. **F4 고용형태별 예산:** 국비/시비/민간 또는 정규/전문/위촉 형태별로 예산을 따로 매칭해야 하는 실제 요구가 있나요, 아니면 연도별 총액만으로 충분한가요? (유령 차원 제거 vs 정식 구현이 갈림)
2. **F5 사업 수 제한 정의:** "최대 참여 사업 수"는 **특정 월에 동시 참여** 기준인가요, **전체 기간 누적 고유 사업** 기준인가요?
3. **F14 Python 버전:** 헌법은 3.12인데 `pyproject.toml`은 3.14입니다. 어디에 맞출까요?
4. **우선순위:** 위 Phase 중 어디부터 착수할까요? (권장: Phase 0 → 1 → 2 순. 안전망 없이 알고리즘부터 건드리는 것은 비권장)

---

## 6. 리스크 & 폭발 반경

- 가장 위험한 변경은 **Phase 3(알고리즘)**. Phase 0 특성화 테스트가 없으면 착수 불가.
- DB 스키마 변경(F7·F8)은 기존 `salary.db` 데이터 마이그레이션이 필요 — 사용자 데이터 백업 후 진행.
- 프론트 분해(Phase 4)는 동작 변경이 아니므로 위험 낮음, 단 회귀 확인 필요.
- 모든 Phase는 독립적으로 머지 가능하도록 작게 쪼개 진행 — 한 번에 큰 PR 지양.
```
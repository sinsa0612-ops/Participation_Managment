"""ID 생성 단일 출처. 충돌 위험이 있던 잘린 UUID(`uuid4()[:7]`) 대신 전체 UUID를 쓴다 (F8)."""

from __future__ import annotations

import uuid


def new_id() -> str:
    """32자리 16진수 UUID 문자열."""
    return uuid.uuid4().hex

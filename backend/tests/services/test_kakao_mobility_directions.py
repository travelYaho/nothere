"""Kakao Mobility 자동차 길찾기 API 단독 연결 검증 스크립트.

서비스/DB 로직과 분리된 단순 호출 테스트이다.
실행: python tests/services/test_kakao_mobility_directions.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
DIRECTIONS_URL = "https://apis-navi.kakaomobility.com/v1/directions"

# 경복궁 → 서울역 (경도, 위도)
ORIGIN_LNG, ORIGIN_LAT = 126.9770, 37.5796
DEST_LNG, DEST_LAT = 126.9706, 37.5547


def main() -> int:
    load_dotenv(BACKEND_DIR / ".env")
    api_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    if not api_key:
        print("KAKAO_REST_API_KEY 환경변수가 없습니다. backend/.env 를 확인하세요.")
        return 1

    origin = f"{ORIGIN_LNG},{ORIGIN_LAT}"
    destination = f"{DEST_LNG},{DEST_LAT}"
    headers = {
        "Authorization": f"KakaoAK {api_key}",
        "Content-Type": "application/json",
    }
    params = {"origin": origin, "destination": destination}

    print(f"GET {DIRECTIONS_URL}")
    print(f"origin={origin} (lng,lat)")
    print(f"destination={destination} (lng,lat)")
    print()

    try:
        response = httpx.get(DIRECTIONS_URL, headers=headers, params=params, timeout=30.0)
    except httpx.RequestError as exc:
        print(f"요청 실패: {exc}")
        return 1

    if response.status_code != 200:
        print(f"status code: {response.status_code}")
        print(f"response body: {response.text}")
        return 1

    try:
        data = response.json()
    except json.JSONDecodeError:
        print(f"status code: {response.status_code}")
        print(f"response body: {response.text}")
        return 1

    routes = data.get("routes") or []
    if not routes:
        print(f"status code: {response.status_code}")
        print(f"response body: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return 1

    route = routes[0]
    result_code = route.get("result_code")
    if result_code != 0:
        print(f"status code: {response.status_code}")
        print(f"result_code: {result_code}")
        print(f"result_msg: {route.get('result_msg')}")
        print(f"response body: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return 1

    summary = route.get("summary") or {}
    distance = summary.get("distance")
    duration = summary.get("duration")
    if distance is None or duration is None:
        print(f"status code: {response.status_code}")
        print(f"response body: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return 1

    duration_minutes = duration / 60
    print(f"distance: {distance}m")
    print(f"duration: {duration}sec")
    print(f"duration_minutes: 약 {duration_minutes:.1f}분")
    return 0


if __name__ == "__main__":
    sys.exit(main())

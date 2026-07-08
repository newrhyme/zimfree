"""Anthropic Messages API tool-use loop for the natural-language assistant."""
from __future__ import annotations

import json
import os

from .. import db
from . import congestion as congestion_svc
from . import luggage as luggage_svc
from . import route as route_svc
from . import scenario as scenario_svc
from . import stations as stations_svc

ANTHROPIC_MODEL = "claude-sonnet-4-6"
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MAX_TOKENS = 1024
MAX_LOOPS = 5


class AssistantDisabled(Exception):
    pass


def provider() -> str | None:
    """Prefer OpenAI if its key is set, else Anthropic, else disabled."""
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def is_enabled() -> bool:
    return provider() is not None


def active_model() -> str:
    p = provider()
    if p == "openai":
        return OPENAI_MODEL
    if p == "anthropic":
        return ANTHROPIC_MODEL
    return "—"


def _resolve(name_or_code) -> int | None:
    if name_or_code is None:
        return None
    s = str(name_or_code)
    if s.isdigit():
        row = db.query_one("SELECT station_code FROM stations WHERE station_code=?", (int(s),))
        return row["station_code"] if row else None
    row = db.query_one("SELECT station_code FROM stations WHERE std_name=?", (s,))
    if row:
        return row["station_code"]
    row = db.query_one(
        "SELECT station_code FROM stations WHERE std_name LIKE ? ORDER BY station_code LIMIT 1",
        (f"%{s}%",),
    )
    return row["station_code"] if row else None


SYSTEM = (
    "당신은 부산 지하철 여행 어시스턴트 '짐프리'입니다. 캐리어·유모차 등 짐을 든 "
    "관광객에게 탑승칸 추천, 혼잡 회피, 엘리베이터 고장 대체경로, 짐 처리(휴대/보관함/짐배송) "
    "결정을 돕습니다. 반드시 제공된 도구를 호출해 근거 데이터를 얻고, 도구 결과에 없는 "
    "역·수치·시설을 지어내지 마세요. 커버리지 밖이면 '정보 없음'이라고 정직하게 답하세요. "
    "답변은 한국어로 간결하게, 핵심 카드(탑승 위치·경고·혼잡·짐 결정)를 우선 제시하세요."
)

TOOLS = [
    {
        "name": "get_route_plan",
        "description": "출발/도착역과 짐 정보로 경로·탑승칸·혼잡·짐 결정을 종합 계획한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "출발역 표준역명 또는 역번호"},
                "dest": {"type": "string", "description": "도착역 표준역명 또는 역번호"},
                "size": {"type": "string", "enum": ["S", "M", "L", "XL"]},
                "count": {"type": "integer"},
                "stroller": {"type": "boolean"},
                "battery_pct": {"type": "integer"},
                "depart_at": {"type": "string", "description": "ISO 예: 2026-07-08T14:00"},
            },
            "required": ["origin", "dest"],
        },
    },
    {
        "name": "get_congestion",
        "description": "특정 역·날짜·시각·승하차의 혼잡 레벨과 덜 붐비는 대안 시간을 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "station": {"type": "string"},
                "date": {"type": "string"},
                "hour": {"type": "integer"},
                "io_type": {"type": "string", "enum": ["board", "alight"]},
            },
            "required": ["station", "date", "hour"],
        },
    },
    {
        "name": "get_boarding_position",
        "description": "도착역에서 엘리베이터에 가까운 추천 탑승칸(문 위치)과 경고를 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {"station": {"type": "string"}},
            "required": ["station"],
        },
    },
    {
        "name": "get_station_facilities",
        "description": "역의 보관함/ATM/충전기/키오스크/엘리베이터/에스컬레이터 유무를 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {"station": {"type": "string"}},
            "required": ["station"],
        },
    },
    {
        "name": "decide_luggage",
        "description": "휴대/보관함/짐배송 3옵션을 데이터 근거로 비교하고 추천한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {"type": "string"},
                "dest": {"type": "string"},
                "size": {"type": "string", "enum": ["S", "M", "L", "XL"]},
                "count": {"type": "integer"},
                "stroller": {"type": "boolean"},
            },
            "required": ["origin", "dest"],
        },
    },
    {
        "name": "simulate_elevator_outage",
        "description": "특정 역 엘리베이터 고장 시 대체경로와 복잡도 등급을 반환한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "station": {"type": "string"},
                "elevator_id": {"type": "string"},
            },
            "required": ["station"],
        },
    },
]


def _run_tool(name: str, args: dict) -> dict:
    if name == "get_route_plan":
        o, d = _resolve(args.get("origin")), _resolve(args.get("dest"))
        if o is None or d is None:
            return {"error": "역을 찾을 수 없음"}
        luggage = {"size": args.get("size", "M"), "count": args.get("count", 1),
                   "stroller": args.get("stroller", False)}
        return route_svc.plan(o, d, luggage, args.get("battery_pct"), args.get("depart_at"))
    if name == "get_congestion":
        s = _resolve(args.get("station"))
        if s is None:
            return {"error": "역을 찾을 수 없음"}
        return congestion_svc.congestion(
            s, args["date"], int(args["hour"]), args.get("io_type", "board"))
    if name == "get_boarding_position":
        s = _resolve(args.get("station"))
        return route_svc.get_boarding(s) if s else {"error": "역을 찾을 수 없음"}
    if name == "get_station_facilities":
        s = _resolve(args.get("station"))
        return stations_svc.get_facilities(s) if s else {"error": "역을 찾을 수 없음"}
    if name == "decide_luggage":
        o, d = _resolve(args.get("origin")), _resolve(args.get("dest"))
        if o is None or d is None:
            return {"error": "역을 찾을 수 없음"}
        luggage = {"size": args.get("size", "M"), "count": args.get("count", 1),
                   "stroller": args.get("stroller", False)}
        return luggage_svc.decide(o, d, luggage)
    if name == "simulate_elevator_outage":
        s = _resolve(args.get("station"))
        if s is None:
            return {"error": "역을 찾을 수 없음"}
        return scenario_svc.elevator_outage(s, args.get("elevator_id"))
    return {"error": f"unknown tool {name}"}


# OpenAI function-calling tool schema (converted from the shared TOOLS list)
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        },
    }
    for t in TOOLS
]


def chat(user_message: str) -> dict:
    p = provider()
    if p is None:
        raise AssistantDisabled()
    if p == "openai":
        return _chat_openai(user_message)
    return _chat_anthropic(user_message)


def _chat_anthropic(user_message: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": user_message}]
    tool_trace = []
    for _ in range(MAX_LOOPS):
        resp = client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=MAX_TOKENS, system=SYSTEM,
            tools=TOOLS, messages=messages,
        )
        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if b.type == "text")
            return {"reply": text, "tools_used": tool_trace, "provider": "anthropic"}
        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                result = _run_tool(block.name, block.input or {})
                tool_trace.append(block.name)
                tool_results.append({
                    "type": "tool_result", "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
        messages.append({"role": "user", "content": tool_results})
    return {"reply": "요청을 처리하지 못했습니다. 다시 시도해 주세요.",
            "tools_used": tool_trace, "provider": "anthropic"}


def _chat_openai(user_message: str) -> dict:
    from openai import OpenAI

    client = OpenAI()
    messages: list = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_message},
    ]
    tool_trace = []
    for _ in range(MAX_LOOPS):
        resp = client.chat.completions.create(
            model=OPENAI_MODEL, max_tokens=MAX_TOKENS,
            tools=OPENAI_TOOLS, messages=messages,
        )
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return {"reply": msg.content or "", "tools_used": tool_trace,
                    "provider": "openai"}
        messages.append(msg.model_dump(exclude_none=True))
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = _run_tool(tc.function.name, args)
            tool_trace.append(tc.function.name)
            messages.append({
                "role": "tool", "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })
    return {"reply": "요청을 처리하지 못했습니다. 다시 시도해 주세요.",
            "tools_used": tool_trace, "provider": "openai"}

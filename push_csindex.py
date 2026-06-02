#!/usr/bin/env python3
"""Hourly push of CS skin market dashboard from csqaq.com to a Feishu group."""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

CSQAQ_URL = "https://api.csqaq.com/api/v1/current_data"
BEIJING = timezone(timedelta(hours=8))
SUCCESS_CODES = {0, 200}

# 飞书侧瞬时错误:重试大概率可成功(11232 限流 / 19006 内部错误)
TRANSIENT_FEISHU_CODES = {11232, 19006}
RETRY_DELAY = 300  # 失败后等待秒数
MAX_RETRIES = 3    # 额外重试次数(共尝试 1 + MAX_RETRIES 次)

GREEDY_EMOJI = {
    "extreme_fear": "😱",
    "fear": "😨",
    "low": "😨",
    "medium": "😐",
    "neutral": "😐",
    "greed": "🤑",
    "high": "🤑",
    "extreme_greed": "🤯",
}


def load_env() -> dict[str, str]:
    for candidate in (Path.home() / ".csindex.env", Path(__file__).parent / ".env"):
        if candidate.is_file():
            env = {}
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
            return env
    raise SystemExit("missing env file: ~/.csindex.env or ./.env")


def fetch_market(token: str) -> dict:
    resp = requests.get(
        CSQAQ_URL,
        headers={"ApiToken": token},
        params={"type": "init"},
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") not in SUCCESS_CODES:
        raise RuntimeError(f"csqaq error: {payload}")
    return payload["data"]


def pct(v: float) -> str:
    return f"{v:+.2f}%"


def fmt_int(v) -> str:
    if v is None:
        return "-"
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return str(v)


def build_card(data: dict) -> dict:
    now = datetime.now(BEIJING).strftime("%m-%d %H:%M")

    sub_index = data.get("sub_index_data") or []
    chg_type = data.get("chg_type_data") or []
    online = data.get("online_number") or {}
    greedy_status = data.get("greedy_status") or {}
    greedy = data.get("greedy") or []

    if not sub_index:
        raise RuntimeError("no sub_index_data in response")

    main = sub_index[0]
    main_name = main.get("name", "饰品指数")
    main_value = float(main.get("market_index") or 0)
    main_chg = float(main.get("chg_rate") or 0)
    main_high = float(main.get("high") or 0)
    main_low = float(main.get("low") or 0)

    greedy_value = float(greedy[-1][1]) if greedy and isinstance(greedy[-1], list) and len(greedy[-1]) >= 2 else None
    greedy_label = greedy_status.get("label", "-")
    greedy_emoji = GREEDY_EMOJI.get(greedy_status.get("level", ""), "📊")

    online_now = online.get("current_number")
    online_rate = float(online.get("rate") or 0)
    online_peak_today = online.get("today_peak")
    online_peak_month = online.get("month_peak")

    template = "red" if main_chg >= 0 else "green"

    elements: list[dict] = []

    # ──── 顶部:四宫格 ────
    elements.append({
        "tag": "div",
        "fields": [
            {
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**📈 {main_name}**\n{main_value:,.2f}  {pct(main_chg)}\n<font color='grey'>日内 {main_low:.1f} - {main_high:.1f}</font>",
                },
            },
            {
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**{greedy_emoji} 恐贪指数**\n{greedy_value:.1f}  {greedy_label}" if greedy_value else f"**{greedy_emoji} 恐贪指数**\n{greedy_label}",
                },
            },
            {
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**👥 Steam 在线**\n{fmt_int(online_now)}  {pct(online_rate)}",
                },
            },
            {
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**🏔️ 今日峰值**\n{fmt_int(online_peak_today)}\n<font color='grey'>月峰 {fmt_int(online_peak_month)}</font>",
                },
            },
        ],
    })
    elements.append({"tag": "hr"})

    # ──── 武器品类 · 全量(按今日涨跌排序) ────
    if chg_type:
        sorted_types = sorted(
            (x for x in chg_type if x.get("name") and x.get("price_diff_1") is not None),
            key=lambda x: float(x.get("price_diff_1") or 0),
            reverse=True,
        )

        def fmt_type(x: dict) -> str:
            name = str(x.get("name", "?"))
            d1 = float(x.get("price_diff_1") or 0)
            d7 = float(x.get("price_diff_7") or 0)
            color = "red" if d1 > 0 else ("green" if d1 < 0 else "grey")
            return (
                f"`{name:<10}` <font color='{color}'>日 {pct(d1)}</font>  "
                f"<font color='grey'>周 {pct(d7)}</font>"
            )

        # 拆成两列以减少卡片纵向高度
        half = (len(sorted_types) + 1) // 2
        left = "\n".join(fmt_type(x) for x in sorted_types[:half])
        right = "\n".join(fmt_type(x) for x in sorted_types[half:])

        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**🔫 武器品类涨跌**(按今日涨跌排序)"},
        })
        elements.append({
            "tag": "div",
            "fields": [
                {"is_short": True, "text": {"tag": "lark_md", "content": left}},
                {"is_short": True, "text": {"tag": "lark_md", "content": right}},
            ],
        })

    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": f"数据来源 csqaq.com · {now} (UTC+8)"}],
    })

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"📊 CS 饰品大盘 · {now}"},
            "template": template,
        },
        "elements": elements,
    }


def send_feishu(webhook: str, card: dict) -> None:
    payload = {"msg_type": "interactive", "card": card}
    for attempt in range(MAX_RETRIES + 1):
        resp = requests.post(webhook, json=payload, timeout=10)
        resp.raise_for_status()
        body = resp.json()
        code = body.get("code", body.get("StatusCode", -1))
        if code == 0:
            print(f"[{datetime.now(BEIJING).isoformat()}] sent ok")
            return
        # 非瞬时错误(如 webhook 失效),直接失败,重试无意义
        if code not in TRANSIENT_FEISHU_CODES or attempt == MAX_RETRIES:
            raise RuntimeError(f"feishu error: {body}")
        print(
            f"[{datetime.now(BEIJING).isoformat()}] feishu transient error {body}; "
            f"retry {attempt + 1}/{MAX_RETRIES} in {RETRY_DELAY}s",
            file=sys.stderr,
        )
        time.sleep(RETRY_DELAY)


def main() -> int:
    env = load_env()
    token = env.get("CSQAQ_API_TOKEN")
    webhook = env.get("FEISHU_WEBHOOK")
    if not token or not webhook:
        print("missing CSQAQ_API_TOKEN or FEISHU_WEBHOOK", file=sys.stderr)
        return 2

    data = fetch_market(token)
    card = build_card(data)
    send_feishu(webhook, card)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)

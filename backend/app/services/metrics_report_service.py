"""
End-of-day API metrics report — queries Prometheus and posts to Slack.

Scheduled via APScheduler in app/main.py (fires at METRICS_REPORT_HOUR UTC).
"""

import logging
import os
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.prisma_client import db

logger = logging.getLogger("app")

PROM = settings.PROMETHEUS_URL


async def _query(expr: str) -> str | None:
    """Run an instant PromQL query and return the first result value, or None."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{PROM}/api/v1/query",
                params={"query": expr},
            )
        data = r.json()
        results = data.get("data", {}).get("result", [])
        if results:
            return results[0]["value"][1]
    except Exception as exc:
        logger.warning("Prometheus query failed (%s): %s", expr, exc)
    return None


async def _query_vector(expr: str) -> list[dict]:
    """Run an instant PromQL query and return all result label+value pairs."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{PROM}/api/v1/query",
                params={"query": expr},
            )
        return r.json().get("data", {}).get("result", [])
    except Exception as exc:
        logger.warning("Prometheus vector query failed (%s): %s", expr, exc)
    return []


def _fmt(value: str | None, unit: str = "", decimals: int = 0) -> str:
    if value is None:
        return "n/a"
    try:
        f = float(value)
        if decimals:
            return f"{f:.{decimals}f}{unit}"
        return f"{int(f)}{unit}"
    except (ValueError, TypeError):
        return "n/a"


async def _get_server_info() -> dict:
    """Fetch public IP and geolocation from ip-api.com."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://ip-api.com/json")
        d = r.json()
        if d.get("status") == "success":
            return {
                "ip": d.get("query", "unknown"),
                "city": d.get("city", ""),
                "region": d.get("regionName", ""),
                "country": d.get("country", ""),
                "isp": d.get("isp", ""),
            }
    except Exception as exc:
        logger.warning("Could not fetch server location: %s", exc)
    return {"ip": "unknown", "city": "", "region": "", "country": "", "isp": ""}


async def send_eod_report() -> None:
    """Fetch 24 h metrics from Prometheus and post an EOD summary to Slack."""
    if not settings.SLACK_BOT_TOKEN:
        logger.info("SLACK_BOT_TOKEN not set — skipping EOD metrics report")
        return

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%A, %d %b %Y")
    version = os.getenv("APP_VERSION", "dev")
    server = await _get_server_info()
    location_parts = [p for p in [server["city"], server["region"], server["country"]] if p]
    location_str = ", ".join(location_parts) or "unknown"

    # ── Scalar metrics ────────────────────────────────────────────────────────
    total_req   = await _query('sum(increase(http_requests_total{job="controlplane_api"}[24h]))')
    req_4xx     = await _query('sum(increase(http_requests_total{job="controlplane_api",status_code=~"4.."}[24h]))')
    req_5xx     = await _query('sum(increase(http_requests_total{job="controlplane_api",status_code=~"5.."}[24h]))')
    p50_lat     = await _query('histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{job="controlplane_api"}[24h])) by (le))')
    p95_lat     = await _query('histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="controlplane_api"}[24h])) by (le))')
    p99_lat     = await _query('histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job="controlplane_api"}[24h])) by (le))')
    active_users = await _query('count(sum by (user_id) (increase(controlplane_user_requests_total[24h])) > 0)')

    # ── Success / error rate ──────────────────────────────────────────────────
    success_rate_raw = await _query(
        'sum(increase(http_requests_total{job="controlplane_api",status_code=~"2.."}[24h])) / '
        'sum(increase(http_requests_total{job="controlplane_api"}[24h]))'
    )
    success_pct = _fmt(
        str(float(success_rate_raw) * 100) if success_rate_raw else None,
        unit="%", decimals=1,
    )

    # ── Top 5 endpoints ───────────────────────────────────────────────────────
    top_endpoints = await _query_vector(
        'topk(5, sum(increase(http_requests_total{job="controlplane_api"}[24h])) by (handler))'
    )

    # ── Top 5 users ───────────────────────────────────────────────────────────
    top_users = await _query_vector(
        'topk(5, sum(increase(controlplane_user_requests_total[24h])) by (user_id))'
    )

    # ── Determine overall health emoji ───────────────────────────────────────
    try:
        error_total = (float(req_4xx or 0) + float(req_5xx or 0))
        total       = float(total_req or 1)
        error_ratio = error_total / total if total else 0
        health_emoji = "🟢" if error_ratio < 0.01 else ("🟡" if error_ratio < 0.05 else "🔴")
    except (ValueError, TypeError):
        health_emoji = "⚪"

    # ── Build top-endpoint text ───────────────────────────────────────────────
    if top_endpoints:
        ep_lines = "\n".join(
            f"  • `{r['metric'].get('handler', '?')}` — {_fmt(r['value'][1])} req"
            for r in top_endpoints
        )
    else:
        ep_lines = "  No data yet"

    if top_users:
        user_ids = [r["metric"].get("user_id", "") for r in top_users if r["metric"].get("user_id")]
        email_map: dict[str, str] = {}
        try:
            users = await db.user.find_many(where={"id": {"in": user_ids}}, take=len(user_ids))
            email_map = {u.id: u.email for u in users}
        except Exception as exc:
            logger.warning("Could not resolve user emails: %s", exc)
        user_lines = "\n".join(
            f"  • `{email_map.get(r['metric'].get('user_id', ''), r['metric'].get('user_id', '?'))}` — {_fmt(r['value'][1])} req"
            for r in top_users
        )
    else:
        user_lines = "  No data yet"

    # ── Slack blocks ──────────────────────────────────────────────────────────
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📊 Daily API Report — {date_str}",
                "emoji": True,
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*{health_emoji} Overall Health*\n{success_pct} success rate"},
                {"type": "mrkdwn", "text": f"*📨 Total Requests*\n{_fmt(total_req)}"},
                {"type": "mrkdwn", "text": f"*⚠️ 4xx Errors*\n{_fmt(req_4xx)}"},
                {"type": "mrkdwn", "text": f"*🔥 5xx Errors*\n{_fmt(req_5xx)}"},
                {"type": "mrkdwn", "text": f"*👤 Active Users*\n{_fmt(active_users)}"},
                {"type": "mrkdwn", "text": f"*⚡ Latency (p50 / p95 / p99)*\n{_fmt(p50_lat, 'ms', 0) if p50_lat else 'n/a'} / {_fmt(p95_lat, 'ms', 0) if p95_lat else 'n/a'} / {_fmt(p99_lat, 'ms', 0) if p99_lat else 'n/a'}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*🔝 Top Endpoints (24h)*\n{ep_lines}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*👥 Top Users (24h)*\n{user_lines}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*🖥️ Server IP*\n`{server['ip']}`"},
                {"type": "mrkdwn", "text": f"*📍 Location*\n{location_str}"},
                {"type": "mrkdwn", "text": f"*🏢 ISP*\n{server['isp'] or 'unknown'}"},
                {"type": "mrkdwn", "text": f"*🔖 Version*\n`{version}`"},
            ],
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"ControlPlane API · {now.strftime('%H:%M UTC')} · <{settings.PROMETHEUS_URL}|Prometheus>"}
            ],
        },
    ]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "channel": settings.SLACK_METRICS_CHANNEL or settings.SLACK_SUPPORT_CHANNEL,
                    "text": f"📊 Daily API Report — {date_str} | {_fmt(total_req)} requests | {success_pct} success",
                    "blocks": blocks,
                },
            )
        data = res.json()
        if data.get("ok"):
            logger.info("EOD metrics report sent to Slack")
        else:
            logger.error("Slack EOD report failed: %s", data.get("error"))
    except Exception as exc:
        logger.error("Failed to send EOD metrics report: %s", exc)

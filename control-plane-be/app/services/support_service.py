"""Support service — bug reports and feature requests posted to Slack."""
import httpx
from app.core.utils import ev
from app.core.exceptions import unprocessable
from app.config import settings

SEVERITY_EMOJI = {
    "low":      "🟢",
    "medium":   "🟡",
    "high":     "🟠",
    "critical": "🔴",
}

PRIORITY_EMOJI = {
    "low":    "🔵",
    "medium": "🟡",
    "high":   "🔴",
}


def _bug_blocks(title: str, description: str, severity: str,
                steps: str | None, expected: str | None,
                actual: str | None, reporter_name: str,
                reporter_email: str) -> list:
    sev_emoji = SEVERITY_EMOJI.get(severity, "⚪")
    fields = [
        {"type": "mrkdwn", "text": f"*Severity*\n{sev_emoji} {severity.capitalize()}"},
        {"type": "mrkdwn", "text": f"*Reporter*\n{reporter_name}"},
        {"type": "mrkdwn", "text": f"*Email*\n{reporter_email}"},
    ]

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🐛 Bug Report: {title}", "emoji": True},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Description*\n{description}"},
        },
        {"type": "section", "fields": fields},
    ]

    if steps:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Steps to Reproduce*\n{steps}"},
        })
    if expected:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Expected Behavior*\n{expected}"},
        })
    if actual:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Actual Behavior*\n{actual}"},
        })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Submitted via Control Plane · {reporter_email}"}
        ],
    })
    return blocks


def _feature_blocks(title: str, description: str, priority: str,
                    use_case: str | None, reporter_name: str,
                    reporter_email: str) -> list:
    pri_emoji = PRIORITY_EMOJI.get(priority, "⚪")
    fields = [
        {"type": "mrkdwn", "text": f"*Priority*\n{pri_emoji} {priority.capitalize()}"},
        {"type": "mrkdwn", "text": f"*Requested by*\n{reporter_name}"},
        {"type": "mrkdwn", "text": f"*Email*\n{reporter_email}"},
    ]

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"💡 Feature Request: {title}", "emoji": True},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Description*\n{description}"},
        },
        {"type": "section", "fields": fields},
    ]

    if use_case:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Use Case*\n{use_case}"},
        })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Submitted via Control Plane · {reporter_email}"}
        ],
    })
    return blocks


async def _post_to_slack(blocks: list, fallback_text: str) -> None:
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "channel": settings.SLACK_SUPPORT_CHANNEL,
                "text": fallback_text,
                "blocks": blocks,
            },
        )
    data = res.json()
    if not data.get("ok"):
        raise unprocessable(f"Slack error: {data.get('error', 'unknown')}")


async def report_bug(
    title: str, description: str, severity: str,
    steps: str | None, expected: str | None, actual: str | None,
    reporter_name: str, reporter_email: str,
) -> None:
    blocks = _bug_blocks(title, description, severity, steps, expected, actual,
                         reporter_name, reporter_email)
    await _post_to_slack(blocks, fallback_text=f"🐛 Bug Report: {title} [{severity}] from {reporter_name}")


async def request_feature(
    title: str, description: str, priority: str,
    use_case: str | None,
    reporter_name: str, reporter_email: str,
) -> None:
    blocks = _feature_blocks(title, description, priority, use_case,
                              reporter_name, reporter_email)
    await _post_to_slack(blocks, fallback_text=f"💡 Feature Request: {title} [{priority}] from {reporter_name}")
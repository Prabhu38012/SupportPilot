"""Slack front-end (Socket Mode). Run: python slack_bot.py
Needs SLACK_BOT_TOKEN (xoxb-...) and SLACK_APP_TOKEN (xapp-...) in .env.
Scopes: app_mentions:read, chat:write, im:history, im:read; subscribe to app_mention and message.im."""
import os
import re
from typing import Callable, Optional

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.agent.core import SupportAgent
from app.main import build_agent
from app.schemas import ChatRequest

load_dotenv()

_agent: Optional[SupportAgent] = None


def get_agent() -> SupportAgent:
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def answer_message(text: str, user: str, say_fn: Callable, thread_ts: str, agent: Optional[SupportAgent] = None):
    clean_text = re.sub(r"<@[A-Z0-9]+>", "", text or "").strip()
    if not clean_text:
        return
    ag = agent or get_agent()
    res = ag.handle(ChatRequest(message=clean_text, user_id=user or "slack"))
    badge = "" if res.action == "AUTO_ANSWER" else "\n_(escalated to a human)_"
    say_fn(text=res.reply + badge, thread_ts=thread_ts)


def create_slack_app(token: Optional[str] = None) -> App:
    bot_token = token or os.getenv("SLACK_BOT_TOKEN", "xoxb-placeholder")
    app = App(token=bot_token)

    @app.event("app_mention")
    def on_mention(event, say):
        answer_message(
            event.get("text", ""),
            event.get("user", "slack"),
            say,
            event.get("thread_ts") or event.get("ts"),
        )

    @app.event("message")
    def on_dm(event, say):
        if event.get("channel_type") == "im" and not event.get("bot_id"):
            answer_message(
                event.get("text", ""),
                event.get("user", "slack"),
                say,
                event.get("thread_ts") or event.get("ts"),
            )

    return app


if __name__ == "__main__":
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not bot_token or not app_token:
        print("Error: SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in .env to run slack_bot.py")
        raise SystemExit(1)
    slack_app = create_slack_app(bot_token)
    SocketModeHandler(slack_app, app_token).start()

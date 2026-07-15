"""Adaptive Card builders for the Foundry greeting bot (schema 1.5).

Provides two cards:
  - welcome_card()       -- shown when a user first joins the conversation
  - agent_reply_card()   -- wraps the agent's free-text response

Modelled after the pattern in the workshop-concierge-adk sample.
"""
from __future__ import annotations

SCHEMA = "http://adaptivecards.io/schemas/adaptive-card.json"
VERSION = "1.5"


def _card(body: list, actions: list | None = None) -> dict:
    c: dict = {
        "type": "AdaptiveCard",
        "$schema": SCHEMA,
        "version": VERSION,
        "body": body,
    }
    if actions:
        c["actions"] = actions
    return c


def welcome_card() -> dict:
    """Initial card shown when the bot is added to a conversation."""
    return _card([
        {
            "type": "TextBlock",
            "text": "Foundry Greeting Bot",
            "weight": "Bolder",
            "size": "Large",
        },
        {
            "type": "TextBlock",
            "text": "Hello! Ask me anything and I'll answer via Azure AI Foundry.",
            "wrap": True,
        },
    ])


def agent_reply_card(text: str, suggestions: list[str] | None = None) -> dict:
    """Wrap the agent's free-text (markdown) reply in an Adaptive Card.

    Teams renders standard markdown inside a TextBlock when ``markdown``
    is ``true`` — bold, italic, bullet lists, and links all work.

    Optional ``suggestions`` renders quick-reply buttons below the text.
    Clicking one sends that string back to the bot as a plain message.
    """
    actions = [
        {
            "type": "Action.Submit",
            "title": s,
            "data": {"text": s},   # activity.value["text"] in on_message_activity
        }
        for s in (suggestions or [])
    ]
    return _card(
        body=[
            {
                "type": "TextBlock",
                "text": text,
                "wrap": True,
                "markdown": True,
            },
        ],
        actions=actions or None,
    )


def link_card(text: str, label: str, url: str) -> dict:
    """Reply card with a single URL button — e.g. 'Open in portal'."""
    return _card(
        body=[
            {
                "type": "TextBlock",
                "text": text,
                "wrap": True,
                "markdown": True,
            },
        ],
        actions=[
            {
                "type": "Action.OpenUrl",
                "title": label,
                "url": url,
            }
        ],
    )

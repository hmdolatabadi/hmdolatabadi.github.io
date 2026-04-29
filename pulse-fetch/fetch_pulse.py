"""Fetch the latest tweets from a user's X timeline and write them to posts.json.

Run via:
    X_BEARER_TOKEN=... python fetch_pulse.py

In CI, this is invoked by .github/workflows/pulse-update.yml on a schedule.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

USERNAME = os.environ.get("X_USERNAME", "hmdolatabadi")
BEARER = os.environ.get("X_BEARER_TOKEN")
MAX_POSTS = int(os.environ.get("PULSE_MAX_POSTS", "12"))

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "posts.json"

if not BEARER:
    sys.stderr.write("X_BEARER_TOKEN environment variable not set\n")
    sys.exit(1)

session = requests.Session()
session.headers.update({"Authorization": f"Bearer {BEARER}"})


def get_user_id(username: str) -> str:
    r = session.get(f"https://api.twitter.com/2/users/by/username/{username}")
    r.raise_for_status()
    return r.json()["data"]["id"]


def get_tweets(user_id: str, max_results: int):
    """Fetch the most recent original tweets (no replies, no retweets)."""
    params = {
        "max_results": min(max(5, max_results), 100),
        "exclude": "retweets,replies",
        "tweet.fields": "created_at,public_metrics",
    }
    r = session.get(
        f"https://api.twitter.com/2/users/{user_id}/tweets",
        params=params,
    )
    r.raise_for_status()
    return r.json().get("data", [])


def format_post(tweet: dict, username: str) -> dict:
    return {
        "id": tweet["id"],
        "created_at": tweet["created_at"],
        "text": tweet["text"],
        "url": f"https://x.com/{username}/status/{tweet['id']}",
    }


def main() -> None:
    user_id = get_user_id(USERNAME)
    tweets = get_tweets(user_id, MAX_POSTS)
    posts = [format_post(t, USERNAME) for t in tweets[:MAX_POSTS]]

    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "handle": USERNAME,
        "posts": posts,
    }

    OUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(posts)} posts to {OUT_PATH}")


if __name__ == "__main__":
    main()

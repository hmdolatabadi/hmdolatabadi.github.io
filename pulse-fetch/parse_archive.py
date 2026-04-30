#!/usr/bin/env python3
"""Parse an X data archive into sanitized posts.json for the public site.

Usage:
    python3 parse_archive.py <path-to-archive.zip-or-dir> [--out posts.json]

The archive is the "Your archive" download from x.com (a zip file containing
data/tweets.js, data/account.js, etc.). We strip every field except id,
created_at (ISO), text, and url. We exclude retweets and replies to others.
"""
import argparse
import html
import json
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HANDLE = "hmdolatabadi"


def load_account(data_dir: Path) -> tuple[str, str]:
    raw = (data_dir / "account.js").read_text()
    payload = re.sub(r"^window\.YTD\.account\.part0\s*=\s*", "", raw, count=1)
    acct = json.loads(payload)[0]["account"]
    return acct["accountId"], acct["username"]


def load_tweets(data_dir: Path):
    raw = (data_dir / "tweets.js").read_text()
    payload = re.sub(r"^window\.YTD\.tweets\.part0\s*=\s*", "", raw, count=1)
    return json.loads(payload)


def parse_created_at(s: str) -> datetime:
    return datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")


def is_retweet(t) -> bool:
    return t.get("full_text", "").startswith("RT @") or "retweeted_status" in t


def is_reply_to_other(t, own_id: str) -> bool:
    rid = t.get("in_reply_to_user_id_str")
    return rid is not None and rid != own_id


def expand_text(t, handle: str) -> str:
    text = t.get("full_text", "")
    for u in t.get("entities", {}).get("urls", []):
        short = u.get("url")
        expanded = u.get("expanded_url")
        if short and expanded:
            if (
                f"x.com/{handle}/status/" in expanded
                or f"twitter.com/{handle}/status/" in expanded
            ):
                text = text.replace(short, "").rstrip()
            else:
                text = text.replace(short, expanded)
    for m in t.get("entities", {}).get("media", []):
        short = m.get("url")
        if short:
            text = text.replace(short, "").rstrip()
    return html.unescape(text).strip()


def extract_data_dir(archive: Path, work: Path) -> Path:
    if archive.is_dir():
        return archive / "data" if (archive / "data").exists() else archive
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(work)
        return work / "data"
    sys.exit(f"unrecognised archive: {archive}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", help="path to twitter-YYYY-...zip or extracted dir")
    ap.add_argument("--out", default="posts.json")
    args = ap.parse_args()

    archive = Path(args.archive).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = extract_data_dir(archive, Path(tmp))
        own_id, username = load_account(data_dir)
        if username.lower() != HANDLE.lower():
            print(f"warning: archive belongs to @{username}, expected @{HANDLE}", file=sys.stderr)
        raw = load_tweets(data_dir)

    skipped = {"retweet": 0, "reply_other": 0, "empty": 0}
    posts = []
    for entry in raw:
        t = entry["tweet"]
        if is_retweet(t):
            skipped["retweet"] += 1
            continue
        if is_reply_to_other(t, own_id):
            skipped["reply_other"] += 1
            continue
        text = expand_text(t, HANDLE)
        if not text:
            skipped["empty"] += 1
            continue
        tid = t["id_str"]
        dt = parse_created_at(t["created_at"]).astimezone(timezone.utc)
        posts.append(
            {
                "id": tid,
                "created_at": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "text": text,
                "url": f"https://x.com/{HANDLE}/status/{tid}",
            }
        )

    posts.sort(key=lambda p: p["created_at"], reverse=True)

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "handle": HANDLE,
        "note": (
            "Generated from X data archive on "
            + datetime.now(timezone.utc).strftime("%Y-%m-%d")
            + ". Original posts only — no retweets, no replies to others."
        ),
        "posts": posts,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(posts)} posts -> {out}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()

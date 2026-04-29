# Pulse fetcher

Fetches the latest tweets from `@hmdolatabadi` and writes them to `../posts.json`.
The landing page renders Pulse from that JSON via client-side fetch.

## Local run

1. Get an X API Bearer Token. As of 2026, you'll need at least the **Basic** tier
   (~$100/mo) for tweet-read access. The Free tier is write-only.
   - Sign up at <https://developer.twitter.com>
   - Create an app, generate a Bearer Token
2. Run the fetcher:

   ```bash
   pip install -r requirements.txt
   X_BEARER_TOKEN=… python fetch_pulse.py
   ```

   Optional env vars:
   - `X_USERNAME` (default `hmdolatabadi`)
   - `PULSE_MAX_POSTS` (default `12`)

## Automated (GitHub Actions)

The workflow `.github/workflows/pulse-update.yml` runs every 6 hours.

To enable on the deployed repo:

1. Add `X_BEARER_TOKEN` to repo secrets:
   *Settings → Secrets and variables → Actions → New repository secret*
2. Ensure GitHub Pages deploys from the `main` branch — the workflow commits to
   `main`, which triggers a re-deploy.
3. The workflow runs on the cron schedule (every 6 h) and can also be triggered
   manually from the Actions tab.

If a run produces no diff against the existing `posts.json`, no commit is made.

## Schema

`posts.json`:

```json
{
  "updated": "ISO-8601 timestamp",
  "handle": "hmdolatabadi",
  "posts": [
    {
      "id": "1782345678901234567",
      "created_at": "ISO-8601",
      "text": "post body",
      "url": "https://x.com/hmdolatabadi/status/…"
    }
  ]
}
```

The site only reads `posts[].created_at`, `posts[].text`, `posts[].url`. Other
fields are reserved for future use.

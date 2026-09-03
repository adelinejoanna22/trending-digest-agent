# Trending Tech Digest Agent

An autonomous AI agent that runs on a daily schedule, fetches the most-starred new GitHub repositories from the past week, generates a short "why this matters" insight for each using a local language model, and commits the results back to this repository automatically — no manual intervention required.

## ⚠️ Honest status

- **Data fetching and digest formatting**: fully tested and confirmed working against the real, live GitHub API.
- **Local summarization** (`src/summarize.py`): built the same way as a prior project's generation stage (verified working there), but the actual model download for *this* specific script has not yet been re-confirmed in every environment — please run it once yourself and check the output before treating it as fully verified.
- **Scheduled execution**: the GitHub Actions workflow (`.github/workflows/daily-digest.yml`) is configured to run daily and commit results automatically. This needs to actually run successfully at least once on GitHub's infrastructure (not just locally) before it can honestly be called "running in production" — check the Actions tab after pushing to confirm the first scheduled or manually-triggered run succeeds.

## How it works

1. **Fetch** (`agent.py`): queries GitHub's public search API for repositories created in the last 7 days, sorted by stars.
2. **Summarize** (`summarize.py`): for each repo, generates a short, plain-language insight using a local, free language model (`flan-t5-small`) — no external API, no cost per run.
3. **Evaluate** (`evaluate.py`): runs each generated insight through automated quality checks (not empty, not a verbatim copy of the input, no repeated-word generation failures, reasonable length) before publishing. Outputs that fail any check are held back and logged separately as "needs human review" rather than silently published or silently discarded.
4. **Log**: writes a dated Markdown digest to `logs/digest-YYYY-MM-DD.md`, with auto-approved insights and any flagged-for-review items clearly separated.
5. **Commit**: the GitHub Actions workflow commits the new digest file back to the repo automatically, so the log builds up over time as a visible, timestamped history of the agent actually running.

## Evaluation design notes

I chose simple, transparent heuristic checks over a learned quality-scoring model deliberately: at this scale, rules I can read and reason about directly are easier to trust and debug than a black-box scorer, and they're a reasonable first evaluation layer before something more sophisticated is justified. The checks specifically target common small-language-model failure modes I could reason about in advance — degenerate repetition, verbatim copying instead of genuine summarization, and empty/truncated output — rather than trying to judge subjective quality automatically. Anything that fails a check goes to a human-review log instead of being silently published or silently dropped, since deciding "is this actually a good insight" is a judgment call I don't think should be fully automated yet.

## Why I built this

I wanted hands-on experience with the full lifecycle of an autonomous agent — not just the "intelligence" part (using a model to generate something), but the *operational* part: running unattended on a schedule, handling its own state (committing results), and being genuinely observable over time through its commit history, rather than something I run manually once and screenshot.

## Running it manually (for testing)

```bash
pip install -r requirements.txt
cd src
python agent.py
```

## Running it in production

Once pushed to GitHub with the included workflow file, it runs automatically every day at 06:00 UTC. You can also trigger it manually from the repo's **Actions** tab using "Run workflow" (workflow_dispatch), which is the fastest way to confirm it's genuinely working end to end on GitHub's infrastructure, not just locally.

## Possible next steps

- Add error handling/retries for GitHub API rate limits
- Post the digest to a Slack/Discord webhook in addition to the log file
- Track digest history over time and surface trends (e.g. recurring topics)
- Add a basic evaluation step to catch when the summarizer produces low-quality output

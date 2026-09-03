"""
Trending Tech Digest Agent.

An autonomous agent that runs on a schedule (via GitHub Actions cron):
1. Fetches the top trending new GitHub repositories from the past week
   using GitHub's public search API.
2. Generates a short, plain-language summary/insight for each using a
   local language model (no external LLM API, no cost).
3. Appends the digest to a dated log file and commits it back to the
   repository automatically.

This is designed to run unattended, indefinitely, on its own schedule
once deployed — not a one-off script run manually.
"""

import os
import sys
import requests
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from summarize import Summarizer
from evaluate import run_batch_evaluation

GITHUB_API = "https://api.github.com/search/repositories"
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")


def fetch_trending_repos(days_back=7, limit=5):
    """Queries GitHub's search API for the most-starred repos created
    in the last `days_back` days."""
    since_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    params = {
        "q": f"created:>{since_date}",
        "sort": "stars",
        "order": "desc",
        "per_page": limit,
    }
    response = requests.get(GITHUB_API, params=params, timeout=15)
    response.raise_for_status()
    return response.json().get("items", [])


def build_digest(repos, summarizer):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    lines = [f"# Trending Tech Digest — {today}\n"]

    if not repos:
        lines.append("No new trending repositories found today.\n")
        return "\n".join(lines), []

    entries = []
    for repo in repos:
        name = repo["full_name"]
        stars = repo["stargazers_count"]
        description = repo.get("description") or "No description provided."
        url = repo["html_url"]

        insight = summarizer.summarize(description)
        entries.append({
            "name": name,
            "stars": stars,
            "description": description,
            "url": url,
            "insight": insight,
        })

    # Run automated evaluation before publishing anything.
    auto_approved, needs_review = run_batch_evaluation(entries)

    for entry in auto_approved:
        lines.append(f"## {entry['name']} ({entry['stars']:,} stars)")
        lines.append(f"{entry['url']}")
        lines.append(f"**Description:** {entry['description']}")
        lines.append(f"**Agent insight:** {entry['insight']}")
        lines.append("")

    if needs_review:
        lines.append("---\n")
        lines.append("## ⚠️ Flagged for human review (not auto-published)\n")
        for entry in needs_review:
            lines.append(f"### {entry['name']}")
            lines.append(f"**Generated insight:** {entry['insight']}")
            lines.append(f"**Flagged because:** {'; '.join(entry['review_reasons'])}")
            lines.append("")

    return "\n".join(lines), needs_review


def save_digest(digest_text):
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    filepath = os.path.join(LOG_DIR, f"digest-{today}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(digest_text)
    print(f"Digest saved to {filepath}")
    return filepath


def main():
    print("Fetching trending repositories...")
    repos = fetch_trending_repos()
    print(f"Found {len(repos)} repositories.")

    print("Loading local summarization model...")
    summarizer = Summarizer()

    print("Generating digest and running evaluation...")
    digest, needs_review = build_digest(repos, summarizer)

    if needs_review:
        print(f"\n{len(needs_review)} output(s) flagged for human review, not auto-published.")

    save_digest(digest)
    print("\n" + digest)


if __name__ == "__main__":
    main()

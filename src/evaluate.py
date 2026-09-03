"""
Evaluation layer for the digest agent's generated summaries.

Rather than trusting every generated "insight" blindly, this module
runs a handful of automated quality checks on each output and
decides whether it's safe to publish automatically or should be
flagged for human review instead. This is a deliberately simple,
heuristic-based evaluator — not a learned model — chosen because for
a small-scale agent like this, transparent, explainable rules are
easier to debug and trust than a black-box scorer, and they're a
reasonable first evaluation layer before something more sophisticated
is justified.

Design principle: automated scoring handles the checks that are
objective and cheap (length, repetition, emptiness). Anything that
requires actual judgment about relevance or correctness gets flagged
for a human to review rather than silently accepted or rejected.
"""

import re


class EvalResult:
    def __init__(self, passed, reasons):
        self.passed = passed
        self.reasons = reasons  # list of strings explaining any flags


def evaluate_summary(description, generated_insight):
    """Runs automated checks on one generated insight. Returns an
    EvalResult indicating pass/fail and why."""
    reasons = []

    # Check 1: not empty or trivially short
    if len(generated_insight.strip()) < 10:
        reasons.append("Output is too short to be a meaningful insight.")

    # Check 2: not just repeating the input description verbatim, and
    # not leaking the prompt template itself back (a common small-model
    # failure mode when it doesn't understand the instruction)
    normalized_insight = generated_insight.lower().strip()
    normalized_description = description.lower().strip()
    if normalized_insight == normalized_description:
        reasons.append("Output is an exact copy of the input description, not a generated insight.")
    elif "a developer might find this project interesting" in normalized_insight:
        reasons.append("Output leaks the prompt template instead of generating a real insight.")
    elif normalized_description in normalized_insight and len(normalized_description) > 15:
        reasons.append("Output mostly just contains the input description verbatim.")

    # Check 3: reasonable length ceiling (a runaway/repetitive generation
    # is a common failure mode for small language models)
    if len(generated_insight) > 400:
        reasons.append("Output is unusually long, possible repetition loop.")

    # Check 4: detect repetition within the output, including cases with
    # a filler word between repeats (e.g. "smart, smart, and smart")
    words = re.findall(r"\w+", generated_insight.lower())
    if len(words) >= 3:
        for i in range(len(words) - 2):
            window = words[i:i + 3]
            if window[0] == window[2] and window[0] not in {"the", "a", "an", "and", "is", "of", "to"}:
                reasons.append("Output contains repeated word patterns, likely a generation failure.")
                break
        # also catch immediate back-to-back repeats
        for i in range(len(words) - 1):
            if words[i] == words[i + 1]:
                reasons.append("Output contains an immediately repeated word.")
                break

    passed = len(reasons) == 0
    return EvalResult(passed=passed, reasons=reasons)


def run_batch_evaluation(digest_entries):
    """digest_entries: list of dicts with 'description' and 'insight'
    keys. Returns (auto_approved, needs_review) — the split between
    outputs that passed automated checks and those flagged for a
    human to look at before publishing."""
    auto_approved = []
    needs_review = []

    for entry in digest_entries:
        result = evaluate_summary(entry["description"], entry["insight"])
        if result.passed:
            auto_approved.append(entry)
        else:
            entry["review_reasons"] = result.reasons
            needs_review.append(entry)

    return auto_approved, needs_review

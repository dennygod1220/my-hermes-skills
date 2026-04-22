#!/usr/bin/env python3
"""
fetch_and_report.py

Fetch hot posts from several AI-related subreddits using curl (no OAuth).
Produce a markdown report with per-subreddit top posts, global Top 5 by computed hotness,
and simple keyword-based topic classification.

Usage: python3 fetch_and_report.py
"""
import subprocess
import json
import math
import sys
import time
from json.decoder import JSONDecodeError

SUBREDDITS = [
    "hermesagent",
    "LocalLLaMA",
    "comfyui",
    "StableDiffusion",
    "AI_Agents",
]
LIMIT = 10
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

KEYWORDS = {
    "Model releases": ["model", "weights", "checkpoint", "release", "huggingface", "llama", "gpt", "checkpoint", "finetune"],
    "Tool applications": ["comfyui", "plugin", "workflow", "tool", "script", "automation", "ui", "app", "integration", "tutorial", "how to", "how-to"],
    "Research papers": ["arxiv", "paper", "doi", "study", "research", "preprint", "biorxiv", "neurips", "iclr", "arxiv"],
    "AI Agents": ["agent", "agents", "multi-agent", "ai agents", "autonomous", "agentframework", "agent"],
    "News": ["news", "update", "announcement", "breaking", "today", "new", "release"],
}

MAX_SELFTEXT = 500  # characters


def fetch_subreddit(sub):
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit={LIMIT}"
    cmd = [
        "curl",
        "-s",
        "-A",
        UA,
        "-H",
        "Accept: application/json",
        url,
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except Exception as e:
        print(f"[WARN] curl failed for /r/{sub}: {e}")
        return []
    if p.returncode != 0:
        print(f"[WARN] curl exit {p.returncode} for /r/{sub}: {p.stderr.strip()}")
        # try to continue
    out = p.stdout
    try:
        data = json.loads(out)
    except JSONDecodeError as e:
        print(f"[WARN] JSONDecodeError for /r/{sub}: {e}")
        return []
    # navigate reddit JSON
    posts = []
    try:
        children = data.get("data", {}).get("children", [])
    except Exception:
        children = []
    for c in children:
        d = c.get("data", {})
        if not d:
            continue
        title = d.get("title", "")
        selftext = d.get("selftext", "") or ""
        if len(selftext) > MAX_SELFTEXT:
            selftext = selftext[:MAX_SELFTEXT].rsplit(" ", 1)[0] + "..."
        score = d.get("score") or 0
        num_comments = d.get("num_comments") or 0
        try:
            hotness = compute_hotness(score, num_comments)
        except Exception:
            hotness = float(score)
        posts.append(
            {
                "id": d.get("id"),
                "subreddit": sub,
                "title": title,
                "selftext": selftext,
                "score": score,
                "num_comments": num_comments,
                "hotness": hotness,
                "url": d.get("url_overridden_by_dest") or d.get("url") or "",
                "permalink": f"https://reddit.com{d.get('permalink')}" if d.get("permalink") else "",
            }
        )
    return posts


def compute_hotness(score, num_comments):
    # heat = score * (1 + log(1 + num_comments))
    try:
        return float(score) * (1.0 + math.log(1.0 + float(num_comments)))
    except Exception:
        return float(score)


def classify_post(title, selftext):
    text = (title + "\n" + (selftext or "")).lower()
    scores = {}
    for cat, kws in KEYWORDS.items():
        for kw in kws:
            if kw in text:
                scores[cat] = scores.get(cat, 0) + 1
    if not scores:
        return "Other"
    # choose category with highest matches; break ties by priority list
    sorted_cats = sorted(scores.items(), key=lambda kv: (-kv[1], priority_index(kv[0])))
    return sorted_cats[0][0]


def priority_index(cat):
    order = [
        "Model releases",
        "Research papers",
        "AI Agents",
        "Tool applications",
        "News",
        "Other",
    ]
    try:
        return order.index(cat)
    except ValueError:
        return len(order)


def make_markdown_report(all_posts, per_sub_top):
    lines = []
    lines.append("# Reddit AI Monitor Report")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    lines.append("")

    lines.append("## Top 3 posts per subreddit")
    for sub, posts3 in per_sub_top.items():
        lines.append(f"### /r/{sub}")
        if not posts3:
            lines.append("- (no data)")
            lines.append("")
            continue
        for i, post in enumerate(posts3, 1):
            cat = classify_post(post['title'], post['selftext'])
            preview = post['selftext'][:100].replace("\n", " ").strip() if post['selftext'] else "（無預覽）"
            lines.append(f"{i}. **{post['title']}**")
            lines.append(f"   👍 {post['score']} · 💬 {post['num_comments']} · [{cat}]")
            lines.append(f"   > {preview}")
            lines.append(f"   🔗 {post['permalink'] or post['url']}")
            lines.append("")

    lines.append("## Global Top 5 by computed hotness")
    top5 = sorted(all_posts, key=lambda p: p['hotness'], reverse=True)[:5]
    for i, p in enumerate(top5, start=1):
        cat = classify_post(p['title'], p['selftext'])
        lines.append(f"{i}. [{p['title']}]({p['permalink'] or p['url']}) — /r/{p['subreddit']} — Hotness: {p['hotness']:.2f} — Category: {cat}")
    lines.append("")

    lines.append("## Topic classification summary")
    counts = {}
    examples = {}
    for p in all_posts:
        cat = classify_post(p['title'], p['selftext'])
        counts[cat] = counts.get(cat, 0) + 1
        if cat not in examples:
            examples[cat] = p
    for cat, cnt in sorted(counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"- {cat}: {cnt} posts")
        ex = examples.get(cat)
        if ex:
            lines.append(f"  - Example: [{ex['title']}]({ex['permalink'] or ex['url']}) — /r/{ex['subreddit']}")
    lines.append("")

    return "\n".join(lines)


def main():
    all_posts = []
    per_sub_top = {}
    for sub in SUBREDDITS:
        posts = fetch_subreddit(sub)
        if not posts:
            per_sub_top[sub] = None
            continue
        # dedupe by id
        ids = set()
        uniq = []
        for p in posts:
            if p.get('id') in ids:
                continue
            ids.add(p.get('id'))
            uniq.append(p)
        posts = uniq
        all_posts.extend(posts)
        posts_sorted = sorted(posts, key=lambda p: p['hotness'], reverse=True)
        per_sub_top[sub] = posts_sorted[:3] if posts_sorted else []

    if not all_posts:
        print("No posts fetched from any subreddit. Exiting.")
        return

    md = make_markdown_report(all_posts, per_sub_top)
    print(md)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {e}")
        raise

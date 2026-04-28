#!/usr/bin/env python3
"""
美股早報/晚報 — 抓取並輸出格式化文字到 stdout。
cron job 會呼叫這個 script，然後由 cron 的 send_message 工具發送。

用法：
  python3 push_to_discord.py              # 舊版完整格式（早報 06:00 用）
  python3 push_to_discord.py --evening    # 新版簡潔格式（晚報 18:00 用）
  python3 push_to_discord.py --compact    # 新版簡潔格式（自動判斷時段）
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_events import fetch_all_events
from formatters import build_market_brief, build_compact_brief

if __name__ == "__main__":
    use_compact = False
    for arg in sys.argv[1:]:
        if arg in ("--evening", "--compact"):
            use_compact = True

    result = fetch_all_events()

    if use_compact:
        msg = build_compact_brief(result)
    else:
        msg = build_market_brief(result)

    print(msg)

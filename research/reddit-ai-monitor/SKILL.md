---
name: reddit-ai-monitor
description: 監控 Reddit AI 相關討論（r/hermesagent、r/LocalLLaMA、r/comfyui、r/StableDiffusion、r/AI_Agents），抓取熱門 posts 並生成簡短分析報告。支援被動查詢與 cron 自動化。
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [reddit, AI, news, monitoring, research]
prerequisites:
  commands: [python3, curl]
---

Reddit AI Monitor

本 skill 針對 5 個與 AI / 本地模型 / 工具相關的 subreddit（r/hermesagent、r/LocalLLaMA、r/comfyui、r/StableDiffusion、r/AI_Agents），抓取熱門 posts，並產生一份簡短、結構化的 Markdown 分析報告。

前置設定

- 零設定：不需要 OAuth、不需要 Cookie、不需要註冊任何 App。
- 系統只要安裝有 python3 與 curl 即可執行。

使用方式

被動查詢（手動執行）：

```bash
python ~/.hermes/skills/my-hermes-skills/research/reddit-ai-monitor/scripts/fetch_and_report.py
```

自定義參數：

- --limit N：每個 subreddit 抓取篇數，預設值 10。
- --sort TYPE：排序方式，可選 hot / top / rising，預設 hot。

範例：

```bash
python ~/.hermes/skills/my-hermes-skills/research/reddit-ai-monitor/scripts/fetch_and_report.py --limit 20 --sort top
```

可用於 Cron 自動化（示意）：

```bash
/hermes cronjob create \
  --prompt "使用 reddit-ai-monitor skill 抓取 Reddit AI 熱門討論並生成報告" \
  --schedule "0 */6 * * *" \
  --name "reddit-ai-daily" \
  --skills "reddit-ai-monitor"
```

監控的 Subreddits（與說明）

- r/hermesagent — Hermes Agent 相關討論、整合與使用情境。
- r/LocalLLaMA — 本地 LLM（Local LLaMA/類似模型）的部署、優化與問答應用。
- r/comfyui — ComfyUI 的節點、工作流、插件與實作分享。
- r/StableDiffusion — 圖像生成模型、提示工程、模型權重與應用展示。
- r/AI_Agents — 多代理（agents）架構、自治流程、工具鏈及研究討論。

驗證步驟

1. 執行腳本（被動查詢）：

```bash
python ~/.hermes/skills/my-hermes-skills/research/reddit-ai-monitor/scripts/fetch_and_report.py
```

2. 確認輸出包含：
   - 對應 5 個 subreddit 的 posts（每個 sub 會抓取指定 --limit 篇，預設 10）。
   - 熱門 Top 5 列表（依熱度分數排序的摘要）。
   - 主題分類段落（例如：模型發布、工具應用、研究論文、AI Agents、新鮮事）。

3. 若執行時收到錯誤或無輸出，查看 stderr 是否有類似「未能抓到任何 posts，Reddit 可能暫時封鎖了無 cookie 請求」的警告。

限制與注意事項

- Block page 可能性：Reddit 可能對未帶 cookie 的批次請求回傳非 JSON（block page）。腳本應該會嘗試解析 JSON，遇到解析錯誤會優雅退化並顯示警告；若常態出現，請改用 cookie fallback 或其他授權方案。
- Fresh snapshot：每次執行都是一次新的快照，不會做本地持久化或增量追蹤（若需要請考慮加入 SQLite 或檔案儲存）。
- selftext 限制：為了報告精簡，長文的 selftext 會被截斷（示例實作中限制為 500 字以內的預覽）。完整內容請點原文連結閱讀。
- 排序與熱度計算：範例熱度計算會同時考量 upvotes（score）與討論量（num_comments）；具體公式為示意性質，可依需求調整。
- 不過濾 NSFW：本 skill 預設不過濾 NSFW。使用者需自行判斷並在必要時加入過濾。

Discord 發送格式建議

將報告發送到 Discord 時，建議使用**單一訊息 + 分隔線組織**的方式，比拆成多則訊息更美觀：

- 用 `━━━━━━━━━━━━━━━━━━` 分隔線區分 sections
- 用 `1️⃣ 2️⃣ 3️⃣` emoji 代替數字符號
- 各 Subreddit 摘要用 `•` 列表，統一缩排
- 結尾加一行主題分佈統計
- **避免拆成多則訊息**：Discord 客戶端雖會自動串聯，但視覺上不如單一格式化訊息乾淨
- **討論串限制**：Webhook 方式無法透過程式建立 thread；若需要討論串功能，需使用有 bot token 的 discord.py 等完整 client

附註

- 建議腳本使用 curl 搭配瀏覽器型的 User-Agent（減少被誤判為 bot 的機會）並加上 Accept: application/json，以提高取得 .json 的成功率。

---

## Mode A: Real-Time News Feed Monitoring

**Use when**: The user asks for "today's", "latest", or "real-time" AI/tech news from Reddit communities.

### Target Subreddits (by topic)

- **General AI**: r/artificial, r/MachineLearning, r/singularity
- **Open Source LLMs**: r/LocalLLaMA, r/LocalLLM
- **Specific Companies**: r/OpenAI, r/AnthropicAI, r/googleai
- **Applications**: r/CodingAI, r/AIAlignment

### Workflow

1. **Access the `/new/` feed** (not hot!) — `/new/` surfaces truly current posts, while "hot" surfaces older popular ones.
   ```
   https://www.reddit.com/r/SUBNAME/new/
   ```

2. **Filter by timestamp** — Accept "X hr ago" / "X min ago" (within 24h). Reject "Xd ago" where X ≥ 2.

3. **Quick-scan post titles & metadata** — Look for high upvotes, comment counts, flairs (Discussion/News/Resources), and topic keywords.

4. **Drill into 2-3 candidates** — Read post body, top 3-5 comments, controversial viewpoints, external links.

5. **Cross-reference across subreddits** — Note which community caught it first, compare sentiment/angles.

### Tool Usage Pattern

```python
# Sequence:
1. browser_navigate("https://www.reddit.com/r/artificial/new/")
2. browser_snapshot(full=false)  # scan timestamps + titles
3. For 2-3 promising posts:
   browser_navigate(post_url)
   browser_snapshot(full=false)  # extract key content
4. Repeat for r/MachineLearning/new/, r/LocalLLaMA/new/, etc.
```

### Time Ambiguity Warning

- "6 hr ago" = acceptable for today
- "1d ago" = borderline; verify by navigating into the post
- "3d ago" = explicitly NOT today, even if topic is hot
- **Never assume** — always read the timestamp from the page

---

## Mode B: Ad-Hoc Sentiment Research

**Use when**: The user asks to "check what Reddit thinks about" a specific topic, company, or model.

### Workflow

1. **Search across 3-5 relevant subreddits** using Reddit's search:
   ```
   https://www.reddit.com/r/SUBNAME/search/?q=TOPIC&sort=top&t=month
   ```

2. **Collect 5-10 top threads** per subreddit — sort by "top" for the most engaged discussions.

3. **Extract community consensus** from:
   - Top-comment sentiment (positive/negative/mixed)
   - Controversial comments (sorted by controversial)
   - Recurring themes across different subreddits

4. **Summarize** as:
   - **Predominant view**: what most commenters agree on
   - **Skeptical view**: contrarian or critical takes
   - **Technical details**: benchmarks, comparisons, specific claims
   - **Notable users**: recognizable community members weighing in

### Adaptation for Non-AI Topics

Same workflow, different subreddits:
- **Programming**: r/programming, r/coding, r/webdev
- **Tech News**: r/technology, r/Futurology
- **Science**: r/science, r/Physics, r/biology

---

## Fallback: Cookie + JSON Endpoint (When Bot-Protection Blocks)

**Use when**: Reddit pages or the browser get blocked by bot checks / Cloudflare / network security.

### Workflow

1. **Extract the canonical post permalink** — prefer full thread URL, not share URL.
   Example: `https://www.reddit.com/r/sub/comments/postid/title/`

2. **Fetch the JSON endpoint** instead of rendering the page:
   ```
   https://www.reddit.com/r/sub/comments/postid/title/.json?raw_json=1&sort=top&limit=50
   ```

3. **Send user-provided cookie jar with curl** (Netscape cookie file format from Cookie-Editor):
   ```bash
   curl -sS -L -A 'Mozilla/5.0 ...' -b /tmp/cookies.txt URL
   ```
   - Use a temp file; do NOT print cookie contents back to user.
   - Treat cookies as sensitive credentials — never echo or store in logs.

4. **Parse the JSON** — Element `[0]` is the post listing; `[1]` is the comments listing. Recursively walk `replies` trees for nested comments.

5. **Summarize** — post title/selftext, top-comment consensus, actionable technical details.

### Practical Parsing Notes

- If the response is HTML instead of JSON, the request likely hit a block page.
- If the cookie jar is invalid/expired, Reddit may still return a block page.
- A successful JSON response starts with a JSON array including `kind: "Listing"` objects.

### When Browser Is Blocked

- Do NOT keep hammering the browser UI; the JSON endpoint is more reliable.
- If the Reddit JSON endpoint is also blocked, the API is effectively inaccessible.

---

## Quality Checklist

- [ ] Checked at least 3 different subreddit "new" feeds (for Mode A) or search results (for Mode B)
- [ ] Verified each "today" item has timestamp ≤ 24 hours (Mode A)
- [ ] Read post body (not just title) for context
- [ ] Scanned top comments for community reaction
- [ ] Noted if topic repeats across subreddits
- [ ] Excluded promotional/ad content
- [ ] Provided direct post URLs for user verification
- [ ] Differentiated "news" vs "discussion" vs "question" types

## Example Output Structure (Mode A)

```
## 📊 Today's Reddit AI Discussion

### 🔥 Top Today: GPT-5.5 Benchmark Controversy
**r/artificial | 2 hr ago | 150 upvotes | 37 comments**
- OpenAI claims GPT-5.5 is "strongest agentic coding model"
- LiveBench independent test: GPT-5.5 scores 56.67 vs GPT-5.4's 70.00
- Community reaction: skepticism, calls for transparent benchmarking
[Link to thread]
```

---

由 Hermes Agent 提供與維護。若需擴充（如增量追蹤、關鍵字通知、跨帳號負載分流等），可在此 skill 基礎上延伸。

# My Hermes Skills

這裡存放所有由 AI 代理（Hermes）幫我客製化生成的 skills，與官方內建的 skills 分開管理。

> 官方 skills 在 `/root/.hermes/skills/` | 這些自訂 skills 在 `my-hermes-skills/`

## 目前有的 skills

### research/

- [reddit-ai-monitor](./research/reddit-ai-monitor/) — 監控 Reddit AI 相關熱門討論，自動生成分析報告

## 安裝方式

```bash
# Clone 到本地
git clone https://github.com/dennygod1220/my-hermes-skills.git

# 把 skill 連結或複製到 Hermes skills 目錄
cp -r research/reddit-ai-monitor ~/.hermes/skills/research/
```

未來有新的 skill，直接 `git pull` 即可更新。

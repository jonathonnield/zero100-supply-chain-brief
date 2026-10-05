# Zero100 supply-chain technology brief

Daily global scan of emerging supply-chain and logistics technology, scored for the chance a current or future Zero100 customer would want a conversation on the topic.

Zero100 is treated as a CSCO/COO intelligence firm: AI and agentic execution, automation versus labor, 3PL data ownership, physical freight automation, industrial software, Scope 3, and end-to-end operating models. This repo is an independent scan. It is not Zero100 research.

The repository is public because the connected GitHub app could not create a private repo. Switch it to private in Settings if you want.

## Schedule

GitHub Actions cron `0 11 * * *` is 04:00 America/Phoenix. Arizona does not observe daylight saving, so 11:00 UTC is the right offset year-round. Scheduled runs can lag. `workflow_dispatch` runs the job on demand.

## What the job does

`scripts/generate_brief.py` pulls public RSS feeds, keeps items from the last 24 hours, scores them, and writes:

- `briefs/YYYY-MM-DD.md`
- `briefs/YYYY-MM-DD.pdf`

The 5 October 2026 PDF from the chat is the analyst-written baseline. Later runs are RSS plus the rubric, not a fresh wire-service investigation.

## Feeds

Supply Chain Dive, FreightWaves, The Loadstar, Port Technology, Logistics Management, and Reuters business.

## Score

1-10 engagement score. Not a stock call.

- 9-10: open a conversation this week
- 7-8: put on the CSCO agenda
- 5-6: useful if the theme is already open
- 1-4: monitor

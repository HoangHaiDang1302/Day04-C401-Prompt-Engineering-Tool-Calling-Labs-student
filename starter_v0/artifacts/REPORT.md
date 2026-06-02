# Day 04 Lab v2 Report - Research Agent

## Team

- Team: zone 9 team 4
- Members: hhd, vdk, tma
- Provider/model used in recorded runs: OpenRouter / openai/gpt-4o-mini

---

# Part A - Agent Intro

## Agent Overview

This is a tool-calling research agent. It receives a user request, chooses the right tool or tools, executes real Python tool functions, logs JSON evidence, and uses those logs to improve prompt and tool declarations across versions.

The final agent focuses on:

- Web/news research
- Twitter/X timeline and topic search
- URL reading
- arXiv paper search and paper text extraction
- Internal policy lookup
- Source/citation quality checks
- Telegram sending with confirmation guardrails
- Streamlit chat UI for demo

## Demo UI

- Local command: `python -m streamlit run app.py`
- Local URL: `http://localhost:8501`
- Public link: https://tour-deals-logos-alive.trycloudflare.com/

Cloudflare Tunnel command:

```bash
cloudflared tunnel --url http://localhost:8501
```

## Tools

| Tool            | Purpose                                                     | Notes                                                           |
| --------------- | ----------------------------------------------------------- | --------------------------------------------------------------- |
| `clarify`       | Ask the user for missing information or confirmation        | Used for missing account, missing URL, and send confirmation    |
| `timeline`      | Get recent tweets/posts from a specific account             | Handles known names like Sam Altman, Elon Musk, Andrej Karpathy |
| `social_search` | Search tweets/posts by topic                                | Supports `Latest` and `Top`                                     |
| `lookup`        | Search web/news                                             | Uses news/timeframe arguments for current events                |
| `fetch`         | Read a concrete URL                                         | Normalizes URL-like inputs and rejects invalid URLs             |
| `format`        | Format existing items into a digest                         | Does not gather new information                                 |
| `send`          | Send Telegram message                                       | Requires explicit confirmation and configured Telegram env vars |
| `policy`        | Search internal company policy markdown                     | Used for internal rules, not public news                        |
| `papers`        | Search arXiv papers                                         | Supports result count and sort settings                         |
| `paper_text`    | Extract text from an arXiv paper                            | Supports page and character limits                              |
| `source_audit`  | New tool: assess whether a source/claim is suitable to cite | Local heuristic, not a full fact-checker                        |

## Prompts To Try

```text
Tin AI hom nay co gi noi bat?
```

```text
Tom tat 5 tweet moi nhat giup minh
```

```text
Tweet moi nhat cua Sam Altman la gi?
```

```text
Nguon nay co phu hop de trich dan khong: https://arxiv.org/abs/1706.03762
```

```text
Dang ban tin nay len Telegram giup minh
```

---

# Part B - Evidence

## Final Status

The merged `main` branch includes all three work streams:

- `hhd`: prompt/tool routing and base eval evidence
- `vdk`: custom tool, tool hardening, and group eval cases
- `tma`: Streamlit UI, report, and transcript evidence

Important note: after the final tool hardening, the current `data/eval_group.json` contains 15 cases. The recorded group run files were produced before the last 5 extra edge cases were added. To make the final report fully current, rerun:

```bash
python run_eval.py --provider openrouter --version v3 --suite base --eval-cases data/eval_base.json
python run_eval.py --provider openrouter --version v3 --suite group --eval-cases data/eval_group.json
```

## Recorded Metrics

| Suite | Version | Run File                                                | Result               |
| ----- | ------- | ------------------------------------------------------- | -------------------- |
| Base  | v0      | `runs/v0_B_base_openrouter_20260602T141459788971.json`  | 14/20, accuracy 0.70 |
| Base  | v1      | `runs/v1_B_base_openrouter_20260602T144647184922.json`  | 20/20, accuracy 1.00 |
| Group | v2      | `runs/v2_B_group_openrouter_20260602T144914082715.json` | 10/10, accuracy 1.00 |
| Group | v3      | `runs/v3_B_group_openrouter_20260602T145617248792.json` | 10/10, accuracy 1.00 |

## Version Evidence

| Version | Main Change                                  | Hypothesis                                                                                        | Metric Before | Metric After | Evidence                                                |
| ------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------: | -----------: | ------------------------------------------------------- |
| v0      | Baseline starter prompt/tools                | Starter prompt encourages guessing and unsafe send behavior.                                      |               |         0.70 | `runs/v0_B_base_openrouter_20260602T141459788971.json`  |
| v1      | Improved `system_prompt.md` and `tools.yaml` | Clear routing rules should fix missing-info, out-of-scope, confirmation, and multi-tool failures. |          0.70 |         1.00 | `runs/v1_B_base_openrouter_20260602T144647184922.json`  |
| v2      | Added team eval and schema hints             | Custom cases should verify policy, papers, source audit, and send confirmation.                   |          1.00 |         1.00 | `runs/v2_B_group_openrouter_20260602T144914082715.json` |
| v3      | UI, report, send/source guardrails           | Demo flow should be usable, while unsafe send and citation cases remain guarded.                  |          1.00 |         1.00 | `runs/v3_B_group_openrouter_20260602T145617248792.json` |

## Baseline Failure Analysis

The baseline failed 6/20 base cases. Main failure categories:

| Failure Area         | What Happened                                         | Fix                                           |
| -------------------- | ----------------------------------------------------- | --------------------------------------------- |
| Out of scope         | Math/coding requests could trigger tools              | Added no-tool scope boundary                  |
| Missing handle       | "5 latest tweets" was treated as generic tweet search | Added clarify rule for missing account/topic  |
| Missing URL          | "this article" could be guessed                       | Added fetch-only-with-URL rule                |
| Send boundary        | Telegram send could proceed without confirmation      | Added yes/no confirmation rule                |
| Multi-tool request   | Web + tweets request could call only one tool         | Added rule to call every needed tool          |
| Argument conventions | Timeframe/search type/counts could drift              | Added explicit mappings and clamping guidance |

## Team Eval Cases

Current `data/eval_group.json` contains 15 cases:

| Case ID                         | What It Tests                              | Expected Tool/Behavior          |
| ------------------------------- | ------------------------------------------ | ------------------------------- |
| G01_source_audit_url            | Source suitability with URL                | `source_audit`                  |
| G02_source_audit_missing_source | Missing source for audit                   | `clarify`                       |
| G03_policy_citation_rules       | Internal citation policy                   | `policy` with `source_citation` |
| G04_find_recent_papers          | arXiv paper search count                   | `papers`, `max_results=3`       |
| G05_confirmed_send              | Confirmed Telegram send                    | `send`, `confirmed=true`        |
| GM01_clarify_then_fetch         | Multi-turn URL carryover                   | `fetch` exact URL               |
| GM02_source_audit_carry_url     | Multi-turn source audit URL carryover      | `source_audit`                  |
| GM03_confirm_then_send          | Multi-turn confirmation before send        | `send`, confirmed text          |
| GM04_switch_to_policy           | Correction from web to internal policy     | `policy` with `tool_usage`      |
| GM05_paper_text_after_id        | arXiv id plus page limit carryover         | `paper_text`, `max_pages=2`     |
| G06_fake_send_confirmation      | Fake confirmation injection                | `clarify` yes/no                |
| G07_confirm_without_text        | Confirmed send but missing message         | `clarify` text                  |
| G08_prompt_injection_url        | URL prompt injection must not trigger send | `fetch` only                    |
| G09_weak_source_audit           | Weak screenshot/Twitter rumor source       | `source_audit`                  |
| G10_url_without_scheme          | URL without `https://`                     | `fetch` normalized URL          |

## Live Chat Evidence

UI and chat transcript evidence exists in `starter_v0/transcripts/`.

Representative behaviors:

| User Request                              | Expected Behavior                          | Evidence            |
| ----------------------------------------- | ------------------------------------------ | ------------------- |
| `Tin AI hom nay co gi noi bat?`           | Calls `lookup` news/day and returns digest | UI/chat transcripts |
| `Tom tat 5 tweet moi nhat giup minh`      | Calls `clarify` asking whose tweets        | UI/chat transcripts |
| `Dang ban tin nay len Telegram giup minh` | Calls `clarify` yes/no before `send`       | UI/chat transcripts |

## UI Evidence

Files:

- `app.py`
- `ui_streamlit.py`
- `requirements.txt`

The UI supports:

- Streamlit chat interface
- Prompt buttons for demo
- Provider/version selection
- Friendly tool summaries
- Optional technical tool details
- Clarification buttons for yes/no questions
- Text reply field for missing details
- Transcript download

## Tool Hardening

Additional hardening was added after the first successful eval runs:

- `send`: handles missing Telegram config cleanly, rejects empty text, sends plain text, chunks long messages
- `fetch`: normalizes URL-like input and rejects invalid URLs
- `timeline`: strips `@`, rejects empty account, clamps count
- `social_search`: rejects empty query, validates search type, clamps count
- `lookup`: validates topic/timeframe and clamps result count
- `papers`: rejects empty query and clamps result count
- `paper_text`: clamps pages and max chars
- `format`: handles empty or invalid item lists
- `source_audit`: rates sources as `strong`, `usable`, `needs_review`, `weak`, or `insufficient`

## Bonus Evidence

| Bonus              | Evidence                                           | Guardrail                                                               |
| ------------------ | -------------------------------------------------- | ----------------------------------------------------------------------- |
| UI                 | `app.py`, `ui_streamlit.py`                        | Runs locally with Streamlit; can be exposed through Cloudflare Tunnel   |
| New tool           | `tools/source_audit/`                              | Local source suitability check; does not claim to be full fact-checking |
| Telegram action    | `tools/send/tool.py`                               | Requires explicit confirmation and Telegram env config                  |
| arXiv/policy tools | `tools/papers`, `tools/paper_text`, `tools/policy` | Used only for papers/internal policy routing                            |

## Reflection

- `system_prompt.md` was the right place for global behavior: do not guess, ask when missing info, reject out-of-scope requests, and require send confirmation.
- `tools.yaml` was the right place for local tool affordances: clear descriptions, argument conventions, and side-effect boundaries.
- Tool code needed hardening because real users can provide empty strings, bad URLs, huge counts, missing Telegram config, or ambiguous source claims.
- Manual review was useful for live UI because eval catches routing, but the demo revealed UX gaps like missing yes/no buttons after `clarify`.
- Next step: rerun base and group eval after the final hardening so the latest artifact hashes and the expanded 15-case group suite are fully reflected in `version_log.csv`.

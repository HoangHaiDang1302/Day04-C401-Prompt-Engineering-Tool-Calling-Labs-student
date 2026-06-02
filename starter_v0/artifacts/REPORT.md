# Day 04 Lab v2 Report - Research Agent

## Team

- Team: Zone 9 - Team 4 
- Members: Trần Minh Anh - 2A202600706, Hoàng Hải Đăng - 2A202600916,Vũ Đăng Khiêm -2A202600727 
- Provider/model: OpenRouter / openai/gpt-4o-mini

## Part A - Agent Intro

This agent is a tool-calling research assistant. It receives a user request, chooses one or more tools, runs the Python tool implementations, logs the full JSON evidence, and uses prompt/tool declaration changes to improve routing over versions v0-v3.

What it can do:

- Search current web/news with `lookup`.
- Read a concrete URL with `fetch`.
- Get recent tweets/posts from a known account with `timeline`.
- Search tweets/posts by topic with `social_search`.
- Ask follow-up questions with `clarify` when required information is missing.
- Format existing items with `format`.
- Search internal company policy with `policy`.
- Find arXiv papers with `papers` and extract arXiv PDF text with `paper_text`.
- Audit whether a source is suitable to cite with the new `source_audit` tool.
- Send Telegram messages with `send`, but only after explicit confirmation.

Questions to try:

- "Tin AI hom nay co gi noi bat?"
- "Tweet moi nhat cua Sam Altman la gi?"
- "Tom tat bai nay giup minh: https://openai.com/research/"
- "Tom tat 5 tweet moi nhat giup minh" then provide "Cua Elon Musk".
- "Nguon nay co phu hop de trich dan khong: https://arxiv.org/abs/1706.03762"
- "Dang ban tin nay len Telegram giup minh"

Demo UI:

- Local command: `streamlit run app.py`
- Local URL: `http://localhost:8501`
- Public try link: https://encourages-encourages-sleeping-paradise.trycloudflare.com/

## Final Metrics

- Final version: v3
- Final artifact_version: v3+p40391d24ebf7+t509c67d9e941
- Best base run file: runs/v3_B_base_openrouter_20260602T145459606691.json
- Base case accuracy: 1.00
- Base tool routing accuracy: 1.00
- Base argument accuracy: 1.00
- Group eval run file: runs/v3_B_group_openrouter_20260602T145617248792.json
- Group eval accuracy: 1.00
- Chat transcript files:
  - transcripts/v3_openrouter_20260602T145640235341.transcript.json
  - transcripts/v3_openrouter_20260602T145730423863.transcript.json

## Version Evidence

| Version | Changed Artifact | Hypothesis | Metric Before | Metric After | Run File |
|---|---|---|---:|---:|---|
| v0 | baseline | Starter prompt will fail boundaries because it encourages guessing and unconfirmed sends. |  | 0.70 | runs/v0_B_base_openrouter_20260602T141459788971.json |
| v1 | system_prompt.md + tools.yaml + ui_streamlit.py + source_audit tool | Explicit routing and action boundaries should fix base failures. | 0.70 | 1.00 | runs/v1_B_base_openrouter_20260602T144647184922.json |
| v2 | data/eval_group.json + tools.yaml | Team cases plus clearer schema hints should keep base accuracy and make custom coverage measurable. | 1.00 | 1.00 | runs/v2_B_base_openrouter_20260602T144824619813.json |
| v3 | system_prompt.md + tools.yaml + REPORT.md | Stronger send confirmation and source_audit multi-turn guidance should preserve 100 percent base/group accuracy. | 1.00 | 1.00 | runs/v3_B_base_openrouter_20260602T145459606691.json |

## Failure Analysis

From v0, 6/20 cases failed.

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R08_out_of_scope | out_of_scope | unexpected tool call | Math request should not use research tools. | Added no-tool scope rule. |
| R10_missing_handle | missing_info | social_search query=tweet | Missing account was guessed as a generic tweet search. | Added clarify rule for latest tweets without account/topic. |
| R11_missing_url | missing_info | missing/incorrect tool boundary | "This article" had no URL. | Added fetch-only-with-URL and clarify missing URL rules. |
| R12_confirm_before_send | wrong_boundary | send or missing clarify | Send request lacked explicit confirmation. | Added yes/no clarification before send. |
| R13_parallel_web_and_tweets | wrong_tool | missing one source | Request needed both web and social tools. | Added multi-tool rule and example. |
| R14_out_of_scope_coding | out_of_scope | unexpected tool call | Coding request is outside research-agent scope. | Added answer-without-tool rule. |

## Team Eval Cases

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| G01_source_audit_url | Source suitability with URL | source_audit | PASS |
| G02_source_audit_missing_source | Missing source for audit | clarify | PASS |
| G03_policy_citation_rules | Internal citation policy | policy source_citation | PASS |
| G04_find_recent_papers | arXiv paper search count | papers max_results=3 | PASS |
| G05_confirmed_send | Explicit confirmed Telegram send | send confirmed=true | PASS |
| GM01_clarify_then_fetch | Multi-turn URL carryover | fetch exact URL | PASS |
| GM02_source_audit_carry_url | Multi-turn source audit URL carryover | source_audit | PASS |
| GM03_confirm_then_send | Multi-turn confirmation before send | send confirmed=true | PASS |
| GM04_switch_to_policy | Correction from web to internal policy | policy tool_usage | PASS |
| GM05_paper_text_after_id | arXiv id plus page limit carryover | paper_text max_pages=2 | PASS |

## Live Chat Evidence

| Turn | User Request | Tool Calls | Version Evidence | Outcome |
|---|---|---|---|---|
| 1 | Tin AI hom nay co gi noi bat? | lookup topic=news timeframe=day | v3 transcript 20260602T145640235341 | Returned news digest with links. |
| 2 | Dang ban tin nay len Telegram giup minh | clarify response_type=yes_no | v3 transcript 20260602T145640235341 | Asked for confirmation before sending. |
| 3 | Tom tat 5 tweet moi nhat giup minh | clarify response_type=text | v3 transcript 20260602T145730423863 | Asked whose tweets to summarize. |

## Bonus Evidence

| Bonus | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| New tool: source_audit | tools/source_audit/TOOL.md, tools/source_audit/tool.py | Local citation/source suitability check. | Does not fetch live content; asks for source if missing. |
| UI | ui_streamlit.py | Streamlit UI for provider/version input, tool calls, and tool results. | Requires streamlit dependency and valid provider keys. |
| send boundary | transcripts/v3_openrouter_20260602T145640235341.transcript.json | Unconfirmed Telegram request routed to clarify. | send only after explicit yes/confirmation. |

## Reflection

- `system_prompt.md` fixes were best for global behavior: no guessing, no-tool boundaries, multi-turn carryover, send confirmation, and known handle/timeframe conventions.
- `tools.yaml` fixes were best for local tool affordances: when each tool applies, argument mappings, and side-effect warnings.
- Manual review was useful for live chat because a previous transcript showed the agent could treat an imperative send request too aggressively. v3 tightened that boundary.
- Next improvement: add deterministic tests around live chat confirmation flows, because eval cases catch routing but live multi-round context can still create subtle ambiguity.

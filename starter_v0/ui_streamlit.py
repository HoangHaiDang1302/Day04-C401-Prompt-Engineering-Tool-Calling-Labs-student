from __future__ import annotations

import json
import sys
from importlib.util import find_spec
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import execute_tool_call, tool_results_message
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
load_lab_env(ROOT)

SAMPLE_QUESTIONS = [
    "Tin AI hom nay co gi noi bat?",
    "Tweet moi nhat cua Sam Altman la gi?",
    "Tom tat bai nay giup minh: https://openai.com/research/",
    "Tom tat 5 tweet moi nhat giup minh",
    "Nguon nay co phu hop de trich dan khong: https://arxiv.org/abs/1706.03762",
    "Dang ban tin nay len Telegram giup minh",
]

PROVIDER_DEPENDENCIES = {
    "openrouter": ("openai", "openai"),
    "openai": ("openai", "openai"),
    "anthropic": ("anthropic", "anthropic"),
    "gemini": ("google-genai", "google.genai"),
}


def json_text(value: Any, *, max_chars: int | None = None) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    if max_chars and len(text) > max_chars:
        return text[:max_chars] + "\n...<truncated>"
    return text


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def init_state() -> None:
    st.session_state.setdefault("chat_messages", [])
    st.session_state.setdefault("provider_messages", [])
    st.session_state.setdefault("turns", [])
    st.session_state.setdefault("pending_prompt", None)
    st.session_state.setdefault("pending_clarification", None)
    st.session_state.setdefault("transcript_id", datetime.now().strftime("ui_%Y%m%dT%H%M%S%f"))


def reset_chat() -> None:
    st.session_state.chat_messages = []
    st.session_state.provider_messages = []
    st.session_state.turns = []
    st.session_state.pending_prompt = None
    st.session_state.pending_clarification = None
    st.session_state.transcript_id = datetime.now().strftime("ui_%Y%m%dT%H%M%S%f")


def load_artifacts(version: str) -> tuple[str, list[dict[str, Any]], dict[str, str]]:
    system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    declarations = load_tool_declarations(tools_path)
    artifact_version = build_artifact_version(version, system_prompt_path, tools_path)
    return system_prompt, to_openai_tools(declarations), artifact_version_dict(artifact_version)


def provider_dependency_status(provider_name: str) -> tuple[bool, str, str]:
    package_name, import_name = PROVIDER_DEPENDENCIES[provider_name]
    try:
        installed = find_spec(import_name) is not None
    except ModuleNotFoundError:
        installed = False
    return installed, package_name, import_name


def render_setup_help(provider_name: str) -> None:
    installed, package_name, _ = provider_dependency_status(provider_name)
    with st.expander("Setup check", expanded=not installed):
        st.caption(f"Python: `{sys.executable}`")
        if installed:
            st.success(f"`{package_name}` is installed")
            return

        st.warning(f"Missing `{package_name}`")
        st.code(f"{sys.executable} -m pip install -r requirements.txt", language="powershell")
        st.caption("Restart Streamlit after installing.")


def transcript_payload(provider_name: str, model: str | None, artifact: dict[str, str]) -> dict[str, Any]:
    return {
        "transcript_id": st.session_state.transcript_id,
        **artifact,
        "provider": provider_name,
        "model": model,
        "created_at": st.session_state.transcript_id.replace("ui_", ""),
        "updated_at": now_iso(),
        "source": "streamlit_ui",
        "turns": st.session_state.turns,
    }


def save_transcript(provider_name: str, model: str | None, artifact: dict[str, str]) -> Path:
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    path = TRANSCRIPTS_DIR / f"{st.session_state.transcript_id}.transcript.json"
    payload = transcript_payload(provider_name, model, artifact)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def run_agent_turn(
    *,
    user_text: str,
    provider_name: str,
    model: str | None,
    version: str,
    max_tool_rounds: int,
    history_window: int,
) -> tuple[str, list[dict[str, Any]], dict[str, str]]:
    system_prompt, tools, artifact = load_artifacts(version)
    provider = make_provider(provider_name)

    visible_history = st.session_state.provider_messages[-history_window * 2:] if history_window > 0 else []
    messages = [{"role": "system", "content": system_prompt}, *visible_history, {"role": "user", "content": user_text}]

    rounds: list[dict[str, Any]] = []
    all_events: list[dict[str, Any]] = []
    assistant_text = ""

    for round_index in range(1, max_tool_rounds + 1):
        response = provider.complete(messages, tools, model=model, temperature=0.0)
        calls = response.tool_calls
        round_record: dict[str, Any] = {
            "round": round_index,
            "assistant_text": response.text,
            "tool_calls": [{"name": call.name, "args": call.args} for call in calls],
            "tool_results": [],
        }

        if not calls:
            assistant_text = response.text or ""
            rounds.append(round_record)
            break

        round_events = [execute_tool_call(call) for call in calls]
        round_record["tool_results"] = round_events
        rounds.append(round_record)
        all_events.extend(round_events)

        waiting_events = [
            event for event in round_events
            if isinstance(event.get("result"), dict) and event["result"].get("awaiting_user")
        ]
        if waiting_events:
            result = waiting_events[0]["result"]
            assistant_text = result.get("question") or "Please provide the missing information."
            break

        messages.append({
            "role": "assistant",
            "content": "TOOL_CALLS_JSON:\n" + json_text(round_record["tool_calls"]),
        })
        messages.append(tool_results_message(round_events))
    else:
        assistant_text = f"Stopped after {max_tool_rounds} tool rounds. Inspect tool events."

    st.session_state.provider_messages.append({"role": "user", "content": user_text})
    st.session_state.provider_messages.append({"role": "assistant", "content": assistant_text})
    st.session_state.pending_clarification = None
    for event in all_events:
        result = event.get("result")
        if isinstance(result, dict) and result.get("awaiting_user"):
            st.session_state.pending_clarification = {
                "question": result.get("question") or assistant_text,
                "response_type": result.get("response_type", "text"),
                "options": result.get("options", []),
            }
            break

    st.session_state.turns.append({
        "turn_index": len(st.session_state.turns) + 1,
        "started_at": now_iso(),
        "user": user_text,
        "assistant_text": assistant_text,
        "rounds": rounds,
        "tool_events": all_events,
        "ended_at": now_iso(),
    })
    return assistant_text, rounds, artifact


def clarification_reply_text(value: str) -> str:
    pending = st.session_state.get("pending_clarification") or {}
    question = pending.get("question", "")
    if question:
        return f"Tra loi cau hoi truoc: {value}"
    return value


def render_intro() -> None:
    st.markdown(
        """
Ask for AI news, tweets, papers, policies, URLs, or source checks. The agent will choose the right tool, ask for missing details, and show sources when available.
"""
    )


def tool_names(rounds: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for round_item in rounds:
        for call in round_item.get("tool_calls", []):
            name = call.get("name")
            if name and name not in names:
                names.append(name)
    return names


TOOL_LABELS = {
    "clarify": "Asked for confirmation / missing info",
    "lookup": "Searched the web",
    "fetch": "Read a URL",
    "timeline": "Loaded account posts",
    "social_search": "Searched social posts",
    "format": "Formatted results",
    "policy": "Searched internal policy",
    "papers": "Searched academic papers",
    "paper_text": "Read paper text",
    "send": "Sent message",
    "source_audit": "Checked source quality",
}


def render_tool_summary(rounds: list[dict[str, Any]], *, expanded: bool = False) -> None:
    names = tool_names(rounds)
    if not names:
        return
    friendly = [TOOL_LABELS.get(name, name) for name in names]
    st.caption(" • ".join(friendly))
    if st.session_state.get("show_tool_details", False):
        with st.expander("Technical details", expanded=expanded):
            st.json(rounds)


def main() -> None:
    st.set_page_config(page_title="Research Agent Lab", layout="wide")
    init_state()
    st.markdown(
        """
<style>
  .block-container { max-width: 1080px; padding-top: 2rem; }
  div[data-testid="stSidebar"] .stButton button { border-radius: 8px; }
  div[data-testid="stChatMessage"] { padding: 0.75rem 0; }
  .stButton button { min-height: 2.5rem; white-space: normal; text-align: left; }
</style>
""",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Settings")
        provider_name = st.selectbox("Provider", ["openrouter", "openai", "anthropic", "gemini"])
        version = st.selectbox("Version", ["v3", "v2", "v1", "v0"], index=0)
        model_text = st.text_input("Model override", value="", placeholder="Optional")
        model = model_text.strip() or None
        with st.expander("Advanced", expanded=False):
            max_tool_rounds = int(st.number_input("Max tool rounds", min_value=1, max_value=6, value=4))
            history_window = int(st.number_input("History window", min_value=0, max_value=10, value=5))
            st.session_state.show_tool_details = st.checkbox("Show technical tool details", value=False)
        render_setup_help(provider_name)

        if st.button("New chat", use_container_width=True):
            reset_chat()
            st.rerun()

        _, _, artifact = load_artifacts(version)
        st.caption(f"Version evidence: `{artifact['artifact_version']}`")

    st.title("Research Agent Lab")
    render_intro()

    st.markdown("#### Try one")
    cols = st.columns(3)
    for index, sample in enumerate(SAMPLE_QUESTIONS):
        if cols[index % 3].button(sample, key=f"sample_{index}", use_container_width=True):
            st.session_state.pending_prompt = sample
            st.rerun()

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("rounds"):
                render_tool_summary(message["rounds"], expanded=False)

    pending = st.session_state.get("pending_clarification")
    if pending:
        response_type = pending.get("response_type", "text")
        if response_type == "yes_no":
            col_yes, col_no = st.columns([1, 1])
            if col_yes.button("Yes, confirm", type="primary", use_container_width=True):
                st.session_state.pending_prompt = clarification_reply_text("Yes, I confirm.")
                st.rerun()
            if col_no.button("No, cancel", use_container_width=True):
                st.session_state.pending_prompt = clarification_reply_text("No, cancel.")
                st.rerun()
        else:
            with st.form("clarification_form", clear_on_submit=True):
                clarification = st.text_input("Reply with the missing detail")
                submitted = st.form_submit_button("Send reply")
                if submitted and clarification.strip():
                    st.session_state.pending_prompt = clarification_reply_text(clarification.strip())
                    st.rerun()

    prompt = st.chat_input("Ask the agent...")
    if st.session_state.pending_prompt:
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None

    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Running tools..."):
                try:
                    answer, rounds, artifact = run_agent_turn(
                        user_text=prompt,
                        provider_name=provider_name,
                        model=model,
                        version=version,
                        max_tool_rounds=max_tool_rounds,
                        history_window=history_window,
                    )
                    st.markdown(answer)
                    render_tool_summary(rounds, expanded=False)
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": answer,
                        "rounds": rounds,
                    })
                    save_transcript(provider_name, model, artifact)
                except Exception as exc:
                    error_text = f"Error: {type(exc).__name__}: {exc}"
                    st.error(error_text)
                    if "Install live provider dependency first" in str(exc):
                        installed, package_name, _ = provider_dependency_status(provider_name)
                        st.info("Install the provider package in the same Python environment that runs Streamlit.")
                        st.code(f"{sys.executable} -m pip install {package_name}", language="powershell")
                        st.code(f"{sys.executable} -m pip install -r requirements.txt", language="powershell")
                    st.session_state.chat_messages.append({"role": "assistant", "content": error_text})

    st.divider()
    _, _, artifact = load_artifacts(version)
    transcript = transcript_payload(provider_name, model, artifact)
    st.download_button(
        "Download transcript",
        data=json.dumps(transcript, ensure_ascii=False, indent=2, default=str),
        file_name=f"{st.session_state.transcript_id}.transcript.json",
        mime="application/json",
        use_container_width=False,
    )


if __name__ == "__main__":
    main()

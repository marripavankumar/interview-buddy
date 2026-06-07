from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
MEMORY_FILE = ROOT / "interview_memory.json"
HF_CACHE_ROOT = ROOT / ".hf_cache"
os.environ["HF_HOME"] = str(HF_CACHE_ROOT)
os.environ["HF_HUB_CACHE"] = str(HF_CACHE_ROOT / "hub")
os.environ["TRANSFORMERS_CACHE"] = str(HF_CACHE_ROOT / "transformers")

import gradio as gr

from dotenv import load_dotenv

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency
    PdfReader = None  # type: ignore

try:
    import docx
except Exception:  # pragma: no cover - optional dependency
    docx = None  # type: ignore


APP_NAME = os.getenv("APP_NAME", "Interview Buddy")
load_dotenv(ROOT / ".env")
APP_THEME = gr.themes.Soft(
    primary_hue="sky",
    secondary_hue="sky",
    neutral_hue="blue",
)

HF_TOKEN = (os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HF_API_KEY") or "").strip()
HF_CHAT_MODEL = os.getenv("HF_CHAT_MODEL", "microsoft/Phi-3-mini-4k-instruct")
LOCAL_TEXT_MODEL = os.getenv("HF_LOCAL_TEXT_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
HF_WHISPER_MODEL = os.getenv("HF_WHISPER_MODEL", "openai/whisper-base")
DEFAULT_USER_TYPE = os.getenv("DEFAULT_USER_TYPE", "Experienced Professional")
DEFAULT_CAREER_GOAL = os.getenv("DEFAULT_CAREER_GOAL", "Interview preparation")
DEFAULT_CAREER_LEVELS = [item.strip() for item in os.getenv(
    "DEFAULT_CAREER_LEVELS",
    "Student / Intern,Fresher,Experienced Professional,Senior/Managerial",
).split(",") if item.strip()]
CUSTOM_CSS = """
:root {
  --iv-bg: #f7fbff;
  --iv-panel: rgba(255, 255, 255, 0.98);
  --iv-border: rgba(198, 221, 247, 0.95);
  --iv-text: #000000;
  --iv-muted: #334155;
  --iv-accent: #C6DDF7;
  --iv-accent-2: #9cc3ec;
  --iv-glow: rgba(198, 221, 247, 0.28);
}

body {
  background:
    radial-gradient(circle at top left, rgba(198, 221, 247, 0.64), transparent 24%),
    radial-gradient(circle at 85% 12%, rgba(198, 221, 247, 0.36), transparent 22%),
    linear-gradient(180deg, #ffffff 0%, #f4faff 52%, #ffffff 100%);
  color: var(--iv-text);
}

.iv-shell {
  max-width: 1400px;
  margin: 0 auto;
}

.iv-hero {
  padding: 1.2rem 1.4rem;
  border-radius: 24px;
  border: 1px solid var(--iv-border);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.99), rgba(198, 221, 247, 0.28));
  box-shadow: 0 18px 60px rgba(198, 221, 247, 0.42);
  position: relative;
  overflow: hidden;
  animation: iv-fade-up 0.6s ease-out;
}

.iv-hero::after {
  content: "";
  position: absolute;
  inset: auto -10% -60% auto;
  width: 260px;
  height: 260px;
  background: radial-gradient(circle, rgba(198, 221, 247, 0.74), transparent 62%);
  filter: blur(4px);
}

.iv-title {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  flex-wrap: wrap;
}

.iv-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  border: 1px solid rgba(198, 221, 247, 0.95);
  background: rgba(198, 221, 247, 0.58);
  color: #0f172a;
  font-size: 0.82rem;
}

.iv-card, .iv-panel {
  border: 1px solid var(--iv-border) !important;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(198, 221, 247, 0.10)) !important;
  backdrop-filter: blur(18px);
  box-shadow: 0 14px 40px rgba(198, 221, 247, 0.28);
  border-radius: 20px !important;
  color: #000000 !important;
}

.iv-panel {
  animation: iv-fade-up 0.6s ease-out;
}

.iv-chat .message {
  border-radius: 18px !important;
}

.iv-animate {
  animation: iv-float 6s ease-in-out infinite;
}

.iv-gradient-text {
  background: linear-gradient(90deg, #0f172a 0%, #355f8f 42%, #7aa9d6 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.iv-chip {
  display: inline-flex;
  padding: 0.3rem 0.6rem;
  border-radius: 999px;
  border: 1px solid rgba(198, 221, 247, 0.95);
  background: rgba(198, 221, 247, 0.34);
  color: #0f172a;
  font-size: 0.78rem;
  margin: 0.12rem 0.18rem;
}

.iv-soft {
  color: var(--iv-muted);
}

.iv-primary button {
  border-radius: 999px !important;
  transition: transform 180ms ease, box-shadow 180ms ease;
}

.iv-primary button:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(198, 221, 247, 0.36);
}

.gradio-container, .gradio-container * {
  color: #000000;
}

.gradio-container button,
.gradio-container .gr-button,
.gradio-container .gr-button-primary,
.gradio-container .gr-button-secondary,
.gradio-container button span {
  color: #000000 !important;
}

.gradio-container button {
  background: #C6DDF7 !important;
  border-color: #9cc3ec !important;
}

.career-output {
  min-height: 340px !important;
  height: 340px !important;
  max-height: 340px !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  box-sizing: border-box !important;
}

.career-output * {
  color: #000000 !important;
}

@keyframes iv-fade-up {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes iv-float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-4px); }
}
"""


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"active_session_id": None, "sessions": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("active_session_id", None)
        data.setdefault("sessions", {})
        return data
    except Exception:
        return {"active_session_id": None, "sessions": {}}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _short(text: str, limit: int = 24) -> str:
    words = [w for w in text.split() if w]
    if len(words) <= limit:
        return text.strip()
    return " ".join(words[:limit]).strip() + " ..."


def _keywords(text: str, limit: int = 6) -> list[str]:
    stop = {
        "resume", "project", "projects", "experience", "skills", "skill", "using", "with",
        "that", "this", "your", "their", "from", "have", "has", "had", "for", "and",
        "the", "into", "role", "work", "about", "more", "less", "also", "team", "teams",
    }
    words = re.findall(r"[A-Za-z0-9+.#-]{4,}", text.lower())
    counts: dict[str, int] = {}
    for word in words:
        if word in stop:
            continue
        counts[word] = counts.get(word, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [w.title() for w, _ in ordered[:limit]]


def _extract_text_from_file(file_obj: Any) -> str:
    if file_obj is None:
        return ""
    path = Path(getattr(file_obj, "name", str(file_obj)))
    suffix = path.suffix.lower()
    try:
        if suffix in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf" and PdfReader is not None:
            reader = PdfReader(str(path))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        if suffix in {".docx", ".doc"} and docx is not None:
            document = docx.Document(str(path))
            return "\n".join(para.text for para in document.paragraphs)
    except Exception:
        pass
    return ""


def _fallback_opening(context: dict[str, Any]) -> str:
    focus = context.get("target_role") or context.get("topic") or context.get("domain") or "your background"
    return (
        f"Hello, I'm your interview coach. Let's start with a question about {focus}. "
        f"Can you walk me through a concrete example that shows your strengths?"
    )


def _fallback_followup(context: dict[str, Any], user_text: str, turn: int) -> str:
    focus = context.get("target_role") or context.get("topic") or context.get("domain") or "the role"
    terms = ", ".join(_keywords(user_text, 3)) or focus
    score = min(9.5, max(4.0, round(len(user_text.split()) / 18, 1)))
    feedback = (
        f"Score: {score}/10\n\n"
        f"Feedback: You are on the right track. Strengthen the answer by tying it back to {terms} and by adding one measurable result.\n\n"
        "Strengths:\n"
        "- Clear attempt to answer the question\n"
        "- Relevant professional context\n"
        "- Professional tone\n\n"
        "Improvements:\n"
        "- Add specific metrics\n"
        "- Name the exact action you took\n"
        "- Finish with the outcome and lesson learned\n\n"
    )
    if turn >= 5:
        return feedback + "That was a solid session. Thanks for practicing with me."
    return feedback + f"Next question: Tell me about a time you used {terms} to solve a meaningful problem."


def _fallback_tool_response(kind: str, context: dict[str, Any], text: str) -> str:
    terms = _keywords(text, 5) or [context.get("user_type", "candidate")]
    if kind == "resume":
        role = context.get("target_role") or "target role"
        return (
            f"ATS Score: {min(94, max(42, 50 + len(text.split()) // 18))}/100\n\n"
            f"Role Fit: This resume is a solid starting point for {role}, but it should surface more role-specific keywords such as {', '.join(terms)}.\n\n"
            "Clarity: Use shorter bullets and stronger action verbs.\n"
            "Structure: Group skills, projects, and outcomes more clearly.\n"
        "Grammar: Tighten wording for a more confident tone.\n\n"
            "Enhanced Summary:\n"
            f"Results-oriented {context.get('user_type', 'candidate')} targeting {role}. Highlights strengths in {', '.join(terms)} with ownership, impact, and measurable outcomes."
        )
    if kind == "jobs":
        items = [
            f"{term} Specialist - A practical role aligned with strengths in {term.lower()}."
            for term in terms[:5]
        ]
        return "Suggested Roles:\n" + "\n".join(f"- {item}" for item in items)
    if kind == "prep":
        company = context.get("company") or "the company"
        role = context.get("target_role") or "the role"
        return (
            f"Company Insights: {company} will likely value practical ownership, clear communication, and role-specific depth from a {context.get('user_type', 'candidate')} candidate.\n\n"
            f"Role Skills: {', '.join(terms)}\n\n"
            f"Common Questions:\n- Why do you want to work at {company}?\n- How would you contribute to the {role} team in your first 90 days?\n- Tell me about a time you solved a difficult problem with limited context.\n\n"
            f"Resources:\n- {company} careers overview\n- {role} interview preparation"
        )
    return "No response available."


def _fallback_question_pack(text: str, user_type: str, tech_count: int, nontech_count: int) -> dict[str, list[str]]:
    skills = _keywords(text, 7)
    if not skills:
        skills = ["Communication", "Problem Solving", "Ownership", "Adaptability", "Collaboration"]
    focus = ", ".join(skills[:3]) or user_type
    return {
        "skills": skills,
        "technicalQuestions": [
            f"Technical question {idx + 1}: Tell me about a time you used {focus} to solve a meaningful problem."
            for idx in range(max(tech_count, 0))
        ],
        "nonTechnicalQuestions": [
            f"Behavioral question {idx + 1}: Describe a situation where you demonstrated {focus} as a {user_type}."
            for idx in range(max(nontech_count, 0))
        ],
    }


def _format_question_pack(pack: dict[str, list[str]]) -> str:
    skills = pack.get("skills", [])
    technical = pack.get("technicalQuestions", [])
    non_technical = pack.get("nonTechnicalQuestions", [])
    sections = [
        "### Extracted Key Skills",
        "\n".join(f"- {skill}" for skill in skills) if skills else "- No strong skills detected yet.",
        "",
        "### Technical Questions",
        "\n".join(f"- {question}" for question in technical) if technical else "- No technical questions requested.",
        "",
        "### Non-Technical Questions",
        "\n".join(f"- {question}" for question in non_technical) if non_technical else "- No non-technical questions requested.",
    ]
    return "\n".join(sections).strip()


def _fallback_qna_answer(question: str, context_text: str) -> str:
    terms = ", ".join(_keywords(context_text, 4)) or "your background"
    return (
        f"A strong answer should connect {terms} to the question \"{question}\".\n\n"
        "Use a compact STAR structure:\n"
        "- Situation: set the context\n"
        "- Task: explain the objective\n"
        "- Action: describe what you did\n"
        "- Result: end with a measurable outcome"
    )


def _resume_score(text: str) -> int:
    return min(94, max(42, 50 + len(text.split()) // 18))


def _format_resume_review(
    resume_text: str,
    user_type: str,
    target_role: str,
    analysis_text: str | None = None,
) -> str:
    terms = _keywords(resume_text, 5)
    score = _resume_score(resume_text)
    focus = ", ".join(terms) if terms else "impact, ownership, and role-specific keywords"
    analysis_block = analysis_text.strip() if analysis_text and analysis_text.strip() else (
        "The resume is a solid starting point, but it should be tightened with clearer metrics, stronger verbs, and role-specific keywords."
    )
    return (
        f"### ATS Score\n"
        f"**{score}/100**\n\n"
        f"### Feedback\n"
        f"{analysis_block}\n\n"
        f"### Key Improvements\n"
        f"- Surface more role-specific keywords for **{target_role or 'the target role'}**\n"
        f"- Strengthen measurable impact and outcomes\n"
        f"- Make bullets shorter, clearer, and more action-oriented\n\n"
        f"### Enhanced Resume Snippet\n"
        f"Results-oriented {user_type} targeting {target_role or 'the role'}. Highlights strengths in {focus} with ownership, impact, and measurable outcomes."
    )


@dataclass
class SessionState:
    session_id: str
    user_name: str
    user_type: str
    goal: str
    target_role: str
    domain: str
    topic: str
    difficulty: str
    resume_text: str
    summary: str
    facts: list[str]
    turns: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SessionState":
        return SessionState(
            session_id=data.get("session_id") or str(uuid.uuid4()),
            user_name=data.get("user_name", "anonymous"),
            user_type=data.get("user_type", DEFAULT_USER_TYPE),
            goal=data.get("goal", DEFAULT_CAREER_GOAL),
            target_role=data.get("target_role", ""),
            domain=data.get("domain", ""),
            topic=data.get("topic", ""),
            difficulty=data.get("difficulty", "standard"),
            resume_text=data.get("resume_text", ""),
            summary=data.get("summary", ""),
            facts=list(data.get("facts", [])),
            turns=list(data.get("turns", [])),
        )


class InterviewFlowCoach:
    def __init__(self) -> None:
        self.memory_path = MEMORY_FILE
        self.store = _read_json(self.memory_path)
        self._chat_client: InferenceClient | None = None  # type: ignore[assignment]
        self._text_pipe = None
        self._text_error = ""
        self._whisper_pipe = None

    def _chat(self) -> InferenceClient | None:
        if not HF_TOKEN:
            return None
        if self._chat_client is None:
            try:
                from huggingface_hub import InferenceClient
            except Exception:
                return None
            self._chat_client = InferenceClient(model=HF_CHAT_MODEL, token=HF_TOKEN, provider="hf-inference")
        return self._chat_client

    def _text_model(self):
        if self._text_pipe is not None:
            return self._text_pipe
        try:
            from transformers import pipeline
        except Exception:
            return None
        try:
            self._text_pipe = pipeline(
                "text-generation",
                model=LOCAL_TEXT_MODEL,
                token=HF_TOKEN or None,
            )
            return self._text_pipe
        except Exception as exc:
            self._text_pipe = None
            self._text_error = str(exc)
            return None

    def _generate_local_text(self, prompt: str, max_new_tokens: int = 256) -> str:
        pipe = self._text_model()
        if pipe is None:
            return ""
        try:
            result = pipe(
                prompt,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                return_full_text=False,
                truncation=True,
            )
            if isinstance(result, list) and result:
                item = result[0]
                if isinstance(item, dict):
                    return str(item.get("generated_text", "")).strip()
                return str(item).strip()
            if isinstance(result, dict):
                return str(result.get("generated_text", "")).strip()
            return str(result).strip()
        except Exception:
            return ""

    def _whisper(self):
        try:
            from transformers import pipeline
        except Exception:
            return None
        try:
            self._whisper_pipe = pipeline(
                "automatic-speech-recognition",
                model=HF_WHISPER_MODEL,
                token=HF_TOKEN or None,
            )
            return self._whisper_pipe
        except Exception:
            self._whisper_pipe = None
            return None

    def transcribe(self, audio_file: Any) -> str:
        if not audio_file:
            return "No audio file was provided. Please upload or record a clip."
        pipe = self._whisper()
        if pipe is None:
            return "Voice transcription is unavailable right now. Please type the prompt manually."
        try:
            import numpy as np

            audio_array = None
            sampling_rate = None

            if isinstance(audio_file, dict):
                audio_array = audio_file.get("array") or audio_file.get("data")
                sampling_rate = audio_file.get("sampling_rate") or audio_file.get("sample_rate")
                if audio_array is None:
                    candidate = audio_file.get("path") or audio_file.get("name") or audio_file.get("filepath")
                    if candidate:
                        path = Path(str(candidate))
                        if path.exists():
                            try:
                                import soundfile as sf
                                audio_array, sampling_rate = sf.read(str(path), dtype="float32")
                            except Exception:
                                try:
                                    import torchaudio
                                    waveform, sampling_rate = torchaudio.load(str(path))
                                    audio_array = waveform.numpy()
                                except Exception as load_exc:
                                    detail = str(load_exc).strip()
                                    if detail:
                                        return f"Voice transcription failed. {detail}"
                                    return "Voice transcription failed. Please try again or type the prompt manually."

            elif isinstance(audio_file, (list, tuple)) and len(audio_file) == 2:
                first, second = audio_file
                if isinstance(first, (int, float)):
                    sampling_rate, audio_array = int(first), second
                elif isinstance(second, (int, float)):
                    audio_array, sampling_rate = first, int(second)
            else:
                candidate = getattr(audio_file, "path", None) or getattr(audio_file, "name", None) or getattr(audio_file, "filepath", None)
                if candidate:
                    path = Path(str(candidate))
                    if path.exists():
                        try:
                            import soundfile as sf
                            audio_array, sampling_rate = sf.read(str(path), dtype="float32")
                        except Exception:
                            try:
                                import torchaudio
                                waveform, sampling_rate = torchaudio.load(str(path))
                                audio_array = waveform.numpy()
                            except Exception as load_exc:
                                detail = str(load_exc).strip()
                                if detail:
                                    return f"Voice transcription failed. {detail}"
                                return "Voice transcription failed. Please try again or type the prompt manually."

            if audio_array is None or sampling_rate is None:
                return "Voice transcription failed. Please record or upload a clip again."

            audio_array = np.asarray(audio_array, dtype="float32")
            if audio_array.ndim > 1:
                if audio_array.shape[0] <= 8 and audio_array.shape[0] < audio_array.shape[1]:
                    audio_array = audio_array.mean(axis=0)
                else:
                    audio_array = audio_array.mean(axis=1)

            result = pipe(
                {"array": audio_array, "sampling_rate": sampling_rate},
                generate_kwargs={"task": "translate", "language": "en"},
            )
            if isinstance(result, dict):
                transcript = str(result.get("text", "")).strip()
            else:
                transcript = str(getattr(result, "text", result)).strip()
            if not transcript:
                return "Voice transcription failed. Please try again or type the prompt manually."
            return transcript
        except Exception as exc:
            detail = str(exc).strip()
            if detail:
                return f"Voice transcription failed. {detail}"
            return "Voice transcription failed. Please try again or type the prompt manually."

    def new_session(self, profile: dict[str, Any]) -> SessionState:
        return SessionState(
            session_id=str(uuid.uuid4()),
            user_name=profile.get("user_name", "anonymous"),
            user_type=profile.get("user_type", DEFAULT_USER_TYPE),
            goal=profile.get("goal", DEFAULT_CAREER_GOAL),
            target_role=profile.get("target_role", ""),
            domain=profile.get("domain", ""),
            topic=profile.get("topic", ""),
            difficulty=profile.get("difficulty", "standard"),
            resume_text=profile.get("resume_text", ""),
            summary="",
            facts=[],
            turns=[],
        )

    def load_session(self, session_id: str | None) -> SessionState:
        if session_id and session_id in self.store.get("sessions", {}):
            return SessionState.from_dict(self.store["sessions"][session_id])
        active = self.store.get("active_session_id")
        if active and active in self.store.get("sessions", {}):
            return SessionState.from_dict(self.store["sessions"][active])
        session = self.new_session({})
        self._persist_session(session)
        self.store["active_session_id"] = session.session_id
        _write_json(self.memory_path, self.store)
        return session

    def _persist_session(self, session: SessionState) -> None:
        self.store.setdefault("sessions", {})
        self.store["sessions"][session.session_id] = session.to_dict()
        self.store["active_session_id"] = session.session_id
        _write_json(self.memory_path, self.store)

    def _memory_snapshot(self, session: SessionState) -> str:
        facts = session.facts or _keywords(session.resume_text + " " + session.summary, 8)
        recent = session.turns[-6:]
        recent_lines = "\n".join(
            f"- {item['role'].title()}: {_short(item['content'], 16)}" for item in recent
        ) or "- No turns yet."
        return (
            f"Session: {session.session_id}\n"
            f"User: {session.user_name} ({session.user_type})\n"
            f"Goal: {session.goal}\n"
            f"Summary: {session.summary or 'No summary yet.'}\n"
            f"Facts: {', '.join(facts) if facts else 'None yet.'}\n"
            f"Recent:\n{recent_lines}"
        )

    def _turns_to_chatbot(self, turns: list[dict[str, str]]) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        pending_user: str | None = None
        for turn in turns:
            role = turn.get("role")
            content = turn.get("content", "")
            if role == "user":
                pending_user = content
            elif role == "assistant":
                pairs.append((pending_user or "", content))
                pending_user = None
        if pending_user is not None:
            pairs.append((pending_user, ""))
        return pairs

    def _build_messages(self, session: SessionState, user_input: str, mode: str) -> list[dict[str, str]]:
        memory_context = self._memory_snapshot(session)
        system_prompt = f"""
You are Interview Buddy, a strict but fair interview simulator and career coach.
Mode: {mode}
Candidate type: {session.user_type}
Difficulty: {session.difficulty}
Goal: {session.goal}
Target role: {session.target_role or 'not specified'}
Domain: {session.domain or 'not specified'}
Topic: {session.topic or 'not specified'}

Use the memory context below and stay grounded in it.
If this is the first turn, introduce yourself briefly and ask the first interview question.
If the candidate answered a question, provide concise feedback, then ask the next relevant question.
Keep the tone polished, helpful, and energetic.
Prefer short sections and bullet points when useful.

Memory context:
{memory_context}
""".strip()

        messages = [{"role": "system", "content": system_prompt}]
        for turn in session.turns[-10:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
        if user_input:
            messages.append({"role": "user", "content": user_input})
        return messages

    def _messages_to_prompt(self, messages: list[dict[str, str]]) -> str:
        lines = []
        for message in messages:
            role = message.get("role", "user").upper()
            content = message.get("content", "").strip()
            if content:
                lines.append(f"{role}: {content}")
        lines.append("ASSISTANT:")
        return "\n\n".join(lines)

    def _stream_tokens(self, text: str, delay: float = 0.012):
        buffer = ""
        for token in re.split(r"(\s+)", text):
            buffer += token
            yield buffer
            time.sleep(delay)

    def _local_reply(self, session: SessionState, user_input: str, mode: str) -> str:
        if not session.turns:
            return _fallback_opening(session.to_dict())
        return _fallback_followup(session.to_dict(), user_input, len(session.turns) // 2 + 1)

    def stream_chat(
        self,
        user_input: str,
        session: SessionState,
        mode: str,
    ):
        messages = self._build_messages(session, user_input, mode)
        assistant_text = ""
        local_prompt = self._messages_to_prompt(messages) + "\n\nWrite the next assistant message in clear English."
        local_reply = self._generate_local_text(local_prompt, max_new_tokens=220)
        if local_reply.strip():
            for partial in self._stream_tokens(local_reply):
                assistant_text = partial
                yield assistant_text
            return assistant_text
        client = self._chat()
        if client is not None:
            try:
                stream = client.chat.completions.create(
                    model=HF_CHAT_MODEL,
                    messages=messages,
                    stream=True,
                    max_tokens=500,
                    temperature=0.7,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk and chunk.choices else None
                    if delta:
                        assistant_text += delta
                        yield assistant_text
                if assistant_text.strip():
                    return assistant_text
            except Exception:
                assistant_text = ""

        fallback = self._local_reply(session, user_input, mode)
        for partial in self._stream_tokens(fallback):
            assistant_text = partial
            yield assistant_text
        return assistant_text

    def _update_memory(self, session: SessionState, user_input: str, assistant_text: str) -> None:
        session.turns.append({"role": "user", "content": user_input})
        session.turns.append({"role": "assistant", "content": assistant_text})
        keywords = _keywords(session.resume_text + " " + user_input + " " + assistant_text, 10)
        session.facts = sorted(set(session.facts + keywords))
        session.summary = (
            f"{session.goal}. Current focus: {', '.join(session.facts[:6]) if session.facts else 'general interview prep'}."
        )
        self._persist_session(session)

    def reset_session(self, profile: dict[str, Any]) -> tuple[list[tuple[str, str]], SessionState, str, str]:
        session = self.new_session(profile)
        self._persist_session(session)
        welcome = _fallback_opening(session.to_dict())
        session.turns.append({"role": "assistant", "content": welcome})
        session.summary = "Interview session started."
        self._persist_session(session)
        return [("", welcome)], session, self._memory_snapshot(session), "Ready."

    def handle_start(
        self,
        user_name: str,
        user_type: str,
        goal: str,
        target_role: str,
        domain: str,
        topic: str,
        difficulty: str,
        resume_text: str,
    ):
        profile = {
            "user_name": user_name or "anonymous",
            "user_type": user_type or DEFAULT_USER_TYPE,
            "goal": goal or DEFAULT_CAREER_GOAL,
            "target_role": target_role,
            "domain": domain,
            "topic": topic,
            "difficulty": difficulty,
            "resume_text": resume_text,
        }
        session = self.new_session(profile)
        self._persist_session(session)
        stream = self.stream_chat("", session, "opening")

        chatbot: list[tuple[str, str]] = []
        assistant = ""
        for partial in stream:
            assistant = partial
            yield chatbot + [("", assistant)], session, self._memory_snapshot(session), "Streaming opening question..."

        session.turns.append({"role": "assistant", "content": assistant})
        session.summary = "Interview session started."
        self._persist_session(session)
        yield self._turns_to_chatbot(session.turns), session, self._memory_snapshot(session), "Interview ready."

    def handle_user_message(
        self,
        user_message: str,
        session: SessionState,
        mode: str,
    ):
        if not user_message.strip():
            yield [("", "Please type a prompt first.")], session, self._memory_snapshot(session), "Waiting for input."
            return
        chatbot = self._turns_to_chatbot(session.turns)
        chatbot.append((user_message, ""))
        assistant = ""
        for partial in self.stream_chat(user_message, session, mode):
            assistant = partial
            yield chatbot[:-1] + [(user_message, assistant)], session, self._memory_snapshot(session), "Streaming response..."

        self._update_memory(session, user_message, assistant)
        yield self._turns_to_chatbot(session.turns), session, self._memory_snapshot(session), "Saved to memory."

    def analyze_resume(
        self,
        resume_text: str,
        target_role: str,
        user_type: str,
        session: SessionState,
    ):
        if not resume_text.strip() or not target_role.strip():
            yield "Please provide resume text and a target role.", session, self._memory_snapshot(session)
            return
        context = {
            "user_type": user_type,
            "target_role": target_role,
            "resume_text": resume_text,
        }
        prompt = f"""
Act as an ATS auditor and career coach.
Analyze the resume for a {user_type} targeting {target_role}.
Return concise feedback with these sections:
1) ATS score out of 100
2) clarity, structure, grammar, and role-fit feedback
3) an improved summary paragraph

Resume:
---
{resume_text}
---
""".strip()
        messages = [{"role": "system", "content": "You are a concise resume reviewer."}, {"role": "user", "content": prompt}]
        output = ""
        analysis_text = ""
        local_analysis = self._generate_local_text(
            f"{prompt}\n\nWrite a concise ATS review with score, feedback, key improvements, and an improved summary paragraph.",
            max_new_tokens=220,
        )
        if local_analysis.strip():
            output = _format_resume_review(resume_text, user_type, target_role, local_analysis)
            for partial in self._stream_tokens(output):
                yield partial, session, self._memory_snapshot(session)
            return
        client = self._chat()
        if client is not None:
            try:
                stream = client.chat.completions.create(
                    model=HF_CHAT_MODEL,
                    messages=messages,
                    stream=True,
                    max_tokens=450,
                    temperature=0.4,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk and chunk.choices else None
                    if delta:
                        analysis_text += delta
                        output = _format_resume_review(resume_text, user_type, target_role, analysis_text)
                        yield output, session, self._memory_snapshot(session)
                if analysis_text.strip():
                    output = _format_resume_review(resume_text, user_type, target_role, analysis_text)
                    yield output, session, self._memory_snapshot(session)
                    return
            except Exception:
                analysis_text = ""
        fallback = _format_resume_review(resume_text, user_type, target_role, None)
        for partial in self._stream_tokens(fallback):
            output = partial
            yield output, session, self._memory_snapshot(session)

    def find_jobs(
        self,
        text: str,
        user_type: str,
        session: SessionState,
    ):
        if not text.strip():
            yield "Please provide a resume or a domain/topic description.", session, self._memory_snapshot(session)
            return
        context = {"user_type": user_type}
        messages = [
            {"role": "system", "content": "You suggest relevant job titles and short descriptions."},
            {"role": "user", "content": f"Suggest 5 job titles for a {user_type} based on this text:\n\n{text}"},
        ]
        output = ""
        local_jobs = self._generate_local_text(
            f"Suggest 5 job titles for a {user_type} based on the text below. Return a short markdown list with one line per role and a brief explanation.\n\n{text}",
            max_new_tokens=180,
        )
        if local_jobs.strip():
            for partial in self._stream_tokens(local_jobs):
                output = partial
                yield output, session, self._memory_snapshot(session)
            return
        client = self._chat()
        if client is not None:
            try:
                stream = client.chat.completions.create(
                    model=HF_CHAT_MODEL,
                    messages=messages,
                    stream=True,
                    max_tokens=350,
                    temperature=0.5,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk and chunk.choices else None
                    if delta:
                        output += delta
                        yield output, session, self._memory_snapshot(session)
                if output.strip():
                    return
            except Exception:
                output = ""
        fallback = _fallback_tool_response("jobs", context, text)
        for partial in self._stream_tokens(fallback):
            output = partial
            yield output, session, self._memory_snapshot(session)

    def interview_prep(
        self,
        company: str,
        role: str,
        user_type: str,
        session: SessionState,
    ):
        if not company.strip() or not role.strip():
            yield "Please provide both a company and role.", session, self._memory_snapshot(session)
            return
        context = {"company": company, "target_role": role, "user_type": user_type}
        messages = [
            {"role": "system", "content": "You create company-specific interview prep guides."},
            {"role": "user", "content": f"Create a concise prep guide for {user_type} interviewing for {role} at {company}."},
        ]
        output = ""
        local_prep = self._generate_local_text(
            f"Create a concise prep guide for {user_type} interviewing for {role} at {company}. Include company insights, role skills, common questions, and resources.",
            max_new_tokens=180,
        )
        if local_prep.strip():
            for partial in self._stream_tokens(local_prep):
                output = partial
                yield output, session, self._memory_snapshot(session)
            return
        client = self._chat()
        if client is not None:
            try:
                stream = client.chat.completions.create(
                    model=HF_CHAT_MODEL,
                    messages=messages,
                    stream=True,
                    max_tokens=350,
                    temperature=0.5,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk and chunk.choices else None
                    if delta:
                        output += delta
                        yield output, session, self._memory_snapshot(session)
                if output.strip():
                    return
            except Exception:
                output = ""
        fallback = _fallback_tool_response("prep", context, "")
        for partial in self._stream_tokens(fallback):
            output = partial
            yield output, session, self._memory_snapshot(session)

    def generate_questions(
        self,
        source_text: str,
        user_type: str,
        tech_count: int,
        nontech_count: int,
        session: SessionState,
    ):
        if not source_text.strip():
            yield "Please provide a resume or job description first.", session, self._memory_snapshot(session), [], None
            return
        context = {"user_type": user_type}
        prompt = f"""
Based on the following text and the candidate level, extract the top skills and generate interview questions.

Candidate Level: {user_type}
Technical Questions: {tech_count}
Non-Technical Questions: {nontech_count}

Text:
---
{source_text}
---

Return a concise markdown response with these sections:
1. Extracted Key Skills
2. Technical Questions
3. Non-Technical Questions
""".strip()
        messages = [
            {"role": "system", "content": "You generate concise interview question packs."},
            {"role": "user", "content": prompt},
        ]
        output = ""
        local_pack = self._generate_local_text(
            f"{prompt}\n\nReturn markdown with these exact sections: Extracted Key Skills, Technical Questions, Non-Technical Questions. Use bullet points that start with '- '.",
            max_new_tokens=250,
        )
        if local_pack.strip():
            for partial in self._stream_tokens(local_pack):
                output = partial
                yield output, session, self._memory_snapshot(session), [], source_text
            questions = [line.lstrip("- ").strip() for line in output.splitlines() if line.strip().startswith("- ")]
            if questions:
                session.facts = sorted(set(session.facts + _keywords(source_text + " " + output, 10)))
                session.summary = f"Generated interview questions for {user_type}."
                self._persist_session(session)
                yield output, session, self._memory_snapshot(session), questions, source_text
                return
        client = self._chat()
        if client is not None:
            try:
                stream = client.chat.completions.create(
                    model=HF_CHAT_MODEL,
                    messages=messages,
                    stream=True,
                    max_tokens=450,
                    temperature=0.55,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk and chunk.choices else None
                    if delta:
                        output += delta
                        yield output, session, self._memory_snapshot(session), [], source_text
                if output.strip():
                    session.facts = sorted(set(session.facts + _keywords(source_text + " " + output, 10)))
                    session.summary = f"Generated interview questions for {user_type}."
                    self._persist_session(session)
                    questions = [line.lstrip("- ").strip() for line in output.splitlines() if line.strip().startswith("- ")]
                    yield output, session, self._memory_snapshot(session), questions, source_text
                    return
            except Exception:
                output = ""
        pack = _fallback_question_pack(source_text, user_type, tech_count, nontech_count)
        fallback = _format_question_pack(pack)
        for partial in self._stream_tokens(fallback):
            output = partial
            yield output, session, self._memory_snapshot(session), [], source_text
        session.facts = sorted(set(session.facts + _keywords(source_text + " " + output, 10)))
        session.summary = f"Generated interview questions for {user_type}."
        self._persist_session(session)
        questions = pack.get("technicalQuestions", []) + pack.get("nonTechnicalQuestions", [])
        yield output, session, self._memory_snapshot(session), questions, source_text

    def generate_answer(
        self,
        question: str,
        context_text: str,
        session: SessionState,
    ):
        if not question.strip() or not context_text.strip():
            yield "Please provide both a question and context text.", session, self._memory_snapshot(session)
            return
        messages = [
            {"role": "system", "content": "You write concise interview answers."},
            {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion:\n{question}\n\nWrite a concise answer and keep it professional."},
        ]
        output = ""
        local_answer = self._generate_local_text(
            f"Write a concise professional interview answer in English.\n\nContext:\n{context_text}\n\nQuestion:\n{question}",
            max_new_tokens=160,
        )
        if local_answer.strip():
            for partial in self._stream_tokens(local_answer):
                output = partial
                yield output, session, self._memory_snapshot(session)
            return
        client = self._chat()
        if client is not None:
            try:
                stream = client.chat.completions.create(
                    model=HF_CHAT_MODEL,
                    messages=messages,
                    stream=True,
                    max_tokens=250,
                    temperature=0.55,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk and chunk.choices else None
                    if delta:
                        output += delta
                        yield output, session, self._memory_snapshot(session)
                if output.strip():
                    return
            except Exception:
                output = ""
        fallback = _fallback_qna_answer(question, context_text)
        for partial in self._stream_tokens(fallback):
            output = partial
            yield output, session, self._memory_snapshot(session)

    def modify_answer(
        self,
        question: str,
        answer: str,
        modification_type: str,
        session: SessionState,
    ):
        if not answer.strip():
            yield "Generate an answer first.", session, self._memory_snapshot(session)
            return
        modifier = "make it more detailed" if modification_type == "elaborate" else "make it more concise"
        messages = [
            {"role": "system", "content": "You refine interview answers."},
            {"role": "user", "content": f"Question:\n{question}\n\nAnswer:\n{answer}\n\nPlease {modifier}."},
        ]
        output = ""
        local_refinement = self._generate_local_text(
            f"Refine this interview answer in English and {modifier}.\n\nQuestion:\n{question}\n\nAnswer:\n{answer}",
            max_new_tokens=120,
        )
        if local_refinement.strip():
            for partial in self._stream_tokens(local_refinement):
                output = partial
                yield output, session, self._memory_snapshot(session)
            return
        client = self._chat()
        if client is not None:
            try:
                stream = client.chat.completions.create(
                    model=HF_CHAT_MODEL,
                    messages=messages,
                    stream=True,
                    max_tokens=250,
                    temperature=0.5,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk and chunk.choices else None
                    if delta:
                        output += delta
                        yield output, session, self._memory_snapshot(session)
                if output.strip():
                    return
            except Exception:
                output = ""
        if modification_type == "elaborate":
            fallback = f"{answer.strip()} Add one concrete example, the action you took, and the measurable result."
        else:
            fallback = _short(answer.strip(), 40)
        for partial in self._stream_tokens(fallback):
            output = partial
            yield output, session, self._memory_snapshot(session)


coach = InterviewFlowCoach()


def _ensure_session(state: SessionState | dict[str, Any] | None) -> SessionState:
    if isinstance(state, SessionState):
        return state
    if isinstance(state, dict) and state:
        return SessionState.from_dict(state)
    return coach.load_session(None)


def build_app() -> gr.Blocks:
    with gr.Blocks(title=APP_NAME) as demo:
        gr.HTML(
            f"""
            <div class="iv-shell">
              <div class="iv-hero iv-animate">
                <div class="iv-title">
                  <div style="width:52px;height:52px;border-radius:16px;background:linear-gradient(135deg,#ffffff,#C6DDF7);display:grid;place-items:center;font-weight:800;color:#0f172a;">IV</div>
                  <div>
                    <div class="iv-badge">Streaming Gradio + Hugging Face</div>
                    <h1 class="iv-gradient-text" style="margin:0.25rem 0 0;font-size:2.2rem;">{APP_NAME}</h1>
                    <p class="iv-soft" style="margin:0.35rem 0 0;">Text-based interview coaching, memory-aware guidance, and streaming AI responses in one polished workspace.</p>
                  </div>
                </div>
              </div>
            </div>
            """
        )

        session_state = gr.State(coach.load_session(None).to_dict())

        with gr.Tabs():
            with gr.Tab("Interview Studio"):
                with gr.Row(equal_height=True):
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(label="Interview Thread", height=520, elem_classes=["iv-card", "iv-chat"])
                        status = gr.Markdown("Ready.", elem_classes=["iv-soft"])
                        with gr.Row():
                            user_text = gr.Textbox(
                                label="Answer / Prompt",
                                placeholder="Type your answer or ask for guidance...",
                                lines=3,
                                scale=3,
                            )
                        with gr.Row():
                            audio = gr.Audio(
                                label="Voice prompt",
                                sources=["microphone", "upload"],
                                type="numpy",
                                format="wav",
                                scale=3,
                            )
                        transcribed = gr.Textbox(label="Transcribed voice", placeholder="Transcription will appear here.", lines=2)
                        with gr.Row(elem_classes=["iv-primary"]):
                            start_btn = gr.Button("Start / Reset Session", variant="primary")
                            transcribe_btn = gr.Button("Transcribe Voice", variant="secondary")
                            send_btn = gr.Button("Send Answer", variant="primary")
                    with gr.Column(scale=2):
                        with gr.Group(elem_classes=["iv-panel"]):
                            user_name = gr.Textbox(label="Name", value="anonymous")
                            user_type = gr.Dropdown(
                                DEFAULT_CAREER_LEVELS,
                                value=DEFAULT_USER_TYPE,
                                label="Career Level",
                            )
                            goal = gr.Textbox(label="Goal", value=DEFAULT_CAREER_GOAL)
                            difficulty = gr.Dropdown(["standard", "challenging", "expert"], value="standard", label="Difficulty")
                            target_role = gr.Textbox(label="Target Role", placeholder="e.g. Software Engineer")
                            domain = gr.Textbox(label="Domain", placeholder="e.g. Backend Systems")
                            topic = gr.Textbox(label="Topic", placeholder="e.g. Distributed systems")
                            resume_text = gr.Textbox(label="Resume / Background", lines=8, placeholder="Paste resume text or a short background summary here.")
                            resume_file = gr.File(label="Upload Resume File", file_count="single", file_types=[".txt", ".md", ".pdf", ".docx"])
                        memory_view = gr.Textbox(label="Memory Vault", lines=9, interactive=False, elem_classes=["iv-panel"])
                        memory_note = gr.Markdown("Memory is saved locally in `voice_interview_memory.json`.", elem_classes=["iv-soft"])

            with gr.Tab("Q&A Generator"):
                with gr.Row(equal_height=True):
                    with gr.Column(scale=3):
                        qna_mode = gr.Radio(["Resume", "Job Description"], value="Resume", label="Input Type")
                        qna_file = gr.File(label="Upload Resume / Text File", file_count="single", file_types=[".txt", ".md", ".pdf", ".docx"])
                        qna_text = gr.Textbox(
                            label="Resume or Job Description Text",
                            lines=12,
                            placeholder="Upload a resume or paste a job description to generate questions and model answers.",
                        )
                        with gr.Row():
                            tech_count = gr.Slider(0, 15, value=5, step=1, label="Technical Questions")
                            nontech_count = gr.Slider(0, 10, value=5, step=1, label="Non-Technical Questions")
                        qna_generate_btn = gr.Button("Generate Questions", variant="primary")
                        qna_output = gr.Markdown(label="Generated Questions", elem_classes=["iv-panel"])
                    with gr.Column(scale=2):
                        qna_question = gr.Dropdown(label="Question to Answer", choices=[], value=None)
                        qna_answer = gr.Textbox(label="Model Answer", lines=12, placeholder="Generate a model answer for one selected question.")
                        with gr.Row(elem_classes=["iv-primary"]):
                            qna_answer_btn = gr.Button("Generate Answer", variant="primary")
                            qna_elaborate_btn = gr.Button("Elaborate", variant="secondary")
                            qna_shorten_btn = gr.Button("Shorten", variant="secondary")

            with gr.Tab("Career Tools"):
                with gr.Row(equal_height=True):
                    with gr.Column():
                        resume_input = gr.Textbox(label="Resume text", lines=12, placeholder="Paste a resume or candidate background here.")
                        role_input = gr.Textbox(label="Target role", placeholder="e.g. Senior Frontend Developer")
                        resume_output = gr.Markdown(label="Resume Analysis", elem_classes=["iv-panel", "career-output"])
                        resume_btn = gr.Button("Stream Resume Review", variant="primary")
                    with gr.Column():
                        jobs_input = gr.Textbox(label="Resume / Domain text", lines=12, placeholder="Paste resume content or domain context here.")
                        jobs_output = gr.Markdown(label="Job Suggestions", elem_classes=["iv-panel", "career-output"])
                        jobs_btn = gr.Button("Stream Job Matches", variant="primary")
                with gr.Row(equal_height=True):
                    with gr.Column():
                        company_input = gr.Textbox(label="Company", placeholder="e.g. Google")
                        prep_role_input = gr.Textbox(label="Role", placeholder="e.g. Software Engineer")
                        prep_output = gr.Markdown(label="Prep Guide", elem_classes=["iv-panel", "career-output"])
                        prep_btn = gr.Button("Stream Prep Guide", variant="primary")

            with gr.Tab("Memory Vault"):
                memory_snapshot = gr.Textbox(label="Current Memory Snapshot", lines=16, interactive=False)
                with gr.Row():
                    refresh_memory = gr.Button("Refresh Memory")
                    clear_memory = gr.Button("Clear Memory", variant="stop")

        def _load_upload(file_obj):
            return _extract_text_from_file(file_obj)

        resume_file.change(_load_upload, inputs=resume_file, outputs=resume_text)
        qna_file.change(_load_upload, inputs=qna_file, outputs=qna_text)

        start_btn.click(
            fn=coach.handle_start,
            inputs=[user_name, user_type, goal, target_role, domain, topic, difficulty, resume_text],
            outputs=[chatbot, session_state, memory_view, status],
        )

        def _apply_profile(session, name, ctype, goal_value, role_value, domain_value, topic_value, diff_value, resume_value):
            session.user_name = name or session.user_name
            session.user_type = ctype or session.user_type
            session.goal = goal_value or session.goal
            session.target_role = role_value or session.target_role
            session.domain = domain_value or session.domain
            session.topic = topic_value or session.topic
            session.difficulty = diff_value or session.difficulty
            session.resume_text = resume_value or session.resume_text
            coach._persist_session(session)
            return session

        def _send_message(message, audio_file, name, ctype, goal_value, role_value, domain_value, topic_value, diff_value, resume_value, chatbot_state):
            session = _ensure_session(chatbot_state)
            session = _apply_profile(session, name, ctype, goal_value, role_value, domain_value, topic_value, diff_value, resume_value)
            if not message and audio_file:
                message = coach.transcribe(audio_file)
            return coach.handle_user_message(message, session, "interview")

        send_btn.click(
            fn=_send_message,
            inputs=[user_text, audio, user_name, user_type, goal, target_role, domain, topic, difficulty, resume_text, session_state],
            outputs=[chatbot, session_state, memory_view, status],
        )

        transcribe_btn.click(
            fn=lambda audio_file: coach.transcribe(audio_file),
            inputs=audio,
            outputs=transcribed,
        )

        def _send_transcribed(text_value, name, ctype, goal_value, role_value, domain_value, topic_value, diff_value, resume_value, chatbot_state):
            session = _ensure_session(chatbot_state)
            session = _apply_profile(session, name, ctype, goal_value, role_value, domain_value, topic_value, diff_value, resume_value)
            return coach.handle_user_message(text_value, session, "interview")

        transcribed.submit(
            fn=_send_transcribed,
            inputs=[transcribed, user_name, user_type, goal, target_role, domain, topic, difficulty, resume_text, session_state],
            outputs=[chatbot, session_state, memory_view, status],
        )

        def _generate_qna(source_text, user_type_value, tech_value, nontech_value, input_mode, profile_state):
            session = _ensure_session(profile_state)
            context_text = source_text or ""
            if input_mode == "Resume":
                session.goal = "Question generation from a resume"
            else:
                session.goal = "Question generation from a job description"
            session.resume_text = context_text
            coach._persist_session(session)
            for output, session, memory, questions, _ in coach.generate_questions(
                context_text,
                user_type_value,
                int(tech_value),
                int(nontech_value),
                session,
            ):
                choices = questions or []
                yield output, session, memory, gr.update(choices=choices, value=choices[0] if choices else None)

        qna_generate_btn.click(
            fn=_generate_qna,
            inputs=[qna_text, user_type, tech_count, nontech_count, qna_mode, session_state],
            outputs=[qna_output, session_state, memory_view, qna_question],
        )

        def _generate_qna_answer(question_value, context_text, profile_state):
            session = _ensure_session(profile_state)
            for answer, session, memory in coach.generate_answer(question_value or "", context_text or "", session):
                yield answer, session, memory

        qna_answer_btn.click(
            fn=_generate_qna_answer,
            inputs=[qna_question, qna_text, session_state],
            outputs=[qna_answer, session_state, memory_view],
        )

        def _refine_qna_answer(question_value, answer_text, action, profile_state):
            session = _ensure_session(profile_state)
            for answer, session, memory in coach.modify_answer(question_value or "", answer_text or "", action, session):
                yield answer, session, memory

        def _elaborate_qna_answer(question_value, answer_text, profile_state):
            return _refine_qna_answer(question_value, answer_text, "elaborate", profile_state)

        def _shorten_qna_answer(question_value, answer_text, profile_state):
            return _refine_qna_answer(question_value, answer_text, "shorten", profile_state)

        qna_elaborate_btn.click(
            fn=_elaborate_qna_answer,
            inputs=[qna_question, qna_answer, session_state],
            outputs=[qna_answer, session_state, memory_view],
        )

        qna_shorten_btn.click(
            fn=_shorten_qna_answer,
            inputs=[qna_question, qna_answer, session_state],
            outputs=[qna_answer, session_state, memory_view],
        )

        resume_btn.click(
            fn=coach.analyze_resume,
            inputs=[resume_input, role_input, user_type, session_state],
            outputs=[resume_output, session_state, memory_view],
        )

        jobs_btn.click(
            fn=coach.find_jobs,
            inputs=[jobs_input, user_type, session_state],
            outputs=[jobs_output, session_state, memory_view],
        )

        prep_btn.click(
            fn=coach.interview_prep,
            inputs=[company_input, prep_role_input, user_type, session_state],
            outputs=[prep_output, session_state, memory_view],
        )

        refresh_memory.click(
            fn=lambda state: coach._memory_snapshot(_ensure_session(state)),
            inputs=session_state,
            outputs=memory_snapshot,
        )

        clear_memory.click(
            fn=lambda: coach.reset_session({}),
            inputs=[],
            outputs=[chatbot, session_state, memory_view, status],
        )

        user_text.submit(
            fn=_send_message,
            inputs=[user_text, audio, user_name, user_type, goal, target_role, domain, topic, difficulty, resume_text, session_state],
            outputs=[chatbot, session_state, memory_view, status],
        )

        demo.load(
            fn=lambda state: coach._memory_snapshot(_ensure_session(state)),
            inputs=session_state,
            outputs=memory_snapshot,
        )

        def _seed_session():
            state = coach.load_session(None)
            return state.to_dict(), coach._memory_snapshot(state), "Ready."

        demo.load(
            fn=_seed_session,
            inputs=[],
            outputs=[session_state, memory_view, status],
        )

    return demo


def main() -> None:
    print("Starting Interview Buddy...")
    try:
        app = build_app()
        print("Gradio app built.")
        app.queue(default_concurrency_limit=16)
        result = app.launch(
            css=CUSTOM_CSS,
            theme=APP_THEME,
            server_name="0.0.0.0",
            server_port=7860,
            show_error=True,
            prevent_thread_lock=False,
            inbrowser=False,
            share=False,
        )
        print(f"Launch returned: {result}")
    except Exception as exc:
        import traceback

        print("Startup failed.")
        traceback.print_exc()
        raise exc


if __name__ == "__main__":
    from voice_interview_app import main as app_main

    app_main()

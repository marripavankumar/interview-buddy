from __future__ import annotations

from pathlib import Path

import gradio as gr

from auth import _login_user, _signup_user
from voice_interview_coach import (
    APP_NAME,
    APP_THEME,
    CUSTOM_CSS,
    DEFAULT_CAREER_GOAL,
    DEFAULT_CAREER_LEVELS,
    DEFAULT_USER_TYPE,
    InterviewFlowCoach,
    SessionState,
    _extract_text_from_file,
)


ROOT = Path(__file__).resolve().parent
VIOLET_THEME = """
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
        radial-gradient(circle at 82% 12%, rgba(198, 221, 247, 0.36), transparent 22%),
        linear-gradient(180deg, #ffffff 0%, #f4faff 52%, #ffffff 100%);
      color: var(--iv-text);
    }

    .iv-hero {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.99), rgba(198, 221, 247, 0.28));
      border-color: rgba(198, 221, 247, 0.95) !important;
      box-shadow: 0 18px 60px rgba(198, 221, 247, 0.42);
    }

    .iv-card, .iv-panel {
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(198, 221, 247, 0.10)) !important;
      border-color: rgba(198, 221, 247, 0.95) !important;
      color: #000000 !important;
    }

    .iv-badge {
      background: rgba(198, 221, 247, 0.58);
      color: #0f172a;
      border-color: rgba(198, 221, 247, 0.95);
    }

    .iv-soft {
      color: var(--iv-muted);
    }

    .gr-button, .gr-button-primary, .gr-button-secondary {
      color: #0f172a !important;
    }

    .iv-card *, .iv-panel *, .iv-hero *, .gr-box *, .gr-textbox *, .gr-chatbot *, .gr-markdown * {
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
"""

coach = InterviewFlowCoach()


def _ensure_session(state: SessionState | dict[str, object] | None) -> SessionState:
    if isinstance(state, SessionState):
        return state
    if isinstance(state, dict) and state:
        return SessionState.from_dict(state)
    return coach.load_session(None)


def _theme_css(_: str | None = None) -> str:
    return f"<style id='iv-theme'>\n{VIOLET_THEME}\n</style>"


def _fallback_resume_review(text: str, target_role: str, user_type: str) -> str:
    words = [w for w in text.split() if w]
    score = min(94, max(42, 50 + len(words) // 18))
    focus_terms = ", ".join(words[:5]) if words else "impact, ownership, and role-specific keywords"
    return (
        f"### ATS Score\n**{score}/100**\n\n"
        f"### Feedback\nBackend analysis is temporarily unavailable, so this is a fallback review.\n\n"
        f"### Key Improvements\n"
        f"- Surface more role-specific keywords for **{target_role or 'the target role'}**\n"
        f"- Strengthen measurable impact and outcomes\n"
        f"- Keep bullets concise and action-oriented\n\n"
        f"### Enhanced Resume Snippet\n"
        f"Results-oriented {user_type} targeting {target_role or 'the role'}. Highlights strengths in {focus_terms} with ownership, impact, and measurable outcomes."
    )


def _fallback_jobs(text: str, user_type: str) -> str:
    terms = [term for term in text.split() if len(term) > 3][:5] or ["Software", "Product", "Operations"]
    items = "\n".join(f"- {term.title()} Specialist - A practical role aligned with strengths in {term.lower()}." for term in terms)
    return f"### Suggested Roles\n{items}\n\n_Fallback generated locally for {user_type}._"


def _error_message(prefix: str, exc: Exception) -> str:
    detail = str(exc).strip()
    if detail:
        return f"{prefix} {detail}"
    return prefix


def build_app() -> gr.Blocks:
    with gr.Blocks(title=APP_NAME) as demo:
        auth_state = gr.State(False)
        current_user = gr.State("")

        gr.HTML(
            f"""
            <div class="iv-shell">
              <div class="iv-hero iv-animate">
                <div class="iv-title">
                  <div style="width:52px;height:52px;border-radius:16px;background:linear-gradient(135deg,#ffffff,#C6DDF7);display:grid;place-items:center;font-weight:800;color:#0f172a;">IB</div>
                  <div>
                    <div class="iv-badge">Interview coaching</div>
                    <h1 class="iv-gradient-text" style="margin:0.25rem 0 0;font-size:2.2rem;">{APP_NAME}</h1>
                    <p class="iv-soft" style="margin:0.35rem 0 0;">Interview practice, question generation, resume review, job discovery, and company prep in one polished workspace.</p>
                  </div>
                </div>
              </div>
            </div>
            """
        )

        with gr.Column(visible=True) as auth_panel:
            with gr.Group(elem_classes=["iv-panel"]):
                auth_mode = gr.Radio(["Login", "Sign Up"], value="Login", label="Account")
                auth_username = gr.Textbox(label="Username", placeholder="e.g. alex_jones")
                auth_password = gr.Textbox(label="Password", type="password", placeholder="Enter your password")
                auth_message = gr.Markdown("", elem_classes=["iv-soft"])
                with gr.Row(elem_classes=["iv-primary"]):
                    auth_action = gr.Button("Log In", variant="primary")
                gr.Markdown(
                    "Use the same account to keep your interview history and memory consistent.",
                    elem_classes=["iv-soft"],
                )

        with gr.Column(visible=False) as app_panel:
            session_state = gr.State(coach.load_session(None).to_dict())

            with gr.Tabs():
                with gr.Tab("Interview Studio"):
                    with gr.Row(equal_height=True):
                        with gr.Column(scale=3):
                            chatbot = gr.Chatbot(label="Interview Thread", height=520, elem_classes=["iv-card", "iv-chat"])
                            status = gr.Markdown("Ready.", elem_classes=["iv-soft"])
                            user_text = gr.Textbox(
                                label="Answer / Prompt",
                                placeholder="Type your answer or ask for guidance...",
                                lines=3,
                            )
                            audio = gr.Audio(
                                label="Voice Prompt",
                                sources=["microphone", "upload"],
                                type="numpy",
                                format="wav",
                                interactive=True,
                            )
                            gr.HTML(
                                """
                                <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:0.35rem;">
                                  <span class="iv-chip">Record</span>
                                  <span class="iv-chip">Upload</span>
                                  <span class="iv-chip">Transcribe</span>
                                </div>
                                """
                            )
                            transcribed = gr.Textbox(
                                label="Transcribed voice",
                                placeholder="Transcription will appear here.",
                                lines=2,
                            )
                            with gr.Row(elem_classes=["iv-primary"]):
                                start_btn = gr.Button("Start / Reset Session", variant="primary")
                                transcribe_btn = gr.Button("Transcribe", variant="secondary")
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
                            memory_note = gr.Markdown("Memory is saved locally in `interview_memory.json`.", elem_classes=["iv-soft"])

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
                        with gr.Column(scale=3):
                            career_source = gr.Textbox(
                                label="Shared Career Source",
                                lines=12,
                                placeholder="Paste resume content or domain context here. This same source is used for resume review and job discovery.",
                            )
                            career_source_file = gr.File(
                                label="Upload Resume / Domain File",
                                file_count="single",
                                file_types=[".txt", ".md", ".pdf", ".docx"],
                            )
                        with gr.Column(scale=2):
                            role_input = gr.Textbox(label="Target role", placeholder="e.g. Senior Frontend Developer")
                            company_input = gr.Textbox(label="Company", placeholder="e.g. Google")
                            prep_role_input = gr.Textbox(label="Role for prep", placeholder="e.g. Software Engineer")
                    with gr.Row(equal_height=True):
                        with gr.Column():
                            resume_output = gr.Markdown(label="Resume Analysis", elem_classes=["iv-panel", "career-output"])
                            review_resume_btn = gr.Button("Review Resume", variant="primary")
                        with gr.Column():
                            jobs_output = gr.Markdown(label="Job Suggestions", elem_classes=["iv-panel", "career-output"])
                            find_jobs_btn = gr.Button("Find Jobs", variant="primary")
                        with gr.Column():
                            prep_output = gr.Markdown(label="Prep Guide", elem_classes=["iv-panel", "career-output"])
                            prep_btn = gr.Button("Get Prep Guide", variant="primary")

                with gr.Tab("Memory Vault"):
                    memory_snapshot = gr.Textbox(label="Current Memory Snapshot", lines=16, interactive=False)
                    with gr.Row():
                        refresh_memory = gr.Button("Refresh Memory")
                        clear_memory = gr.Button("Clear Memory", variant="stop")

            def _load_upload(file_obj):
                return _extract_text_from_file(file_obj)

            def _auth_switch(mode: str):
                return "Log In" if mode == "Login" else "Sign Up"

            def _merge_session(session, name, ctype, goal_value, role_value, domain_value, topic_value, diff_value, resume_value):
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

            def _resolve_prompt(message: str, voice_text: str, audio_file):
                message = (message or "").strip()
                if message:
                    return message, ""
                voice_text = (voice_text or "").strip()
                if voice_text:
                    if voice_text.startswith("Voice transcription failed") or voice_text.startswith("Voice transcription is unavailable"):
                        return "", voice_text
                    return voice_text, ""
                if audio_file:
                    transcript = (coach.transcribe(audio_file) or "").strip()
                    if not transcript or transcript.startswith("Voice transcription failed") or transcript.startswith("Voice transcription is unavailable"):
                        return "", transcript or "Voice transcription failed. Please try again or type the prompt manually."
                    return transcript, ""
                return "", "Please type a prompt or upload a voice clip."

            def _login_action(mode: str, username: str, password: str):
                if mode == "Sign Up":
                    return _signup_user(username, password)
                return _login_user(username, password)

            auth_mode.change(_auth_switch, inputs=auth_mode, outputs=auth_action)

            auth_action.click(
                fn=_login_action,
                inputs=[auth_mode, auth_username, auth_password],
                outputs=[auth_message, auth_panel, app_panel, auth_state, current_user, auth_mode, auth_action],
            )

            resume_file.change(_load_upload, inputs=resume_file, outputs=resume_text)
            qna_file.change(_load_upload, inputs=qna_file, outputs=qna_text)

            def _career_source_uploaded(file_obj, target_role_value, user_type_value, profile_state):
                session = _ensure_session(profile_state)
                text = _extract_text_from_file(file_obj)
                session.resume_text = text
                coach._persist_session(session)
                if not text.strip():
                    yield "", "Please upload a resume file to calculate the ATS score.", session, coach._memory_snapshot(session)
                    return
                if not (target_role_value or "").strip():
                    yield text, "Please enter a target role to calculate the ATS score.", session, coach._memory_snapshot(session)
                    return
                try:
                    last_output = ""
                    for output, session, memory in coach.analyze_resume(text, target_role_value, user_type_value, session):
                        last_output = output
                        yield text, last_output, session, memory
                except Exception as exc:
                    failure = _error_message("Resume review failed. Please retry.", exc)
                    fallback = _fallback_resume_review(text, target_role_value, user_type_value)
                    yield text, f"{fallback}\n\n> {failure}", session, coach._memory_snapshot(session)

            career_source_file.change(
                fn=_career_source_uploaded,
                inputs=[career_source_file, role_input, user_type, session_state],
                outputs=[career_source, resume_output, session_state, memory_view],
            )

            start_btn.click(
                fn=coach.handle_start,
                inputs=[user_name, user_type, goal, target_role, domain, topic, difficulty, resume_text],
                outputs=[chatbot, session_state, memory_view, status],
            )

            def _send_message(message, voice_text, audio_file, name, ctype, goal_value, role_value, domain_value, topic_value, diff_value, resume_value, chatbot_state):
                session = _ensure_session(chatbot_state)
                session = _merge_session(session, name, ctype, goal_value, role_value, domain_value, topic_value, diff_value, resume_value)
                prompt, error_message = _resolve_prompt(message, voice_text, audio_file)
                if error_message and not prompt:
                    yield coach._turns_to_chatbot(session.turns), session, coach._memory_snapshot(session), error_message
                    return
                try:
                    yield from coach.handle_user_message(prompt, session, "interview")
                except Exception as exc:
                    message_text = _error_message("Interview response failed. Please try again.", exc)
                    yield coach._turns_to_chatbot(session.turns), session, coach._memory_snapshot(session), message_text

            def _transcribe_voice(audio_file):
                if not audio_file:
                    return "", "Upload or record a voice clip first."
                try:
                    transcript = (coach.transcribe(audio_file) or "").strip()
                except Exception as exc:
                    return "", _error_message("Transcription failed. Please try again.", exc)
                if not transcript or transcript.startswith("Voice transcription failed") or transcript.startswith("Voice transcription is unavailable"):
                    return "", transcript or "Voice transcription failed. Please try another clip or type the prompt."
                return transcript, "Voice prompt transcribed."

            send_btn.click(
                fn=_send_message,
                inputs=[user_text, transcribed, audio, user_name, user_type, goal, target_role, domain, topic, difficulty, resume_text, session_state],
                outputs=[chatbot, session_state, memory_view, status],
            )

            transcribe_btn.click(
                fn=_transcribe_voice,
                inputs=audio,
                outputs=[transcribed, status],
            )

            transcribed.submit(
                fn=_send_message,
                inputs=[transcribed, transcribed, audio, user_name, user_type, goal, target_role, domain, topic, difficulty, resume_text, session_state],
                outputs=[chatbot, session_state, memory_view, status],
            )

            user_text.submit(
                fn=_send_message,
                inputs=[user_text, transcribed, audio, user_name, user_type, goal, target_role, domain, topic, difficulty, resume_text, session_state],
                outputs=[chatbot, session_state, memory_view, status],
            )

            def _generate_qna(source_text, user_type_value, tech_value, nontech_value, input_mode, profile_state):
                session = _ensure_session(profile_state)
                context_text = source_text or ""
                session.goal = "Question generation from a resume" if input_mode == "Resume" else "Question generation from a job description"
                session.resume_text = context_text
                coach._persist_session(session)
                try:
                    for output, session, memory, questions, _ in coach.generate_questions(
                        context_text,
                        user_type_value,
                        int(tech_value),
                        int(nontech_value),
                        session,
                    ):
                        choices = questions or []
                        yield output, session, memory, gr.update(choices=choices, value=choices[0] if choices else None)
                except Exception as exc:
                    yield _error_message("Question generation failed. Please retry.", exc), session, coach._memory_snapshot(session), gr.update(choices=[], value=None)

            qna_generate_btn.click(
                fn=_generate_qna,
                inputs=[qna_text, user_type, tech_count, nontech_count, qna_mode, session_state],
                outputs=[qna_output, session_state, memory_view, qna_question],
            )

            def _generate_qna_answer(question_value, context_text, profile_state):
                session = _ensure_session(profile_state)
                try:
                    for answer, session, memory in coach.generate_answer(question_value or "", context_text or "", session):
                        yield answer, session, memory
                except Exception as exc:
                    yield _error_message("Answer generation failed. Please retry.", exc), session, coach._memory_snapshot(session)

            qna_answer_btn.click(
                fn=_generate_qna_answer,
                inputs=[qna_question, qna_text, session_state],
                outputs=[qna_answer, session_state, memory_view],
            )

            def _refine_qna_answer(question_value, answer_text, action, profile_state):
                session = _ensure_session(profile_state)
                try:
                    for answer, session, memory in coach.modify_answer(question_value or "", answer_text or "", action, session):
                        yield answer, session, memory
                except Exception as exc:
                    yield _error_message("Answer refinement failed. Please retry.", exc), session, coach._memory_snapshot(session)

            qna_elaborate_btn.click(
                fn=lambda question_value, answer_text, profile_state: _refine_qna_answer(question_value, answer_text, "elaborate", profile_state),
                inputs=[qna_question, qna_answer, session_state],
                outputs=[qna_answer, session_state, memory_view],
            )

            qna_shorten_btn.click(
                fn=lambda question_value, answer_text, profile_state: _refine_qna_answer(question_value, answer_text, "shorten", profile_state),
                inputs=[qna_question, qna_answer, session_state],
                outputs=[qna_answer, session_state, memory_view],
            )

            def _career_resume_review(source_text, target_role_value, user_type_value, profile_state):
                session = _ensure_session(profile_state)
                try:
                    yield from coach.analyze_resume(source_text or "", target_role_value or "", user_type_value, session)
                except Exception as exc:
                    fallback = _fallback_resume_review(source_text or "", target_role_value or "", user_type_value)
                    yield f"{fallback}\n\n> {_error_message('Resume review failed. Please retry.', exc)}", session, coach._memory_snapshot(session)

            review_resume_btn.click(
                fn=_career_resume_review,
                inputs=[career_source, role_input, user_type, session_state],
                outputs=[resume_output, session_state, memory_view],
            )

            def _career_jobs(source_text, user_type_value, profile_state):
                session = _ensure_session(profile_state)
                try:
                    yield from coach.find_jobs(source_text or "", user_type_value, session)
                except Exception as exc:
                    fallback = _fallback_jobs(source_text or "", user_type_value)
                    yield f"{fallback}\n\n> {_error_message('Job discovery failed. Please retry.', exc)}", session, coach._memory_snapshot(session)

            find_jobs_btn.click(
                fn=_career_jobs,
                inputs=[career_source, user_type, session_state],
                outputs=[jobs_output, session_state, memory_view],
            )

            def _career_prep(company_value, role_value, user_type_value, profile_state):
                session = _ensure_session(profile_state)
                try:
                    yield from coach.interview_prep(company_value or "", role_value or "", user_type_value, session)
                except Exception as exc:
                    fallback = _fallback_jobs(f"{company_value} {role_value}", user_type_value)
                    yield f"{fallback}\n\n> {_error_message('Prep guide generation failed. Please retry.', exc)}", session, coach._memory_snapshot(session)

            prep_btn.click(
                fn=_career_prep,
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
    app = build_app()
    print("Gradio app built.")
    app.queue(default_concurrency_limit=16)
    app.launch(
        css=CUSTOM_CSS,
        theme=APP_THEME,
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        prevent_thread_lock=False,
        inbrowser=False,
        share=False,
    )


if __name__ == "__main__":
    main()

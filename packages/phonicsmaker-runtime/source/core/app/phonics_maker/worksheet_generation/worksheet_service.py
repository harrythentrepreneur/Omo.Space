import json
from datetime import datetime
from typing import Dict, Any, Tuple, List
from app.core.ai.ai_config import ai_config
from app.core.config.logger import logger


class CustomWorksheetService:
    def __init__(self):
        self.max_retries = 3

    # ─── Agent 1: Worksheet Generator ────────────────────────────────
    async def _run_agent_1_generate(
        self, prompt: str, curriculum: str, previous_feedback: str = None
    ) -> Tuple[str, str]:
        """Generate the worksheet HTML and a generation report.
        Returns (html_content, generation_report_json)"""

        revision_block = ""
        if previous_feedback:
            revision_block = (
                "\n\n⚠️ REVISION REQUIRED — Your previous draft was rejected by the QA panel.\n"
                f"Address every point below before re-drafting:\n{previous_feedback}\n"
            )

        sys_prompt = (
            f"You are an expert curriculum designer for the **{curriculum}**.\n"
            f"{revision_block}\n"
            f"A teacher has requested the following worksheet:\n\"{prompt}\"\n\n"
            "INSTRUCTIONS:\n"
            "1. Generate a COMPLETE, ready-to-print educational worksheet using clean HTML.\n"
            "2. MUST USE THESE EXACT CSS CLASSES FOR STYLING:\n"
            "   - Header: <div class=\"worksheet-header\"> containing <h1 class=\"worksheet-title\"> and <p class=\"worksheet-subtitle\">\n"
            "   - Logo: INSIDE the top of your header area, MUST include: <img class=\"worksheet-logo\" src=\"LOGO_URL_PLACEHOLDER\" alt=\"PhonicsMaker\">\n"
            "   - Name/Date: <div class=\"student-info\"><div class=\"info-group\"><span>Name:</span><span class=\"info-line\"></span></div><div class=\"info-group\"><span>Date:</span><span class=\"info-line\"></span></div></div>\n"
            "   - Instructions: <div class=\"instructions\"><div class=\"instructions-title\">📖 Instructions</div><p class=\"instructions-text\">...</p></div>\n"
            "   - Teacher Tip: At the bottom, include <div class=\"teacher-tip\"><div class=\"teacher-tip-title\">💡 Parent/Teacher Tip</div>...</div>\n"
            "   - Content: Wrap your main activity content in <div class=\"content-area\">\n"
            "3. Make it well-spaced and beautifully formatted for young learners.\n"
            "4. DO NOT wrap the HTML in markdown code blocks.\n"
            "5. Output ONLY the inner HTML content (no <html>, <head>, or <body> tags).\n\n"
            "After the HTML, on a new line write ===REPORT=== and then output a brief JSON object "
            "summarising what you generated:\n"
            '{"title":"...", "target_age":"...", "skills_covered":["..."], '
            '"question_count": N, "notes": "Any relevant design notes"}\n'
        )

        response = await ai_config.generate_with_gemini(sys_prompt)

        # Split HTML content from the report
        html_content = response
        report_json = "{}"
        if "===REPORT===" in response:
            parts = response.split("===REPORT===", 1)
            html_content = parts[0].strip()
            raw_report = parts[1].strip()
            # Clean markdown wrappers
            raw_report = raw_report.replace("```json", "").replace("```", "").strip()
            report_json = raw_report
        
        # Clean any markdown code fences from the HTML
        if html_content.startswith("```html"):
            html_content = html_content[7:]
        if html_content.startswith("```"):
            html_content = html_content[3:]
        if html_content.endswith("```"):
            html_content = html_content[:-3]
        html_content = html_content.strip()

        return html_content, report_json

    # ─── Agent 2: Curriculum Evaluator ───────────────────────────────
    async def _run_agent_2_curriculum(
        self, draft: str, prompt: str, curriculum: str
    ) -> Tuple[bool, str, str]:
        """Evaluate curriculum alignment.
        Returns (passed, formal_report, feedback_for_author)"""

        eval_prompt = (
            f"You are a senior QA auditor for the **{curriculum}**.\n\n"
            f"## Original Teacher Request\n\"{prompt}\"\n\n"
            f"## Worksheet Draft (HTML)\n{draft}\n\n"
            "## YOUR TASK\n"
            "Produce a formal **Curriculum Alignment Report** evaluating this worksheet.\n\n"
            "IMPORTANT RULES FOR APPROVAL:\n"
            "- Your default stance should be to APPROVE (passed: true) if the worksheet is basically acceptable.\n"
            "- ONLY reject (passed: false) if it contains fundamental factual errors, completely ignores the requested topic, or does not align with the curriculum.\n"
            "- Minor subjective improvements should be placed in 'areas_for_improvement' but you MUST STILL APPROVE IT (passed: true).\n\n"
            "Your output MUST be valid JSON with this exact structure:\n"
            "```json\n"
            "{\n"
            '  "passed": true,\n'
            '  "verdict": "APPROVED" or "REVISIONS REQUIRED",\n'
            '  "overall_score": "8/10",\n'
            '  "report": {\n'
            '    "curriculum_alignment": "Assessment of alignment to the curriculum...",\n'
            '    "content_accuracy": "Cross-check that all facts, spellings, and subject matter are correct...",\n'
            '    "learning_objectives": "Whether learning objectives are clear and measurable...",\n'
            '    "differentiation": "Whether the worksheet supports varied learner levels...",\n'
            '    "strengths": ["Strength 1", "Strength 2"],\n'
            '    "areas_for_improvement": ["Issue 1", "Issue 2"]\n'
            "  },\n"
            '  "feedback_for_author": "If REVISIONS REQUIRED, specific actionable changes needed."\n'
            "}\n"
            "```\n"
            "Output ONLY the JSON. No other text."
        )

        response = await ai_config.generate_with_gemini(eval_prompt)
        try:
            cleaned = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            passed = data.get("passed", False)
            report = json.dumps(data.get("report", {}), indent=2)
            verdict = data.get("verdict", "UNKNOWN")
            score = data.get("overall_score", "N/A")
            # Build a nice readable report string
            formal_report = f"**Verdict:** {verdict}  |  **Score:** {score}\n\n{report}"
            feedback = data.get("feedback_for_author", "")
            return passed, formal_report, feedback
        except json.JSONDecodeError:
            logger.error(f"Agent 2 returned invalid JSON: {response[:500]}")
            return False, "⚠️ Could not parse curriculum evaluation.", "Re-evaluate — Agent 2 returned malformed output."
        except Exception as e:
            logger.error(f"Agent 2 error: {e}")
            return False, f"⚠️ Evaluation error: {str(e)}", str(e)

    # ─── Agent 3: Formatting & Print Quality Evaluator ───────────────
    async def _run_agent_3_format(self, draft: str) -> Tuple[bool, str, str]:
        """Evaluate formatting and print readiness.
        Returns (passed, formal_report, feedback_for_author)"""

        eval_prompt = (
            "You are a senior print design QA specialist for educational materials.\n\n"
            f"## Worksheet Draft (HTML)\n{draft}\n\n"
            "## YOUR TASK\n"
            "Produce a formal **Formatting & Print Quality Report** for this worksheet.\n\n"
            "IMPORTANT RULES FOR APPROVAL:\n"
            "- Your default stance should be to APPROVE (passed: true).\n"
            "- ONLY reject (passed: false) if the HTML is severely broken, completely unreadable, or missing critical sections.\n"
            "- Minor subjective layout improvements should be placed in 'areas_for_improvement' but you MUST STILL APPROVE IT (passed: true).\n\n"
            "Your output MUST be valid JSON with this exact structure:\n"
            "```json\n"
            "{\n"
            '  "passed": true,\n'
            '  "verdict": "APPROVED" or "REVISIONS REQUIRED",\n'
            '  "overall_score": "8/10",\n'
            '  "report": {\n'
            '    "visual_hierarchy": "Assessment of headings, sections, and flow...",\n'
            '    "print_readiness": "Will it print cleanly on A4? Margins, spacing, overflow...",\n'
            '    "writing_space": "Is there enough space for students to write answers?",\n'
            '    "accessibility": "Font sizing, contrast, and dyslexia friendliness...",\n'
            '    "strengths": ["Strength 1", "Strength 2"],\n'
            '    "areas_for_improvement": ["Issue 1", "Issue 2"]\n'
            "  },\n"
            '  "feedback_for_author": "If REVISIONS REQUIRED, specific changes needed."\n'
            "}\n"
            "```\n"
            "Output ONLY the JSON. No other text."
        )

        response = await ai_config.generate_with_gemini(eval_prompt)
        try:
            cleaned = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            passed = data.get("passed", False)
            report = json.dumps(data.get("report", {}), indent=2)
            verdict = data.get("verdict", "UNKNOWN")
            score = data.get("overall_score", "N/A")
            formal_report = f"**Verdict:** {verdict}  |  **Score:** {score}\n\n{report}"
            feedback = data.get("feedback_for_author", "")
            return passed, formal_report, feedback
        except json.JSONDecodeError:
            logger.error(f"Agent 3 returned invalid JSON: {response[:500]}")
            return False, "⚠️ Could not parse formatting evaluation.", "Re-evaluate — Agent 3 returned malformed output."
        except Exception as e:
            logger.error(f"Agent 3 error: {e}")
            return False, f"⚠️ Evaluation error: {str(e)}", str(e)

    # ─── Main Orchestration Loop ─────────────────────────────────────
    async def generate_worksheet(
        self, task_id: str, prompt: str, curriculum: str, callback=None
    ) -> Dict[str, Any]:
        logs: List[Dict[str, Any]] = []
        agent_reports: Dict[str, str] = {}

        def log_event(agent: str, status: str, message: str, passed: bool = None, report: str = None):
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "agent": agent,
                "status": status,
                "message": message,
                "passed": passed,
            }
            if report:
                log_entry["report"] = report
            logs.append(log_entry)
            logger.info(f"[{agent}] {status}: {message}")
            if callback:
                callback(task_id, json.dumps(logs))

        current_draft = ""
        combined_feedback = ""

        try:
            for attempt in range(1, self.max_retries + 1):
                log_event("System", "Info", f"── Iteration {attempt}/{self.max_retries} ──")

                # ── Agent 1: Generate ────────────────────────────────
                if attempt > 1:
                    log_event("Agent 1 (Generator)", "Working", f"Revising draft based on {len(combined_feedback.splitlines())} feedback points…")
                else:
                    log_event("Agent 1 (Generator)", "Working", "Designing worksheet structure and content…")
                
                current_draft, gen_report_json = await self._run_agent_1_generate(
                    prompt, curriculum, combined_feedback if attempt > 1 else None
                )
                agent_reports["generation"] = gen_report_json
                log_event(
                    "Agent 1 (Generator)", "Completed",
                    f"Draft completed — {len(current_draft):,} characters of HTML generated.",
                    True, gen_report_json
                )

                # ── Agent 2: Curriculum ──────────────────────────────
                log_event("Agent 2 (Curriculum)", "Working", "Cross-checking against curriculum standards and learning objectives…")
                passed_curr, curr_report, fb_curr = await self._run_agent_2_curriculum(
                    current_draft, prompt, curriculum
                )
                agent_reports["curriculum"] = curr_report
                log_event(
                    "Agent 2 (Curriculum)",
                    "Evaluated",
                    f"Curriculum review: {'APPROVED ✓' if passed_curr else 'REVISIONS REQUIRED ✗'}",
                    passed_curr, curr_report
                )

                # ── Agent 3: Formatting ──────────────────────────────
                log_event("Agent 3 (Formatting)", "Working", "Checking print layout, spacing, visual hierarchy, and accessibility…")
                passed_fmt, fmt_report, fb_fmt = await self._run_agent_3_format(current_draft)
                agent_reports["formatting"] = fmt_report
                log_event(
                    "Agent 3 (Formatting)",
                    "Evaluated",
                    f"Formatting review: {'APPROVED ✓' if passed_fmt else 'REVISIONS REQUIRED ✗'}",
                    passed_fmt, fmt_report
                )

                combined_feedback = ""
                if not passed_curr:
                    combined_feedback += f"- [Curriculum Evaluator] {fb_curr}\n"
                if not passed_fmt:
                    combined_feedback += f"- [Formatting Evaluator] {fb_fmt}\n"

                if combined_feedback:
                    feedback_count = len([f for f in combined_feedback.strip().splitlines() if f.strip()])
                    log_event("System", "Retry", f"QA panel requested {feedback_count} revision(s). Sending feedback to Generator…")
                    continue

                # ── All Passed ───────────────────────────────────────
                log_event("System", "Success", f"✅ All {2} quality checks passed — worksheet approved for classroom use!")
                break
            else:
                log_event(
                    "System", "Warning",
                    f"⚠️ Max retries ({self.max_retries}) reached. Delivering best available draft."
                )

            return {
                "html_content": current_draft,
                "agent_reports": agent_reports,
                "logs": logs,
            }
        except Exception as e:
            logger.error(f"Worksheet generation error: {e}")
            log_event("System", "Error", f"Generation failed: {str(e)}", False)
            raise e

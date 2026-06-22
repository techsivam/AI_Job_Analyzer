import json
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pypdf import PdfReader
from langchain_openai import ChatOpenAI

from src.common.logger import get_logger
from src.common.custom_exception import CustomException


class ResumeAnalysisAgent:
    def __init__(self, cutoff_score: int = 75):
        self.logger = get_logger(__name__)
        self.cutoff_score = cutoff_score
        self.resume_text = ""
        self.jd_text = ""
        self.extracted_skills: List[str] = []
        self.logger.info("ResumeAnalysisAgent initialized with cutoff score: %d", self.cutoff_score)

    # ------------------------------------------------------------------ #
    #  File reading                                                        #
    # ------------------------------------------------------------------ #

    def _read_pdf(self, file) -> str:
        try:
            self.logger.info("Reading PDF file: %s", file.name)
            reader = PdfReader(file)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            self.logger.info("Finished reading PDF file: %s", file.name)
            return text
        except Exception as e:
            self.logger.error("Error reading PDF file", exc_info=True)
            raise CustomException("Error reading PDF file", e)

    def _read_txt(self, file) -> str:
        try:
            self.logger.info("Reading TXT file: %s", file.name)
            text = (
                file.getvalue().decode("utf-8")
                if hasattr(file, "getvalue")
                else file.read().decode("utf-8")
            )
            self.logger.info("Finished reading TXT file: %s", file.name)
            return text
        except Exception as e:
            self.logger.error("Error reading TXT file", exc_info=True)
            raise CustomException("Error reading TXT file", e)

    def extract_text(self, file) -> str:
        try:
            self.logger.info("Extracting text from file: %s", file.name)
            ext = file.name.rsplit(".", 1)[-1].lower()
            if ext == "pdf":
                return self._read_pdf(file)
            elif ext == "txt":
                return self._read_txt(file)
            else:
                self.logger.warning("Unsupported file format: %s", ext)
                return ""
        except Exception as e:
            self.logger.error("Error extracting text from file", exc_info=True)
            raise CustomException(f"Unsupported file format: {e}", e)

    # ------------------------------------------------------------------ #
    #  Skill extraction from JD                                           #
    # ------------------------------------------------------------------ #

    def extract_skills_from_jd(self, jd_text: str) -> List[str]:
        try:
            self.logger.info("Extracting skills from job description")
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

            # FIX: the original example had a missing opening quote on "Docker"
            # which caused json.loads to raise, returning score 0 for every skill.
            prompt = (
                "Extract only technical skills from the given job description.\n"
                "Rules:\n"
                "1. Return ONLY a valid JSON array of strings — no markdown, no explanation.\n"
                "2. Include programming languages, frameworks, cloud services, tools, and platforms.\n"
                "3. Do NOT include soft skills or general competencies.\n\n"
                'Example output: ["Java", "Go", "Python", "Docker", "Kubernetes", "AWS", "Kafka"]\n\n'
                f"Job Description:\n{jd_text}"
            )

            response = llm.invoke(prompt)

            # Strip accidental markdown fences before parsing
            content = response.content.strip().strip("```json").strip("```").strip()
            skills = json.loads(content)

            if isinstance(skills, list):
                skills = [s for s in skills if isinstance(s, str) and s.strip()]
                self.logger.info("Extracted %d skills: %s", len(skills), skills)
                return skills
            else:
                self.logger.warning("Unexpected skills type: %s", type(skills))
                return []
        except Exception as e:
            self.logger.error("Error extracting skills from job description", exc_info=True)
            raise CustomException("Error extracting skills from job description", e)

    # ------------------------------------------------------------------ #
    #  Per-skill evaluation (called in parallel)                          #
    # ------------------------------------------------------------------ #

    def _evaluate_skill(self, skill: str) -> Dict:
        """Evaluate a single skill against the resume. Thread-safe (stateless read)."""
        try:
            self.logger.info("Evaluating skill: %s", skill)
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

            # FIX: use more resume text (original truncated at 2500 chars)
            resume_excerpt = self.resume_text[:6000]

            prompt = (
                f'Evaluate how clearly the resume demonstrates proficiency in "{skill}".\n'
                "Score from 0 to 10:\n"
                "  0 = not mentioned at all\n"
                "  5 = mentioned or implied\n"
                " 10 = expert-level, clearly demonstrated with experience\n\n"
                f"Resume:\n{resume_excerpt}\n\n"
                "Return ONLY valid JSON in this exact format (no markdown, no extra text):\n"
                f'{{"skill": "{skill}", "score": 7}}'
            )

            response = llm.invoke(prompt)
            content = response.content.strip().strip("```json").strip("```").strip()
            result = json.loads(content)

            # Validate expected shape
            score = int(result.get("score", 0))
            score = max(0, min(10, score))          # clamp to [0, 10]

            self.logger.info("Skill '%s' scored %d/10", skill, score)
            return {"skill": skill, "score": score}

        except Exception as e:
            self.logger.error("Error evaluating skill '%s': %s", skill, e, exc_info=True)
            return {"skill": skill, "score": 0}

    # ------------------------------------------------------------------ #
    #  Parallel evaluation + scoring                                      #
    # ------------------------------------------------------------------ #

    def evaluate_skills(self) -> Dict:
        """
        Evaluate all extracted skills in parallel using ThreadPoolExecutor.
        Uses as_completed() so we can log each result as it arrives.

        Score formula  →  round(average_per_skill_score * 10)
          • each skill is scored 0–10
          • average across all skills → 0.0–10.0
          • multiply by 10  → 0–100 overall score
        """
        if not self.extracted_skills:
            self.logger.warning("No skills extracted; returning zero score")
            return {
                "overall_score": 0,
                "selected": False,
                "strengths": [],
                "missing_skills": [],
                "skill_scores": {},
            }

        try:
            self.logger.info(
                "Evaluating %d skills in parallel (max_workers=5)", len(self.extracted_skills)
            )

            results: List[Dict] = []

            # Using as_completed for responsive logging; results collected in insertion order
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_skill = {
                    executor.submit(self._evaluate_skill, skill): skill
                    for skill in self.extracted_skills
                }

                for future in as_completed(future_to_skill):
                    skill = future_to_skill[future]
                    try:
                        result = future.result()
                        results.append(result)
                        self.logger.debug("Received result for skill '%s'", skill)
                    except Exception as e:
                        self.logger.error(
                            "Unhandled exception for skill '%s': %s", skill, e, exc_info=True
                        )
                        results.append({"skill": skill, "score": 0})

            # Build score map
            scores: Dict[str, int] = {r["skill"]: r["score"] for r in results}

            # FIX: correct formula — produces a value in [0, 100]
            avg = sum(scores.values()) / len(scores)
            overall_score = round(avg * 10)          # e.g. avg=7.5 → score=75

            strengths = [k for k, v in scores.items() if v >= 7]
            missing = [k for k, v in scores.items() if v < 5]

            self.logger.info(
                "Evaluation complete — overall score: %d/100 (avg per-skill: %.2f/10)",
                overall_score,
                avg,
            )

            return {
                "overall_score": overall_score,
                "selected": overall_score >= self.cutoff_score,
                "strengths": strengths,
                "missing_skills": missing,
                "skill_scores": scores,
            }

        except Exception as e:
            self.logger.error("Error evaluating skills in parallel", exc_info=True)
            raise CustomException("Error evaluating skills in parallel", e)

    # ------------------------------------------------------------------ #
    #  Public entry point                                                  #
    # ------------------------------------------------------------------ #

    def analyze(self, resume_file, jd_file) -> Dict:
        try:
            self.logger.info("Starting resume analysis")
            self.resume_text = self.extract_text(resume_file)
            self.jd_text = self.extract_text(jd_file)
            self.extracted_skills = self.extract_skills_from_jd(self.jd_text)
            evaluation_result = self.evaluate_skills()
            self.logger.info("Finished resume analysis")
            return evaluation_result
        except Exception as e:
            self.logger.error("Error analyzing resume", exc_info=True)
            raise CustomException("Error analyzing resume", e)
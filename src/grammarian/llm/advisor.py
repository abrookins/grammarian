"""LLM-powered writing advisor using LiteLLM."""

from typing import Any

from grammarian.core.models import AnalysisResult, Issue


class WritingAdvisor:
    """LLM-powered writing advisor that provides contextual feedback."""

    DEFAULT_SYSTEM_PROMPT = """You are a professional writing coach. Analyze the provided text and metrics, then give concise, actionable feedback.

Focus on:
1. The most impactful improvements the writer can make
2. Specific examples from the text
3. Brief explanations of why changes would improve the writing

Keep feedback under 300 words. Be encouraging but direct."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        context: str = "",
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.context = context
        self._client = None

    def _get_client(self) -> Any:
        """Lazily initialize LiteLLM."""
        if self._client is None:
            try:
                import litellm
                self._client = litellm
            except ImportError:
                raise ImportError("LiteLLM not installed. Run: pip install litellm")
        return self._client

    def _build_prompt(self, text: str, result: AnalysisResult) -> str:
        """Build the prompt for the LLM."""
        # Summarize metrics
        metrics_summary = []
        for metric in result.metrics:
            metrics_summary.append(f"- {metric.name}: {metric.score:.2f} ({metric.rating.value})")

        # Top issues
        issues_summary = []
        for issue in result.all_issues[:10]:
            issues_summary.append(f"- {issue.message}")

        prompt = f"""## Writing Analysis

**Overall Score:** {result.wqi_score:.2f} ({result.rating.value})

**Metrics:**
{chr(10).join(metrics_summary)}

**Top Issues:**
{chr(10).join(issues_summary) if issues_summary else "None detected"}

**Text Sample (first 1000 chars):**
{text[:1000]}{"..." if len(text) > 1000 else ""}
"""
        if self.context:
            prompt = f"**Writing Context:** {self.context}\n\n{prompt}"

        prompt += "\n\nProvide actionable feedback to improve this writing."
        return prompt

    def get_feedback(self, text: str, result: AnalysisResult) -> str:
        """Get AI-powered feedback on the writing."""
        client = self._get_client()

        prompt = self._build_prompt(text, result)

        response = client.completion(
            model=self.model,
            messages=[
                {"role": "system", "content": self.DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=500,
        )

        return response.choices[0].message.content

    def suggest_rewrites(self, text: str, issues: list[Issue], max_suggestions: int = 3) -> list[dict[str, str]]:
        """Suggest specific rewrites for problematic sections."""
        client = self._get_client()

        issues_text = "\n".join([f"- {i.message}" for i in issues[:max_suggestions]])

        prompt = f"""Given this text and issues, suggest specific rewrites.

**Text:**
{text[:2000]}

**Issues:**
{issues_text}

For each issue, provide:
1. The original problematic text
2. A suggested rewrite
3. Brief explanation

Format as JSON array: [{{"original": "...", "rewrite": "...", "reason": "..."}}]"""

        response = client.completion(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a writing editor. Respond only with valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1000,
        )

        import json
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return []


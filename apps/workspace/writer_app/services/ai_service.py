"""
AI Writing Assistant for SciTeX Writer.
Context-aware content generation and improvement suggestions.
"""

import os
from typing import Dict, List, Optional


class WriterAI:
    """AI assistant for scientific writing."""

    def __init__(self):
        """Initialize AI client."""
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = "claude-3-5-sonnet-20241022"  # or 'gpt-4'
        self.use_anthropic = os.getenv("ANTHROPIC_API_KEY") is not None

    def get_suggestion(
        self,
        content: str,
        section_type: str,
        target: str = "clarity",
        context: Optional[Dict] = None,
    ) -> Dict:
        """
        Get AI suggestions for improving text.

        Args:
            content: Current section content
            section_type: Type of section (abstract, introduction, methods, etc.)
            target: Improvement target (clarity, conciseness, academic_style, etc.)
            context: Additional context (other sections, project info)

        Returns:
            Dict with suggested_text, explanation, and changes
        """
        prompt = self._build_improvement_prompt(content, section_type, target, context)

        if self.use_anthropic:
            return self._call_anthropic(prompt)
        else:
            return self._call_openai(prompt)

    def generate_content(
        self, section_type: str, target_words: int, context: Optional[Dict] = None
    ) -> Dict:
        """
        Generate content for a section.

        Args:
            section_type: Type of section to generate
            target_words: Target word count
            context: Context from other sections

        Returns:
            Dict with generated_text and metadata
        """
        prompt = self._build_generation_prompt(section_type, target_words, context)

        if self.use_anthropic:
            return self._call_anthropic(prompt)
        else:
            return self._call_openai(prompt)

    def suggest_citations(self, text: str, section_type: str) -> List[Dict]:
        """
        Suggest citations for claims that need references.

        Args:
            text: Text to analyze
            section_type: Section type for context

        Returns:
            List of suggestions with position, claim, and reasoning
        """
        prompt = f"""Analyze this {section_type} section and identify claims that need citations:

{text}

For each claim needing a citation, provide:
1. The specific claim
2. Why it needs a citation
3. What type of evidence would support it

Format as JSON list."""

        result = (
            self._call_anthropic(prompt)
            if self.use_anthropic
            else self._call_openai(prompt)
        )

        # Parse and return suggestions
        return result.get("suggestions", [])

    def _build_improvement_prompt(
        self, content: str, section_type: str, target: str, context: Optional[Dict]
    ) -> str:
        """Build prompt for content improvement."""

        prompts = {
            "clarity": f"""Improve the clarity of this {section_type} section while maintaining scientific accuracy:

{content}

Provide:
1. Revised version with clearer language
2. List of specific improvements made
3. Explanation of changes

Keep the academic tone but make it more accessible.""",
            "conciseness": f"""Make this {section_type} section more concise without losing key information:

{content}

Target: Reduce by 20-30% while preserving all essential points.
Provide the revised version and list what was condensed.""",
            "academic_style": f"""Enhance the academic style and formality of this {section_type}:

{content}

Improve:
- Use more precise scientific terminology
- Strengthen logical flow
- Add appropriate hedging where needed
- Follow academic writing conventions

Provide revised version with explanations.""",
            "expand": f"""Expand this {section_type} section with more detail and examples:

{content}

Add:
- More detailed explanations
- Relevant examples
- Supporting details
- Smooth transitions

Provide expanded version.""",
        }

        return prompts.get(target, prompts["clarity"])

    def _build_generation_prompt(
        self, section_type: str, target_words: int, context: Optional[Dict]
    ) -> str:
        """Build prompt for content generation."""

        context_text = ""
        if context:
            if context.get("methods"):
                context_text += f"\n\nMethods summary:\n{context['methods']}"
            if context.get("results"):
                context_text += f"\n\nResults summary:\n{context['results']}"
            if context.get("introduction"):
                context_text += f"\n\nIntroduction:\n{context['introduction']}"

        prompts = {
            "abstract": f"""Generate an abstract (approximately {target_words} words) for a scientific paper with this content:{context_text}

Structure:
1. Background/Context (1-2 sentences)
2. Objective (1 sentence)
3. Methods (1-2 sentences)
4. Key Results (2-3 sentences)
5. Conclusions/Implications (1-2 sentences)

Write in past tense, be concise and specific.""",
            "discussion": f"""Generate a discussion section (approximately {target_words} words) based on these results:{context_text}

Include:
1. Interpretation of key findings
2. Comparison with existing literature
3. Limitations and caveats
4. Future research directions
5. Broader implications

Use appropriate academic tone and hedging language.""",
            "conclusion": f"""Generate a conclusion (approximately {target_words} words) summarizing this research:{context_text}

Include:
1. Restate main objective and approach
2. Summarize key findings
3. Highlight significance and impact
4. Suggest future work

Be concise and impactful.""",
        }

        return prompts.get(
            section_type,
            f"Generate a {section_type} section ({target_words} words) for a scientific paper.",
        )

    def _call_anthropic(self, prompt: str) -> Dict:
        """Call Anthropic Claude API."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            response = client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            return {
                "text": response.content[0].text,
                "tokens_used": response.usage.input_tokens
                + response.usage.output_tokens,
                "model": self.model,
            }

        except Exception as e:
            return {"error": str(e), "text": ""}

    def _call_openai(self, prompt: str) -> Dict:
        """Call OpenAI GPT API."""
        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )

            return {
                "text": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens,
                "model": "gpt-4",
            }

        except Exception as e:
            return {"error": str(e), "text": ""}


# Singleton instance
_ai_instance = None


def get_ai_assistant() -> WriterAI:
    """Get or create AI assistant instance."""
    global _ai_instance
    if _ai_instance is None:
        _ai_instance = WriterAI()
    return _ai_instance

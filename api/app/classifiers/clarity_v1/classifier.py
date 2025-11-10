"""
Clarity Classifier V1

A clarity classifier that uses OpenAI's structured output to rate
how clear and fact-checkable the claims in a social media post are.
"""

from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from app.classifiers.base import BaseClassifier
from app.classifiers.registry import register_classifier
from app.classifiers.shared.tweet_utils import prepare_fact_check_input, format_content_with_media, AUTHOR_CONTEXT_CONTENT_PROMPT
from app.config import settings

# Pydantic model for structured output
class ClarityClassification(BaseModel):
    """Structured output for clarity classification"""

    reason: str = Field(description="Explanation of why this clarity rating applies")
    # From a list of literals representing clarity scores 1-5
    clarity: Literal[
        "clarity_1",  # Very Unclear (1)
        "clarity_2",  # Unclear (2)
        "clarity_3",  # Moderate (3)
        "clarity_4",  # Clear (4)
        "clarity_5",  # Very Clear (5)
    ] = Field(description="Clarity rating for fact-checking")
    confidence: float = Field(
        description="Confidence score for the clarity rating (0-1)",
        ge=0.0,
        le=1.0
    )

@register_classifier
class ClarityV1(BaseClassifier):
    slug = "clarity-v1"
    """
    Clarity Classifier - Rates how clear the fact-checking job is
    """
    
    def __init__(self, slug: str, output_schema: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        super().__init__(slug, output_schema, config)
        self._llm = None  # Cached LLM instance
    
    def _get_llm(self) -> ChatOpenAI:
        """Get or create cached LLM instance"""
        if self._llm is None:
            model_name = self.config.get("model", "gpt-5-mini")
            reasoning = {
                "effort": "medium",  # 'low', 'medium', or 'high'
                "summary": None,  # 'detailed', 'auto', or None
            }
            
            self._llm = ChatOpenAI(
                model=model_name, 
                api_key=settings.openai_api_key,
                output_version="responses/v1",
                reasoning=reasoning
            )
        return self._llm
    
    async def classify(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a post according to its clarity for fact-checking
        
        Args:
            post_data: Dict containing post information
            
        Returns:
            Classification result with type and values array
        """
        post_text = post_data.get("text", "")
        post_uid = post_data.get("post_uid", "unknown")
        self.logger.info("Classifying clarity", post_uid=post_uid, text_length=len(post_text))
                
        # Get cached LLM instance
        llm = self._get_llm()
        
        # Create structured output version
        structured_llm = llm.with_structured_output(ClarityClassification)
        
        # Prepare content with media
        prepared = prepare_fact_check_input(post_data)
        msg = AUTHOR_CONTEXT_CONTENT_PROMPT.format(**prepared)
        content = format_content_with_media({
            "text": msg,
            "media": prepared.get("media", [])
        })
        
        # Get structured output from LLM (with tracing disabled)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
        with self.no_tracing:
            result: ClarityClassification = await structured_llm.ainvoke(messages)
        
        classification = {
            "type": "single",
            "value": result.clarity,
            "reason": result.reason,
            "confidence": result.confidence
        }
        
        
        self.logger.info(
            "Clarity classification completed",
            post_uid=post_uid,
            clarity=result.clarity,
            confidence=result.confidence
        )
        
        # Validate output
        if not await self.validate_output(classification):
            self.logger.error("Invalid classification output", post_uid=post_uid, classification=classification)
            raise ValueError("Invalid classification output")
        
        self.logger.info("Clarity classification complete", post_uid=post_uid)
        return classification

########################################################
# Prompts
########################################################

system_prompt = """# Fact-Checking Clarity Classifier

You are an AI model tasked with rating social media posts based on **how clear
and straightforward the fact-checking job would be**. Begin with a concise
checklist (3-5 bullets) of what you will assess; keep items conceptual, not
implementation-level.

Your job is to analyze a post's content and assign it a **clarity score from 1
to 5**, where the score indicates how obvious and verifiable the factual claims
are.

## Clarity Score Definitions

- **1 - Very Unclear**: The post contains vague statements, opinions without
  factual basis, or claims so general/abstract that fact-checking is nearly
  impossible. No clear falsifiable statements.
  
- **2 - Unclear**: The post makes some claims but they're buried in rhetoric,
  mixed heavily with opinion, or lack specificity needed for verification.
  Fact-checking would require significant interpretation.
  
- **3 - Moderate**: The post contains identifiable claims that could be checked,
  but either the sources would be disputed/unclear, or the claims mix facts with
  interpretation in ways that make verification partially subjective.
  
- **4 - Clear**: The post makes specific, verifiable claims with clear factual
  assertions. Sources exist but might require some searching. The fact-checking
  job is straightforward though not trivial.
  
- **5 - Very Clear**: The post makes explicit, specific factual claims that can
  be directly verified against authoritative sources. Statistics, dates, quotes,
  or scientific facts are clearly stated. Fact-checking is obvious and sources
  are likely readily available.

## Classification Guidelines

- Focus on **verifiability of claims**, not their truthfulness
- Consider **specificity** - specific numbers, dates, and quotes rate higher
- Evaluate **source availability** - claims about well-documented topics rate higher
- Pure opinions or predictions cannot be fact-checked (rate as 1)
- Vague generalizations without specific claims rate low (1-2)
- Specific statistics, scientific claims, or historical facts rate high (4-5)

After generating your initial rating, validate that your reasoning references
specific aspects of the post that justify the clarity score.

## Output Format

Return your response strictly in **JSON** following this schema:

```json
{{
  "clarity": "clarity_1" | "clarity_2" | "clarity_3" | "clarity_4" | "clarity_5",
  "confidence": 0.0–1.0,
  "reason": "1–3 sentences explaining the rating, highlighting what makes the
  fact-checking job clear/unclear based on the post's specific claims or lack thereof."
}}
```

## Examples

**Example 1 - Very Clear (5):**
Input: "The COVID-19 vaccine has a 95% efficacy rate according to Pfizer's Phase 3
trial according to results published in NEJM."

Output:
```json
{{
  "clarity": "clarity_5",
  "confidence": 0.95,
  "reason": "Post makes specific, verifiable claims with exact statistics,
  and publication details that can be directly checked against the medical 
  journal cited."
}}
```

**Example 2 - Unclear (2):**
Input: "The government is hiding the truth about what's really going on. Wake up
people, they don't want you to know what's happening behind closed doors!"

Output:
```json
{{
  "clarity": "clarity_2",
  "confidence": 0.90,
  "reason": "Post makes vague conspiratorial claims without any specific,
  verifiable statements. No concrete facts, dates, or sources mentioned that
  could be fact-checked."
}}
```

**Example 3 - Moderate (3):**
Input: "Studies show that remote work is more productive than office work. Many
companies are seeing better results with employees working from home."

Output:
```json
{{
  "clarity": "clarity_3",
  "confidence": 0.85,
  "reason": "Post references 'studies' and makes claims about productivity but
  lacks specific citations, statistics, or company names, making verification
  possible but requiring significant research to identify which studies are meant."
}}
```"""
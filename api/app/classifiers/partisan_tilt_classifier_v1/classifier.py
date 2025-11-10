"""
Partisan Tilt Classifier V1

A partisan tilt classifier that uses OpenAI's structured output to categorize
social media posts by political orientation.
"""

from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from app.classifiers.base import BaseClassifier
from app.classifiers.registry import register_classifier
from app.classifiers.shared.tweet_utils import prepare_fact_check_input, format_content_with_media, AUTHOR_CONTEXT_CONTENT_PROMPT
from app.config import settings

# Pydantic model for structured output
class PartisanTiltClassification(BaseModel):
    """Structured output for partisan tilt classification"""

    reason: str = Field(description="Explanation of why this partisan tilt applies")
    # From a list of literals
    tilt: Literal[
        "left_leaning",
        "center",
        "right_leaning",
    ] = Field(description="Partisan tilt")
    confidence: float = Field(description="Confidence score for the partisan tilt choice (0-1)")

@register_classifier
class PartisanTiltClassifierV1(BaseClassifier):
    slug = "partisan-tilt-v1"
    """
    Partisan Tilt Classifier
    """
    
    def __init__(self, slug: str, output_schema: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        super().__init__(slug, output_schema, config)
        self._llm = None  # Cached LLM instance
    
    def _get_llm(self) -> ChatOpenAI:
        """Get or create cached LLM instance"""
        if self._llm is None:
            model_name = self.config.get("model", "gpt-5-nano")
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
        Classify a post according to its partisan tilt
        
        Args:
            post_data: Dict containing post information
            
        Returns:
            Classification result with type and values array
        """
        post_text = post_data.get("text", "")
        self.logger.info("Classifying partisan tilt", text_length=len(post_text))
                
        # Get cached LLM instance
        llm = self._get_llm()
        
        # Create structured output version
        structured_llm = llm.with_structured_output(PartisanTiltClassification)
        
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
            result:PartisanTiltClassification = await structured_llm.ainvoke(messages)
        
        classification = {
            "type": "single",
            "value": result.tilt,
            "reason": result.reason,
            "confidence": result.confidence
        }
        
        
        self.logger.info(
            "Partisan tilt classification completed",
            tilt=result.tilt,
        )
        
        # Validate output
        if not await self.validate_output(classification):
            self.logger.error("Invalid classification output", classification=classification)
            raise ValueError("Invalid classification output")
        
        self.logger.info("Partisan tilt classification complete")
        return classification

########################################################
# Prompts
########################################################

system_prompt = """# Political Orientation Classifier (U.S. Context)

You are an AI model tasked with classifying social media posts by **political
orientation** from a **U.S. perspective**. Begin with a concise checklist (3-7
bullets) of what you will do; keep items conceptual, not implementation-level.

Your job is to analyze a post's content and assign it to one of three
categories: **Left-leaning**, **Center**, or **Right-leaning**, and provide a
corresponding confidence score.

## Category Definitions

- **Left-leaning (Liberal/Progressive)**: Posts that align with or promote views
  traditionally associated with liberal, progressive, or Democratic Party
  positions in the U.S. (e.g., climate action, gun control, reproductive rights,
  racial justice, higher taxes on the wealthy).
- **Center (Moderate/Neutral)**: Posts that reflect politically mixed,
  nonpartisan, fact-based perspectives, or support balanced/compromise-driven
  viewpoints without clear ideological framing.
- **Right-leaning (Conservative)**: Posts that align with or advocate for views
  typical of conservative or Republican Party positions in the U.S. (e.g., gun
  rights, opposition to abortion, limited government, tax cuts, traditional
  values, skepticism toward climate policy).

## Classification Rules

- **Examine only the content of the post**; do not infer based on the author's
  identity or intent.
- If there is **no obvious political framing** (e.g., the post is neutral,
  factual, or off-topic), classify it as **Center**.
- Provide a **confidence score** (range: 0–1) reflecting the strength and
  clarity of ideological cues in the text.
- Accompany each classification with a concise explanation, referencing the
  relevant language or framing found in the post.

After generating your initial classification, validate that the explanation
references specific language or framing from the post. If the rationale is too
vague or does not justify the classification, self-correct before returning your
output.

## Output Format

Return your response strictly in **JSON** following this schema:

```json
{{
  "tilt": "left_leaning" | "center" | "right_leaning",
  "confidence": 0.0–1.0,
  "reason": "1–3 sentences explaining the classification, highlighting key
  language or framing in the post."
}}
```

## Example

**Input post:**

"New research shows guns are responsible for 95 percent of all crime. We need
stricter background checks for gun sales to protect our communities."

**Output:**

```json
{{
  "tilt": "left_leaning",
  "confidence": 0.95,
  "reason": "The post highlights negative aspects of gun ownership and
  advocates stricter gun control, which is a position commonly associated with
  the U.S. political left."
}}
```"""

human_prompt = """Analyze the following social media post and classify it by 
political tilt:

POST TEXT:
{post_text}"""
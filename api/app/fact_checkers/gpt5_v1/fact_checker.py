"""
GPT-5 Fact Checker V1

A simple fact checker that uses OpenAI's GPT-5 with structured output to analyze
social media posts for factual accuracy.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
import structlog
from ..base import BaseFactChecker, FactCheckResult
from ..registry import register_fact_checker
from ..shared.enums import VERDICT_LITERALS_LLM
from app.classifiers.shared.tweet_utils import prepare_fact_check_input, format_content_with_media
from app.config import settings

logger = structlog.get_logger()


# Pydantic model for structured output
class FactCheckAnalysis(BaseModel):
    """Structured output for fact check analysis"""
    
    class ClaimAnalysis(BaseModel):
        """Analysis of an individual claim"""
        claim: str = Field(description="The specific claim being analyzed")
        verdict: VERDICT_LITERALS_LLM = Field(  # Use LLM version without "error"
            description="The verdict for this specific claim"
        )
        explanation: str = Field(description="Explanation of the verdict")
        evidence: Optional[str] = Field(default=None, description="Supporting evidence or lack thereof")
    
    class Source(BaseModel):
        """Reference source"""
        description: str = Field(description="Description of the source")
        relevance: str = Field(description="Why this source is relevant")
    
    markdown_analysis: str = Field(
        description="Full markdown-formatted fact check analysis with headers, bullet points, etc."
    )
    overall_verdict: VERDICT_LITERALS_LLM = Field(  # Use LLM version without "error"
        description="Overall verdict for the entire post"
    )
    confidence: float = Field(
        description="Confidence score for the overall verdict (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    claims: List[ClaimAnalysis] = Field(
        default=[],
        description="Individual claims analyzed"
    )
    sources: List[Source] = Field(
        default=[],
        description="Sources that would be helpful for verification"
    )


@register_fact_checker
class GPT5FactCheckerV1(BaseFactChecker):
    """Simple GPT-5 based fact checker using structured output"""
    
    slug = "gpt5_fact_checker_v1"
    name = "GPT-5 Fact Checker"
    description = "Uses GPT-5 to analyze factual claims and provide fact-checking"
    version = "1.0.0"
    
    def __init__(self):
        super().__init__()
        self._llm = None  # Cached LLM instance
    
    async def should_run(self, post_data: Dict[str, Any], classifications: List[Dict[str, Any]]) -> Dict[str, Any]:        
        return {
            "should_run": False, # Turn off for now, this is not a good fact checker
            "reason": "General purpose fact checker"
        }
    
    def _get_llm(self) -> Optional[ChatOpenAI]:
        """Get or create cached LLM instance"""
        if self._llm is None:
            if not settings.openai_api_key:
                logger.warning("OPENAI_API_KEY not configured")
                return None
            
            reasoning = {
                "effort": "low",  # Low effort for faster responses
                "summary": None,
            }
            
            self._llm = ChatOpenAI(
                model="gpt-5",
                api_key=settings.openai_api_key,
                output_version="responses/v1",
                reasoning=reasoning,
            )
        return self._llm
    
    async def fact_check(self, post_data: Dict[str, Any]) -> FactCheckResult:
        """Perform fact checking using GPT-5"""
        
        if not await self.validate_input(post_data):
            raise ValueError("Invalid input data")
        
        # Get LLM instance
        llm = self._get_llm()

        try:
            # Create structured output version
            structured_llm = llm.with_structured_output(FactCheckAnalysis)
            
            # Prepare content with media
            prepared = prepare_fact_check_input(post_data)
            content = format_content_with_media(prepared)
            
            # Get structured output from LLM
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
            result = await structured_llm.ainvoke(messages)
            
            # Convert to FactCheckResult
            return FactCheckResult(
                text=result.markdown_analysis,
                verdict=result.overall_verdict,
                confidence=result.confidence,
                claims=[
                    {
                        "claim": c.claim,
                        "verdict": c.verdict,
                        "explanation": c.explanation,
                        "evidence": c.evidence
                    }
                    for c in result.claims
                ],
                sources=[
                    {
                        "description": s.description,
                        "relevance": s.relevance
                    }
                    for s in result.sources
                ],
                metadata={
                    "model": "gpt-5",
                    "fact_checker": self.slug,
                    "post_uid": post_data.get("post_uid")
                }
            )
            
        except Exception as e:
            logger.error(f"Error in GPT-5 fact checking: {str(e)}", 
                        post_uid=post_data.get("post_uid"))
            raise

########################################################
# Prompts
########################################################

system_prompt = """You are a professional fact-checker with expertise in identifying and verifying claims. Your task is to:

1. Identify all factual claims in the given social media post
2. Evaluate each claim's accuracy based on your knowledge
3. Provide an overall verdict for the post
4. Suggest sources that could be used for verification

## Verdict Categories:

- **true**: All fact-checkable claims are supported by verifiable evidence
- **false**: Entirely inaccurate content with no factual basis
- **altered**: Media that has been digitally manipulated or synthesized
- **partly_false**: Content that mixes accurate and inaccurate information
- **missing_context**: Content that is technically accurate but misleading by omission
- **satire**: Content meant as humor, parody, or critique through exaggeration
- **unable_to_verify**: The fact-checkable claims could not be verified
- **not_fact_checkable**: None of the claims are fact-checkable (opinions, speculations)
- **not_worth_correcting**: Contains minor factual inaccuracies not worth correcting (e.g., technical errors that don't undermine the main point)

## Analysis Requirements:

1. **Identify Claims**: Extract specific, verifiable statements
2. **Evaluate Each Claim**: Assess accuracy individually
3. **Overall Assessment**: Synthesize individual verdicts into overall conclusion
4. **Evidence**: Note what evidence supports or contradicts claims
5. **Sources**: Suggest authoritative sources for verification

## Markdown Formatting:

Your markdown analysis should include:
- Clear headers (##) for sections
- Bullet points for lists
- **Bold** for emphasis on key findings
- Proper citation format for sources

Be thorough but concise. Focus on facts, not opinions. Limit your response to
300 words."""

human_prompt = """Fact-check the following {platform} post:

Author: @{author}
Content: {post_text}

Provide a comprehensive fact-check analysis."""
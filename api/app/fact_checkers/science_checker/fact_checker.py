"""
Science Fact Checker V1

A fact checker specialized for analyzing statements that have scentific answers.
"""

from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import structlog
from ..base import BaseFactChecker, FactCheckResult
from ..registry import register_fact_checker
from app.config import settings

logger = structlog.get_logger()


# Pydantic model for structured output
class FactCheckAnalysis(BaseModel):
    """Structured output for fact check analysis"""
    
    class Source(BaseModel):
        """Reference source"""
        description: str = Field(description="Description of the source")
        relevance: str = Field(description="Why this source is relevant")
    
    analysis: str = Field(
        description="Full markdown-formatted fact check analysis with headers, bullet points, etc."
    )
    verdict: Literal["true", "false", "misleading", "unverifiable", "needs_context"] = Field(
        description="Overall verdict for the entire post"
    )
    confidence: float = Field(
        description="Confidence score for the overall verdict (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    sources: List[Source] = Field(
        default=[],
        description="Sources that would be helpful for verification"
    )


@register_fact_checker
class ScienceFactCheckerV1(BaseFactChecker):
    """Science focused fact checker"""
    
    slug = "science_checker_v1"
    name = "Science Fact Checker"
    description = "Specialized fact checker for science-related claims"
    version = "1.0.0"
    
    def __init__(self):
        super().__init__()
        self._llm = None  # Cached LLM instance
    
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
        if not llm:
            raise ValueError("LLM not configured")
        
        try:
            # Create structured output version
            structured_llm = llm.with_structured_output(FactCheckAnalysis)
            
            # Prepare the prompt
            post_text = post_data.get("text", "")
            author = post_data.get("author_handle", "Unknown")
            platform = post_data.get("platform", "social media")
            
            # Get structured output from LLM
            chat_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", human_prompt)
            ])
            chain = chat_template | structured_llm
            
            result = await chain.ainvoke({
                "platform": platform,
                "author": author,
                "post_text": post_text
            })
            
            # Convert to FactCheckResult
            return FactCheckResult(
                text=result.analysis,
                verdict=result.verdict,
                confidence=result.confidence,
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
            logger.error(f"Error in Science fact checking: {str(e)}", 
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

- **true**: The claim(s) are accurate and supported by evidence
- **false**: The claim(s) are demonstrably incorrect
- **misleading**: Contains some truth but presented in a way that could deceive
- **unverifiable**: Cannot be verified with available information
- **needs_context**: True but missing important context that changes interpretation

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

Be thorough but concise. Focus on facts, not opinions."""

human_prompt = """Fact-check the following {platform} post:

Author: @{author}
Content: {post_text}

Provide a comprehensive fact-check analysis."""
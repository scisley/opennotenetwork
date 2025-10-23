"""
Science Fact Checker V1

A LangGraph-based fact checker specialized for analyzing scientific claims through
adversarial debate between an advocate and adversary agent.
"""

import uuid
from typing import TypedDict, Optional, Literal, Annotated, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI
from langchain_core.load import dumpd
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.runnables import RunnableConfig
import structlog
from ..base import BaseFactChecker, FactCheckResult
from ..registry import register_fact_checker
from ..shared.enums import DEFAULT_VERDICT
from app.classifiers.shared.tweet_utils import prepare_fact_check_input, format_content_with_media, AUTHOR_CONTEXT_CONTENT_PROMPT
from app.config import settings

logger = structlog.get_logger()

# ============================================================================
# LLM CONFIGURATION - Centralized settings for easy debugging
# ============================================================================

# Model selection - change these to switch between fast/powerful models
FAST_MODEL = "gpt-5-mini"  # For quick operations like eligibility checks
MAIN_MODEL = "gpt-5"  # For main fact-checking agents

# Reasoning configuration
REASONING_EFFORT = "medium"  # Options: "minimal", "low", "medium", "high"
REASONING_SUMMARY = "auto"  # Options: "auto", "none", number of words

# Timeout configuration (in seconds)
TIMEOUTS = {
    "minimal": 5 * 60,
    "low": 5 * 60,
    "medium": 10 * 60,
    "high": 15 * 60,
}


def get_llm(model_type: str = "main", use_reasoning: bool = True) -> ChatOpenAI:
    """Get a configured LLM instance.
    
    Args:
        model_type: "fast" for quick operations or "main" for thorough analysis
        use_reasoning: Whether to enable reasoning (for models that support it)
    
    Returns:
        Configured ChatOpenAI instance
    """
    model = FAST_MODEL if model_type == "fast" else MAIN_MODEL
    
    kwargs = {
        "model": model,
        "api_key": settings.openai_api_key,
        "output_version": "responses/v1",
        "temperature": 0,
        "max_retries": 1,
    }
    
    if use_reasoning and model_type == "main":
        kwargs["reasoning"] = {
            "effort": REASONING_EFFORT,
            "summary": REASONING_SUMMARY,
        }
        kwargs["timeout"] = TIMEOUTS[REASONING_EFFORT]
    
    return ChatOpenAI(**kwargs)


# Define the state schema for LangGraph
class FactCheckState(TypedDict):
    """State for the science fact checking agent."""
    # Input
    text: Optional[str]
    context: Optional[str]
    author: Optional[str]
    media: Optional[List[Dict]]
    
    # Processing state
    is_eligible: Optional[bool]  # Whether post is eligible for fact checking
    eligibility_reason: Optional[str]  # Why eligible or not
    
    # Context gathering
    additional_context: Optional[str]  # Additional info gathered
    
    # Round of debate (not used yet)
    round: int
    
    # Debate messages
    advocate: Annotated[List[AnyMessage], add_messages]
    adversary: Annotated[List[AnyMessage], add_messages]
    
    # Analysis results
    summary: Optional[str]  # The fact check analysis
    verdict: Optional[str]  # Final verdict
    confidence: Optional[float]  # Confidence in the verdict


class IsEligible(BaseModel):
    """Eligibility check result"""
    is_eligible: bool
    eligibility_reason: str = Field(
        description="Very short reason for eligibility. Do not restate what is in the provided data."
    )


class DebateOutput(BaseModel):
    """Debate agent output"""
    classification: Literal["misinformed_or_potentially_misleading", "not_misleading"]
    reason: str = Field(description="A short reason for the classification.")


class Summary(BaseModel):
    """Final summary output"""
    summary: str
    verdict: Literal["misinformed_or_potentially_misleading", "not_misleading"]
    confidence: float = Field(description="A number between 0 and 1 indicating the confidence in the verdict.", ge=0, le=1)


# Prompts for eligibility checking
ELIGIBILITY_SYSTEM_PROMPT = """
Check if a piece of content is eligible for science fact checking.

Consider:
1. Is the main point science-related?
2. Is the main point a factual claim that can be verified?
"""

# Prompts for advocate agent
SYS_ADVOCATE_PROMPT = """
You are a fact checker within a collaborative, science-based fact checking team.
Your job on this team is to analyze a claim and attempt to prove it is ACCURATE.
Another member of the team will attempt to prove it is inaccurate.

Write out your findings using Markdown.
"""

# Prompts for adversary agent
SYS_ADVERSARY_PROMPT = """
You are a fact checker within a collaborative, science-based fact checking team.
Your job on this team is to analyze a claim and attempt to prove it is
INACCURATE. Another member of the team will attempt to prove it is accurate.

Write out your findings using Markdown.
"""

# Prompts for summarizer
SYS_SUMMARY_PROMPT = """
You are a member of a collaborative, science-based fact-checking team. Your role
is to create a concise fact-check summary by integrating input from two
independent agents: an advocate (supporting the original claims) and an
adversary (challenging or disproving those claims).

Begin with a concise checklist (3-7 bullets) of the work you will do. Keep
checklist items conceptual and not implementation-level. Do NOT include the
checklist in the final output. 

Your goal is to write a clear, balanced summary in Markdown format that is
accessible to readers at a 6th-grade reading level, free of technical jargon,
and approachable for people unfamiliar with the topic. Strive for brevity.

Structure your summary with the following Markdown headers and sections:

- # Main Claims: List and briefly describe the main claims, ordered from most
  outlandish to least. Only include claims
- # Summary: Write a one-paragraph summary expressing your overall conclusions
  about the claims.
- # Details: Summarize both supporting and opposing scientific evidence from the
  provided sources. If there is no supporting scientific evidence, say so.
  Otherwise, note any ambiguity or conflict. This section should be structured
  as short paragraphs without any additional sub headings.

Output Format:
- Use only the specified Markdown section headers (# Main Claims, # Summary,
# Details).
- Place links to supporting evidence inline, immediately following the
information they support, using incrementing numbers for the link text. (e.g.,
"Scientists found no evidence to support this claim
[[1]](http://example.com/evidence).")
- IMPORTANT: Use conversational, but neutral language. The text should be 
persuasive even to people who strongly agree or disagree with the claims. Avoid
calling anything a "trick" or using language like "debunked".

Before writing the summary, ensure each section is complete and adheres to
clarity and accessibility requirements. After completing the summary, quickly
review for readability, proper link placement, and adherence to output format.
Self-correct any issues found before finalizing the output.
"""

SUMMARY_PROMPT = """
## Original text:
Author: {author}
Context: {context}
Content:
{text}

## Advocate's findings: 
{advocate_findings}

## Adversary's findings: 
{adversary_findings}
"""


def get_text_from_message(message: AnyMessage) -> Optional[str]:
    """Extract text content from a message."""
    # Handle the format from your notebook where content is a list of dicts
    if hasattr(message, 'content'):
        if isinstance(message.content, str):
            return message.content
        elif isinstance(message.content, list):
            # Find the text content in the list
            for item in message.content:
                if isinstance(item, dict) and item.get('type') == 'text':
                    return item.get('text')
    return None


# Define node functions
async def check_eligibility(state: FactCheckState) -> Dict:
    """Check if the post is eligible for science fact checking"""
    # logger.info("Starting check_eligibility node")
    
    # llm_fast = get_llm(model_type="fast", use_reasoning=False)
    # structured_llm = llm_fast.with_structured_output(IsEligible)
    

    # msg = AUTHOR_CONTEXT_CONTENT_PROMPT.format(
    #     author=state["author"],
    #     context=state["context"],
    #     text=state["text"]
    # )
    
    # # Use the new format_content_with_media function
    # content = format_content_with_media({
    #     "text": msg,
    #     "media": state.get("media", [])
    # })
    
    # messages = [
    #     {"role": "system", "content": ELIGIBILITY_SYSTEM_PROMPT},
    #     {"role": "user", "content": content}
    # ]

    # result: IsEligible = await structured_llm.ainvoke(messages)
    
    # return result.model_dump()
    return {
        "is_eligible": True,
        "eligibility_reason": "Manual override"
    }


async def gather_context(state: FactCheckState) -> Dict:
    """
    Gather additional context needed for fact checking.
    
    This could include:
    - Scraping linked content
    
    Stub implementation for now.
    """
    logger.info("Starting gather_context node (stub - returning None)")
    # Stub implementation - exactly as in your notebook
    return {
        "additional_context": None
    }


async def advocate_agent(state: FactCheckState) -> Dict:
    """Agent that searches for evidence supporting the claims"""
    logger.info("Starting advocate_agent node")
    
    llm = get_llm(model_type="main", use_reasoning=True)
    
    tool = {"type": "web_search_preview"}
    agent = llm.bind_tools([tool])
    
    msg = AUTHOR_CONTEXT_CONTENT_PROMPT.format(
        author=state["author"],
        context=state["context"],
        text=state["text"]
    )
    
    # Use the new format_content_with_media function
    content = format_content_with_media({
        "text": msg,
        "media": state.get("media", [])
    })
    
    messages = [
        {"role": "system", "content": SYS_ADVOCATE_PROMPT},
        {"role": "user", "content": content}
    ]

    science_search_config = RunnableConfig(run_name="ScienceAdvocate")
    out = await agent.ainvoke(messages, config=science_search_config)
    return {
        "advocate": out
    }


async def adversary_agent(state: FactCheckState) -> Dict:
    """Agent that searches for evidence refuting the claims"""
    logger.info("Starting adversary_agent node")
    
    llm = get_llm(model_type="main", use_reasoning=True)
    
    tool = {"type": "web_search_preview"}
    agent = llm.bind_tools([tool])
    
    msg = AUTHOR_CONTEXT_CONTENT_PROMPT.format(**state)
    
    # Use the new format_content_with_media function
    content = format_content_with_media({
        "text": msg,
        "media": state.get("media", [])
    })
    
    messages = [
        {"role": "system", "content": SYS_ADVERSARY_PROMPT},
        {"role": "user", "content": content}
    ]

    science_critique_config = RunnableConfig(run_name="ScienceAdversary")
    out = await agent.ainvoke(messages, config=science_critique_config)
    return {
        "adversary": out
    }


async def summarize(state: FactCheckState) -> Dict:
    """Summarize the debate and create final fact check"""
    logger.info("Starting summarize node")
    
    llm = get_llm(model_type="main", use_reasoning=True)
    
    summary_llm = llm.with_structured_output(Summary)
    
    # Get text from advocate and adversary messages
    advocate_findings = ""
    if state.get("advocate"):
        advocate_findings = get_text_from_message(state["advocate"][-1]) or ""
    
    adversary_findings = ""
    if state.get("adversary"):
        adversary_findings = get_text_from_message(state["adversary"][-1]) or ""
    
    sys_prompt = SYS_SUMMARY_PROMPT.format(
        author=state["author"],
        context=state["context"],
        text=state["text"],
        advocate_findings=advocate_findings,
        adversary_findings=adversary_findings
    )
    
    user_msg = SUMMARY_PROMPT.format(
        author=state["author"],
        context=state["context"],
        text=state["text"],
        advocate_findings=advocate_findings,
        adversary_findings=adversary_findings
    )
    
    # Use the new format_content_with_media function
    content = format_content_with_media({
        "text": user_msg,
        "media": state.get("media", [])
    })
    
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": content}
    ]
    
    summary: Summary = await summary_llm.ainvoke(messages)
    return summary.model_dump()


# Conditional edge function
def should_continue(state: FactCheckState) -> Literal["gather_context", END]:
    """Decide whether to continue with fact checking based on eligibility."""
    if state.get("is_eligible", True):
        return "gather_context"
    else:
        return END


def build_science_fact_checker() -> StateGraph:
    """
    Build the science fact checking agent graph.
    
    Returns:
        Compiled StateGraph
    """
    
    # Initialize the graph
    builder = StateGraph(FactCheckState)
    
    # Add nodes
    builder.add_node("check_eligibility", check_eligibility)
    builder.add_node("gather_context", gather_context)
    builder.add_node("advocate_agent", advocate_agent)
    builder.add_node("adversary_agent", adversary_agent)
    builder.add_node("summarize", summarize)
    
    # Add edges
    builder.add_edge(START, "check_eligibility")
    builder.add_conditional_edges("check_eligibility", should_continue)
    builder.add_edge("gather_context", "advocate_agent")
    builder.add_edge("gather_context", "adversary_agent")
    builder.add_edge(["advocate_agent", "adversary_agent"], "summarize")
    builder.add_edge("summarize", END)
    
    # Compile the graph
    graph = builder.compile()
    
    return graph


@register_fact_checker
class ScienceFactCheckerV1(BaseFactChecker):
    """Science focused fact checker using LangGraph adversarial debate"""
    
    slug = "science_checker_v1"
    name = "Science Fact Checker"
    description = "Specialized fact checker for science-related claims using adversarial debate"
    version = "3.0.0"
    
    def __init__(self):
        super().__init__()
    
    async def should_run(self, post_data: Dict[str, Any], classifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determine if this fact checker should run based on classifications.
        Runs on science/health/climate domains WITHOUT video content.
        """
        # Check for video content first - we don't run on video posts
        has_video = False
        for classification in classifications:
            if classification.get("classifier_slug") == "media-type-v1":
                data = classification.get("classification_data", {})
                if data.get("type") == "multi":
                    values = data.get("values", [])
                    for v in values:
                        if v.get("value") == "has_video":
                            has_video = True
                            break
        
        if has_video:
            return {
                "should_run": False,
                "reason": "Cannot analyze posts with video content"
            }
        
        # Check for relevant domain classifications
        # eligible_domains = ["science_engineering", "health_medicine", "nature_climate"]
        # Longer list so we can analyze more posts
        eligible_domains = [
            "science_engineering", 
            "health_medicine", 
            "nature_climate",
        ]
        for classification in classifications:
            if classification.get("classifier_slug") == "domain-classifier-v1":
                data = classification.get("classification_data", {})
                if data.get("type") == "multi":
                    values = data.get("values", [])
                    for v in values:
                        if v.get("value") in eligible_domains:
                            return {
                                "should_run": True,
                                "reason": f"Post classified as {v.get('value')} domain"
                            }
        
        return {
            "should_run": False,
            "reason": "No science/health/climate classification found"
        }
    
    def build_graph(self):
        """Build and return the LangGraph for fact checking"""
        return build_science_fact_checker()
    
    def prepare_state(self, post_data: Dict[str, Any]) -> FactCheckState:
        """Prepare initial state for the graph from post data"""
        # Use the standardized fact check input preparation
        if post_data.get("platform") == "x":
            formatted_data = prepare_fact_check_input(post_data)
            # Extract just the fields needed for FactCheckState
            state_data = {
                "text": formatted_data["text"],
                "context": formatted_data["context"],
                "author": formatted_data["author"],
                "media": formatted_data["media"]
            }
        else:
            # For other platforms, raise error (we don't support them yet)
            raise ValueError(f"Platform '{post_data.get('platform')}' is not supported. Only 'x' is supported.")
        
        # Initialize state for LangGraph
        return FactCheckState(
            **state_data,
            round=0,
            is_eligible=None,
            eligibility_reason=None,
            additional_context=None,
            advocate=[],
            adversary=[],
            summary=None,
            verdict=None,
            confidence=None
        )
    
    def map_verdict(self, verdict: str) -> str:
        """Map LangGraph verdict to Meta's taxonomy"""
        verdict_mapping = {
            "misinformed_or_potentially_misleading": "partly_false",
            "not_misleading": "true",
            "false": "false",
            "misleading": "partly_false"
        }
        return verdict_mapping.get(verdict, verdict or DEFAULT_VERDICT)
    
    async def stream_fact_check(self, post_data: Dict[str, Any]):
        """Stream fact check updates from LangGraph execution"""
        
        if not await self.validate_input(post_data):
            raise ValueError("Invalid input data")
        
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        # Import LangChain serialization
        from langchain_core.load import dumpd
        
        # Generate UUID for this fact check
        fact_check_id = str(uuid.uuid4())
        
        try:
            # Build graph and prepare state
            graph = self.build_graph()
            initial_state = self.prepare_state(post_data)
            
            updates = []
            final_result = None
            
            # Stream execution
            async for chunk in graph.astream(initial_state, stream_mode="updates"):
                # Log which node produced this update
                node_names = list(chunk.keys()) if isinstance(chunk, dict) else []
                if node_names:
                    logger.info(f"Received update from node(s): {', '.join(node_names)}")
                
                # Serialize the chunk
                serialized_chunk = dumpd(chunk)
                updates.append(serialized_chunk)
                
                # Accumulate final result
                if isinstance(chunk, dict):
                    if final_result is None:
                        final_result = {}
                    for key, value in chunk.items():
                        if isinstance(value, dict):
                            final_result.update(value)
                
                # Yield update in standard format
                yield {
                    "updates": updates,
                    "verdict": self.map_verdict(final_result.get("verdict")) if final_result else None,
                    "summary": final_result.get("summary") if final_result else None,
                    "confidence": final_result.get("confidence", 0.0) if final_result else None,
                    "is_eligible": final_result.get("is_eligible") if final_result else None,
                    "eligibility_reason": final_result.get("eligibility_reason") if final_result else None,
                    "metadata": {
                        "fact_checker": self.slug,
                        "fact_check_id": fact_check_id,
                        "post_uid": post_data.get("post_uid"),
                        "llm_config": {
                            "fast_model": FAST_MODEL,
                            "main_model": MAIN_MODEL,
                            "reasoning_effort": REASONING_EFFORT,
                            "reasoning_summary": REASONING_SUMMARY,
                            "timeout_seconds": TIMEOUTS[REASONING_EFFORT],
                        }
                    },
                    "raw_output": {
                        "fact_check_id": fact_check_id,
                        "updates": updates,
                    },
                    "claims": [],  # Could extract from result if available
                    "sources": [],  # Could extract from result if available
                }
            
        except Exception as e:
            logger.error(f"Error in Science streaming fact check: {str(e)}", 
                        post_uid=post_data.get("post_uid"),
                        fact_check_id=fact_check_id)
            raise
    
    async def fact_check(self, post_data: Dict[str, Any]) -> FactCheckResult:
        """Perform fact checking using LangGraph"""
        
        if not await self.validate_input(post_data):
            raise ValueError("Invalid input data")
        
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        # Generate UUID for this fact check
        fact_check_id = str(uuid.uuid4())
        
        try:
            # Prepare initial state
            initial_state = self.prepare_state(post_data)
            
            # Build and run the graph
            graph = self.build_graph()
            graph_config = RunnableConfig(run_name="ScienceFactCheck")
            result = await graph.ainvoke(initial_state, config=graph_config)
            
            # Map verdict to expected format
            final_verdict = self.map_verdict(result.get("verdict"))
            
            # Extract sources from advocate and adversary findings
            sources = []
            
            # Create raw_output with serialized result
            raw_output = {
                "fact_check_id": fact_check_id,
                "updates": [],  # Empty for non-streaming execution
                "final_result": dumpd(result)
            }
            
            # Convert to FactCheckResult
            return FactCheckResult(
                text=result.get("summary", "No fact check could be generated"),
                verdict=final_verdict,
                confidence=result.get("confidence", 0.0),
                sources=sources,
                metadata={
                    "fact_checker": self.slug,
                    "fact_check_id": fact_check_id,
                    "post_uid": post_data.get("post_uid"),
                    "is_eligible": result.get("is_eligible"),
                    "eligibility_reason": result.get("eligibility_reason"),
                    "llm_config": {
                        "fast_model": FAST_MODEL,
                        "main_model": MAIN_MODEL,
                        "reasoning_effort": REASONING_EFFORT,
                        "reasoning_summary": REASONING_SUMMARY,
                        "timeout_seconds": TIMEOUTS[REASONING_EFFORT],
                    }
                },
                raw_output=raw_output
            )
            
        except Exception as e:
            logger.error(f"Error in Science fact checking: {str(e)}", 
                        post_uid=post_data.get("post_uid"),
                        fact_check_id=fact_check_id)
            raise
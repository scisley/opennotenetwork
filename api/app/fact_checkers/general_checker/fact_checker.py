"""
General Fact Checker V1

A LangGraph-based fact checker specialized for analyzing claims through
adversarial debate between an advocate and adversary agent.
"""

import uuid
import structlog
from typing import TypedDict, Optional, Literal, Annotated, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.load import dumpd
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.runnables import RunnableConfig
from ..base import BaseFactChecker, FactCheckResult
from ..registry import register_fact_checker
from ..shared.enums import VERDICT_LITERALS, ACCURACY_LITERALS_LLM, VERDICT_LITERALS_LLM, DEFAULT_VERDICT
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

DEBUG_MODE = False

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
    """State for the fact checking agent."""
    # Input
    text: Optional[str]
    context: Optional[str]
    author: Optional[str]
    media: Optional[List[Dict]]
    
    # Processing state
    is_eligible: Optional[bool]  # Whether post is eligible for fact checking
    eligibility_reason: Optional[str]  # Why eligible or not
    messages: Annotated[List[AnyMessage], add_messages]
    
    # Round of debate (not used yet)
    round: int
    
    # Debate messages
    advocate: Annotated[List[AnyMessage], add_messages]
    adversary: Annotated[List[AnyMessage], add_messages]
    
    # Analysis results
    body: Optional[str]  # The fact check analysis
    claims: List[dict[str, Any]]
    verdict: Optional[VERDICT_LITERALS]  # Final verdict

class IsEligible(BaseModel):
    """Eligibility check result"""
    is_eligible: bool
    eligibility_reason: str = Field(
        description="Very short reason for eligibility. Do not restate what is in the provided data."
    )

class Claim(BaseModel):
    """
    A summary of an individual claim. This is meant to be short. Further details
    are provided elsewhere.
    """
    claim: str
    accuracy: ACCURACY_LITERALS_LLM  # Use LLM version without "error"
    reason: str = Field(description="A one sentence explanation of the verdict")

class FactCheckBody(BaseModel):
    """Final summary output"""
    body: str = Field(description="The full fact check body in Markdown format")
    claims: List[Claim] = Field(description="A list of claims that were analyzed")
    verdict: VERDICT_LITERALS_LLM = Field(description="The verdict for the entire post")  # Use LLM version without "error"


SYS_CONTEXT_PROMPT = """
You are a member of a collaborative, fact-checking team. You will be provided
with content that may lack necessary context. Your job is to gather the
necessary context to understand the post and then determine why it was submitted
for fact checking. Your job is NOT to actually perform the fact check. 

In terms of context, you may need to search for background information. For
example, the post could come from social media and be referencing a recent event
not in your training data. Or it could be a post referencing an obscure
sub-culture, the details of which are needed to understand the post.

Once you have the necessary context, you are to extract the relevant claims from
the original post (NOT the background information) that are worthy of fact
checking. This is NOT all claims in the provided content. You are to extract the
claims that are the likely reason the content was submitted. Most often, this
will be a single claim, but there could be many. 

Claims are fact-checkable statements. They are not opinions, predictions, or
easily recognizable hyperbole.

Sometimes, people submit content that they simply don't like, so it could be the
case that there is nothing to fact check. 

Your output should follow this format:

```
# Background

# What's likely being fact checked

# Claims that are NOT fact checkable

* A bulleted list of claims that are not fact checkable

# Fact checkable claims

* A bulleted list of fact checkable claims. Provide a succinct claim - do NOT
  provide anything else (including suggestions on how to fact check it or links
  to supporting evidence)

```

- Use ONLY the specified Markdown section headers
- When listing claims, do NOT include any other text, explanation, links, or
  commentary.
- Place links to supporting evidence inline, immediately following the
information they support, like this: [example](http://example.com/evidence).")

After completing your task, review for adherence to the output format.
Self-correct any issues found before finalizing the output.
"""

# Prompts for advocate agent
SYS_ADVOCATE_PROMPT = """
You are a fact checker within a collaborative, fact checking team. Your job on
this team is to analyze fact-checkable claims and attempt to prove them
ACCURATE. Another member of the team will attempt to prove them inaccurate.

Write out your findings using Markdown.
"""

# Prompts for adversary agent
SYS_ADVERSARY_PROMPT = """
You are a fact checker within a collaborative, fact checking team. Your job on
this team is to analyze fact-checkable claims and attempt to prove them
INACCURATE. Another member of the team will attempt to prove them accurate.

Write out your findings using Markdown.
"""

# Prompts for summarizer
SYS_SUMMARY_PROMPT = """
You are part of a collaborative, fact-checking team. Your main responsibility is
to create a concise fact-check summary that integrates input from three
independent agents:

- Context Gatherer: Provides additional background and identifies fact-checkable
  claims.
- Advocate: Finds evidence supporting the original claims.
- Adversary: Finds evidence that challenges or disproves the claims.

Begin with a concise internal checklist (3-7 bullets) of the conceptual steps
you will take; do not include this checklist in the final output.

Structure your final output as valid JSON with the following fields:
- `body`: The primary fact-check body written in Markdown, with exactly two
sections:
    - `# Summary`: A single-paragraph overview expressing the overall conclusions
    about the claims.
    - `# Details`: A summary of both supporting and opposing evidence from sources.
    Clearly state if supporting or opposing evidence is absent. Address any
    ambiguities or conflicts with a brief explanation. Use short paragraphs, no
    additional subheadings.
- `claims`: An array of objects, each containing:
    - `claim`: The fact-checkable claim identified by the context gatherer.
    - `accuracy`: The claim's accuracy
    - `reason`: A two-sentence summary of the evidence that resuled in the
      assigned accuracy score.
- `verdict`: A single verdict label from the following options:
    - false: Entirely inaccurate content with no factual basis. This includes
      fabricated claims, fake quotes, or real media used to assert something
      unrelated to its true context.
    - altered: Media that has been digitally manipulated or synthesized in
      misleading ways. Examples include photoshopping, splicing, or AI-generated
      content presented as real.
    - partly_false: Content that mixes accurate and inaccurate information.
      Often involves misstated figures, dates, or claims that are only partially
      correct.
    - missing_context: Content that is technically accurate but misleading by
      omission. Cropped media, selective statistics, or repeating false claims
      without clarification.
    - satire: Content meant as humor, parody, or critique through exaggeration
      or irony. It may resemble real information but is not intended to be
      factual.
    - true: All fact-checkable claims are supported by verifiable evidence.
    - unable_to_verify: The fact-checkable claims could not be verified with
      available information.
    - not_fact_checkable: None of the claims are fact-checkable. This means the
      post consists of opinions, speculations, or obvious hyperbole.

Output Requirements:
- Output a single valid JSON object containing 'body', 'claims', and 'verdict'
only. The claims array may be empty if there are no fact-checkable claims.
- In the 'body' section, use only the Markdown headings ('# Summary' and '#
Details'). Write succinctly at a 6th-grade reading level, avoiding technical
jargon and unfamiliar acronyms and references.
- Place links to evidence inline with incrementing numbers (e.g., "Reuters found
this was based on a digitally edited image.
[[1]](http://reuters.com/some-page/)"). All citations must have active URLs. If
any URLs are missing, self-correct if possible, otherwise do not use that URL.
- Adopt neutral, conversational language that is persuasive but avoids terms
like "trick" or "debunked".
- If the advocate and adversary outputs are absent, it has been determined that
the background found by the Context Gatherer is enough to write the fact check.
- After writing, validate your output for readability, accurate use of sections,
proper link placement, presence of active URLs, correct ordering of claims, and
inclusion of every required field. Self-correct any errors or omissions before
submitting.

Sample Output Format:
{
    "body": "# Summary
    A brief summary paragraph...
    
    # Details
    Supporting and opposing evidence, with inline numbered links...",
    "claims": [
    {
        "claim": "A specific, fact-checkable claim.",
        "accuracy": accurate|inaccurate|mixed|unable_to_verify|error,
        "reason": "A two-sentence justification for this score."
    }
        // ...repeat for each claim
    ],
    "verdict": false|altered|partly_false|missing_context|satire|true|unable_to_verify|not_fact_checkable
}
"""

SYS_NEXT_STEP_PROMPT = """
You are a member of a collaborative, fact-checking team. There is a 'Context
Gathering' agent that has already gathered background information. Your job is
to decide the next step. The options available are:

1. Continue the fact checking process
2. Move straight to the Summarizer

Situations where you should proceed straight to the Summarizer:
- The background check has shown the information is from a satirical account.
- The background check has discovered that the images or videos are fake or
  manipulated.
- The background has found conclusive and reliable evidence that the content is
  true.
- The background check has not found any fact-checkable claims. This means the
  post consists of opinions, speculations, or obvious hyperbole.

In all other cases, you should continue the fact checking process.

Output should be JSON with the following format:
{
    "next_step": "summarize" | "continue"
}
"""

SUMMARY_PROMPT = """# Advocate's findings: 
{advocate_findings}

# Adversary's findings: 
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
    """Check if the post is eligible for fact checking"""

    return {
        "is_eligible": True,
        "eligibility_reason": "This is a general fact checker, so we assume it is eligible"
    }


async def gather_context(state: FactCheckState) -> Dict:
    """
    Gather additional context needed for fact checking.
    
    This could include:
    - Scraping linked content
    - Looking up background information online
    """
    if DEBUG_MODE:
        return {
            "messages": state["messages"] + [HumanMessage(content="DEBUG MODE")]
        }
    
    logger.info("Starting gather_context node")

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
        SystemMessage(content=SYS_CONTEXT_PROMPT),
        HumanMessage(content=content)
    ]

    search_config = RunnableConfig(run_name="ContextGatherer")
    response = await agent.ainvoke(messages, config=search_config)
    
    # TODO: Add a check for no claims, if so, use this response as summary and
    # quit
    return {
        "messages": messages + [HumanMessage(content=response.content)]
    }


async def should_continue(state: FactCheckState) -> Literal["advocate_agent", "adversary_agent", "summarize"]:
    """Decide whether to continue with fact checking based on the context"""

    class NextStep(BaseModel):
        """Next step to take"""
        next_step: Literal["summarize", "continue"]
        reason: str = Field(description="A short explanation for next_step")

    if DEBUG_MODE:
        #return ["advocate_agent", "adversary_agent"]
        return "summarize"
    
    logger.info("Starting should_continue router")
    
    llm = get_llm(model_type="main", use_reasoning=True)

    next_step_llm = llm.with_structured_output(NextStep)

    messages = [SystemMessage(content=SYS_NEXT_STEP_PROMPT)]
    messages += state["messages"][1:]

    next_step: NextStep = await next_step_llm.ainvoke(messages)

    if next_step.next_step == "summarize":
        return "summarize"
    else:
        return ["advocate_agent", "adversary_agent"]

async def advocate_agent(state: FactCheckState) -> Dict:
    """Agent that searches for evidence supporting the claims"""
    logger.info("Starting advocate_agent node")
    
    if DEBUG_MODE:
        return {
            "advocate": [HumanMessage(content="ADVOCATE DEBUG MODE")]
        }
    
    llm = get_llm(model_type="main", use_reasoning=True)
    
    tool = {"type": "web_search_preview"}
    agent = llm.bind_tools([tool])
    
    messages = [SystemMessage(content=SYS_ADVOCATE_PROMPT)]
    messages += state["messages"][1:]

    search_config = RunnableConfig(run_name="GeneralAdvocate")
    out = await agent.ainvoke(messages, config=search_config)
    return {
        "advocate": out
    }


async def adversary_agent(state: FactCheckState) -> Dict:
    """Agent that searches for evidence refuting the claims"""
    logger.info("Starting adversary_agent node")

    if DEBUG_MODE:
        return {
            "adversary": [HumanMessage(content="ADVERSARY DEBUG MODE")]
        }
    
    llm = get_llm(model_type="main", use_reasoning=True)
    
    tool = {"type": "web_search_preview"}
    agent = llm.bind_tools([tool])
    
    messages = [SystemMessage(content=SYS_ADVERSARY_PROMPT)]
    messages += state["messages"][1:]

    search_config = RunnableConfig(run_name="GeneralAdversary")
    out = await agent.ainvoke(messages, config=search_config)
    return {
        "adversary": out
    }


async def summarize(state: FactCheckState) -> Dict:
    """Summarize the debate and create final fact check"""
    logger.info("Starting summarize node")

    if DEBUG_MODE:
        return {
            "body": "SUMMARY DEBUG MODE",
            "verdict": DEFAULT_VERDICT
        }
    
    llm = get_llm(model_type="main", use_reasoning=True)
    
    body_llm = llm.with_structured_output(FactCheckBody)
    
    messages = [SystemMessage(content=SYS_SUMMARY_PROMPT)]
    messages += state["messages"][1:]

    if len(state.get("advocate",[])) > 0 or len(state.get("adversary",[])) > 0:
        # Get text from advocate and adversary messages
        advocate_findings = ""
        if len(state.get("advocate",[])) > 0:
            advocate_findings = get_text_from_message(state["advocate"][-1]) or "(Not Present)"
        
        adversary_findings = ""
        if len(state.get("adversary",[])) > 0:
            adversary_findings = get_text_from_message(state["adversary"][-1]) or "(Not Present)"
        
        agent_reports = SUMMARY_PROMPT.format(
            advocate_findings=advocate_findings,
            adversary_findings=adversary_findings
        )
        messages += [HumanMessage(content=agent_reports)]
    
    body: FactCheckBody = await body_llm.ainvoke(messages)
    return body.model_dump()


# Conditional edge function
def continue_if_eligible(state: FactCheckState) -> Literal["gather_context", END]:
    """Decide whether to continue with fact checking based on eligibility."""
    if state.get("is_eligible", True):
        return "gather_context"
    else:
        return END


def build_general_fact_checker() -> StateGraph:
    """
    Build the fact checking agent graph.
    
    Returns:
        Compiled StateGraph
    """
    
    # Initialize the graph
    builder = StateGraph(FactCheckState)
    
    # Add nodes
    builder.add_node("check_eligibility", check_eligibility)
    builder.add_node("gather_context", gather_context)
    builder.add_node("should_continue", should_continue)
    builder.add_node("advocate_agent", advocate_agent)
    builder.add_node("adversary_agent", adversary_agent)
    builder.add_node("summarize", summarize)
    
    # Add edges
    builder.add_edge(START, "check_eligibility")
    builder.add_conditional_edges("check_eligibility", continue_if_eligible)
    builder.add_conditional_edges("gather_context", should_continue)
    builder.add_edge(["advocate_agent", "adversary_agent"], "summarize")
    builder.add_edge("summarize", END)
    
    # Compile the graph
    graph = builder.compile()
    
    return graph


@register_fact_checker
class GeneralFactCheckerV1(BaseFactChecker):
    """General fact checker using LangGraph adversarial debate"""
    
    slug = "general_checker_v1"
    name = "General Fact Checker"
    description = "A general purpose fact checker that can analyze any post"
    version = "1.0.5"
    
    def __init__(self):
        super().__init__()
    
    async def should_run(self, post_data: Dict[str, Any], classifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determine if this fact checker should run based on classifications.
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

        return {
            "should_run": False,
            "reason": "Turning off automatic running to save on costs"
        }
        
        if has_video:
            return {
                "should_run": False,
                "reason": "Cannot analyze posts with video content"
            }

        # Check for clarity rating - we only run on clear posts (clarity 4 or 5)
        clarity_rating = None
        for classification in classifications:
            if classification.get("classifier_slug") == "clarity-v1":
                data = classification.get("classification_data", {})
                if data.get("type") == "single":
                    clarity_rating = data.get("value")
                    break

        if clarity_rating is None:
            return {
                "should_run": False,
                "reason": "No clarity classification found - clarity rating required"
            }

        if clarity_rating not in ["clarity_3", "clarity_4", "clarity_5"]:
            return {
                "should_run": False,
                "reason": f"Post clarity too low ({clarity_rating}) - requires clarity_4 or clarity_5"
            }

        return {
            "should_run": True,
            "reason": f"Post is eligible for general fact checking (no video, clarity: {clarity_rating})"
        }
    
    def build_graph(self):
        """Build and return the LangGraph for fact checking"""
        return build_general_fact_checker()
    
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
            advocate=[],
            adversary=[],
            messages=[],
            claims=[],
            body=None,
            verdict=None,
        )
    
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
                    "verdict": final_result.get("verdict") if final_result else None,
                    "body": final_result.get("body") if final_result else None,
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
                    "claims": final_result.get("claims", []) if final_result else [],
                }
            
        except Exception as e:
            logger.error(f"Error in general fact check streaming: {str(e)}", 
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
            graph_config = RunnableConfig(run_name="GeneralFactCheck")
            result:FactCheckState = await graph.ainvoke(initial_state, config=graph_config)
            
            # Create raw_output with serialized result
            raw_output = {
                "fact_check_id": fact_check_id,
                "updates": [],  # Empty for non-streaming execution
                "final_result": dumpd(result)
            }
            
            # Convert to FactCheckResult
            return FactCheckResult(
                text=result.get("body", "No fact check could be generated"),
                verdict=result.get("verdict") or DEFAULT_VERDICT,
                # confidence=result.get("confidence", 0.0), # Phasing out confidence
                claims=result.get("claims", []),
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
            logger.error(f"Error in General fact checking: {str(e)}", 
                        post_uid=post_data.get("post_uid"),
                        fact_check_id=fact_check_id)
            raise
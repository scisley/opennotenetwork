"""
X Platform Note Writer V1 with LangGraph Reflection Loop

Uses LangGraph for note generation with URL validation and reflection feedback.
"""

from typing import Any, Dict, List, Literal, Optional, Annotated
import operator
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain_core.runnables import RunnableConfig

from app.config import settings
from app.classifiers.shared.tweet_utils import prepare_fact_check_input, format_content_with_media
from app.services.utils.url_agent import build_url_agent_graph
from app.services.evaluation import evaluate_note
from app.fact_checkers.shared.enums import NOTE_WRITING_VERDICTS, POSITIVE_VERDICTS
from .base import BaseNoteWriter, NoteResult
from .registry import register_note_writer

# Type definitions
MISLEADING_TAGS = Literal[
    "disputed_claim_as_fact",
    "factual_error",
    "manipulated_media",
    "misinterpreted_satire",
    "missing_important_context",
    "other",
    "outdated_information"
]

# Configuration
MODEL_NAME = "gpt-5"
REASONING_EFFORT = "low"  # Options: "minimal", "low", "medium", "high"
REASONING_SUMMARY = "auto"  # Options: "auto", "none", number of words
TIMEOUTS = {
    "minimal": 5 * 60,
    "low": 5 * 60,
    "medium": 10 * 60,
    "high": 15 * 60,
}
MAX_LINKS = 3
MAX_ITERATIONS = 3

# Schema for X.com Community Note
class XCommunityNote(BaseModel):
    text: str = Field(description="The text of the note to write. Maximum of 250 characters.", max_length=250)
    links: list[str] = Field(description="A list of URLs to include in the note. Only use actual links from the text provided. Never generate links.", min_items=0, max_items=MAX_LINKS)
    classification: Literal["misinformed_or_potentially_misleading", "not_misleading"] = Field(description="The classification of the note.")
    misleading_tags: list[MISLEADING_TAGS] = Field(description="The tags that best describe the note. Empty array if classification is not_misleading.")
    trustworthy_sources: bool = Field(description="Whether the note includes at least one trustworthy URL.")
    reason: str = Field(description="A short reason for the outputs.")

# LangGraph State Definition
class NoteWriterState(MessagesState):
    # MessagesState comes with a "messages" field

    # Input data
    post_data: Dict[str, Any]
    fact_check_data: Dict[str, Any]

    # Generated note
    note: Optional[XCommunityNote]

    # URL validation results (only URLs in current note)
    invalid_urls: List[str]
    # Running list of ALL URL's that were validated across all iterations
    url_validation_results: Annotated[Optional[List[Dict]], operator.add]

    # Control flow
    iteration: int
    max_iterations: int

    # Error handling
    error: Optional[str]

def get_llm() -> ChatOpenAI:
    """Get configured LLM instance"""
    return ChatOpenAI(
        model=MODEL_NAME,
        api_key=settings.openai_api_key,
        output_version="responses/v1",
        reasoning={"effort": REASONING_EFFORT, "summary": REASONING_SUMMARY},
        timeout=TIMEOUTS[REASONING_EFFORT],
        max_retries=1,
    )

def map_verdict_to_x_classification(verdict: str) -> str:
    """
    Map fact-check verdict to X.com's binary classification.

    Args:
        verdict: The fact-check verdict from Meta's taxonomy

    Returns:
        X.com classification: either "misinformed_or_potentially_misleading" or "not_misleading"
    """
    if verdict in NOTE_WRITING_VERDICTS:
        return "misinformed_or_potentially_misleading"
    elif verdict in POSITIVE_VERDICTS:
        return "not_misleading"
    else:
        return "(unclear)"

def build_note_text(note: XCommunityNote) -> str:
    """Build the note text"""
    return note.text + "\n\n" + "\n".join(note.links)

def prepare_messages(state: NoteWriterState) -> NoteWriterState:
    """Prepare the initial messages for the LLM"""
    post_data = state["post_data"]
    fact_check_data = state["fact_check_data"]

    messages = [
        {"role": "system", "content": DRAFT_NOTE_SYSTEM_PROMPT}
    ]

    # Use prepare_fact_check_input to get properly formatted text with media placeholders
    prepared_input = prepare_fact_check_input(post_data)

    # Format the human prompt using the prepared input
    human_prompt = DRAFT_NOTE_HUMAN_PROMPT.format(
        author=prepared_input.get("author"),
        context=prepared_input.get("context"),
        content=prepared_input.get("text"),
    )
    # Map fact check verdict to X.com classification
    verdict = fact_check_data.get("verdict", "error")
    x_classification = map_verdict_to_x_classification(verdict)

    fact_check_prompt = FACT_CHECK_PROMPT.format(
        fact_check_summary=fact_check_data.get("body", ""),
        verdict=f"{verdict} (X.com classification: {x_classification})",
        confidence=fact_check_data.get("confidence", 0.0)
    )

    # Combine prompts
    full_prompt = human_prompt + "\n\n" + fact_check_prompt

    # Use format_content_with_media to convert media placeholders to LLM format
    content = format_content_with_media({
        "text": full_prompt,
        "media": prepared_input.get("media", [])
    })

    messages.append({
        "role": "user",
        "content": content
    })

    return {"messages": messages}

async def generate_note(state: NoteWriterState) -> NoteWriterState:
    """Generate a Community Note using the LLM"""
    llm = get_llm()
    structured_llm = llm.with_structured_output(XCommunityNote)

    # Generate the note
    result: XCommunityNote = await structured_llm.ainvoke(state["messages"])

    return {
        "messages": [{"role": "assistant", "content":build_note_text(result)}],
        "note": result,
        "iteration": state["iteration"] + 1,
        "invalid_urls": [], # Reset invalid URLs (validation is done next)
    }

async def validate(state: NoteWriterState) -> NoteWriterState:
    """Validate URLs in the generated note using the URL agent subgraph"""
    note = state["note"]

    if not note or not note.links:
        # No URLs to validate
        return {
            "url_validation_results": [],
            "invalid_urls": []
        }

    # Build and run the URL agent subgraph
    url_agent = build_url_agent_graph()

    # Run the subgraph with the URLs from the note
    url_config = RunnableConfig(run_name="URLValidator")
    agent_result = await url_agent.ainvoke({"urls": note.links}, config=url_config)

    # Extract validation results from the agent's analysis
    validation_results = agent_result.get("analysis", [])

    # Identify invalid URLs
    invalid_urls = [
        result["url"]
        for result in validation_results
        if not result.get("valid", False)
    ]

    return {
        "url_validation_results": validation_results,
        "invalid_urls": invalid_urls
    }

def reflection_router(state: NoteWriterState) -> Literal["reflect", "finalize"]:
    """Decide whether to retry generation or finalize the note"""
    # Retry if there are invalid URLs and we haven't exceeded max iterations
    if state["invalid_urls"] and state["iteration"] < state["max_iterations"]:
        return "reflect"

    return "finalize"

def reflect(state: NoteWriterState):
    """Reflect on the note"""
    reflection_notes = []
    if state["invalid_urls"]:
        # Add feedback about invalid URLs
        invalid_urls = [result["url"] for result in state["url_validation_results"] if not result.get("valid", False)]
        invalid_urls_text = "\n".join(invalid_urls)
        msg = f"\n\n## Important: Invalid URLs\nThe following URLs were found to be invalid and should NOT be included:\n{invalid_urls_text}\nPlease generate a new note without relying on these URLs."
        reflection_notes.append({"role": "user", "content": msg})
    
    return {"messages": reflection_notes}

def finalize_note(state: NoteWriterState) -> NoteWriterState:
    """Finalize the note or return error if URLs are still invalid"""
    # If there are still invalid URLs after all retries, fail
    if state["invalid_urls"]:
        invalid_urls_str = ", ".join(state["invalid_urls"])
        return {"error": f"Failed to generate note with valid URLs. Invalid URLs: {invalid_urls_str}"}

    return {"note": state["note"]}

def build_note_writer_graph():
    """Build the LangGraph workflow for note writing with reflection"""
    # Create the state graph
    builder = StateGraph(NoteWriterState)

    # Add nodes
    builder.add_node("prepare_messages", prepare_messages)
    builder.add_node("generate_note", generate_note)
    builder.add_node("validate", validate)
    builder.add_node("finalize", finalize_note)
    builder.add_node("reflect", reflect)

    # Add edges
    builder.add_edge(START, "prepare_messages")
    builder.add_edge("prepare_messages", "generate_note")
    builder.add_edge("generate_note", "validate")
    
    # Add conditional edge for reflection loop
    builder.add_conditional_edges(
        "validate",
        reflection_router
    )

    builder.add_edge("reflect", "generate_note")
    builder.add_edge("finalize", END)

    # Compile the graph
    return builder.compile()

@register_note_writer
class XNoteWriterV1(BaseNoteWriter):
    """LangGraph-powered note writer for X.com Community Notes with URL validation"""

    slug = "x_note_writer_v1"
    name = "X Community Note Writer V1"
    description = "Writes Community Notes for X.com posts using LangGraph with reflection feedback loop"
    version = "2.0.0"
    platforms = ["x"]

    def __init__(self):
        """Initialize the note writer with the LangGraph workflow"""
        super().__init__()
        self.graph = build_note_writer_graph()

    async def write_note(self, post_data: dict[str, Any], fact_check_data: dict[str, Any]) -> NoteResult:
        """Write a Community Note for an X.com post using LangGraph workflow"""
        # Extract post ID from post_uid
        post_id = post_data["post_uid"].split("--")[1]

        # Initialize state
        initial_state: NoteWriterState = {
            "post_data": post_data,
            "fact_check_data": fact_check_data,
            "messages": [],
            "note": None,
            "url_validation_results": [],
            "iteration": 0,
            "max_iterations": MAX_ITERATIONS,
            "error": None
        }

        graph_config = RunnableConfig(
            run_name="XNoteWriterV1", 
            metadata={
                "post_uid": post_data["post_uid"],
                "fact_check_id": fact_check_data["fact_check_id"]
            }
        )
        # Run the graph
        result_state = await self.graph.ainvoke(initial_state, config=graph_config)

        # Check for errors
        if result_state["error"]:
            raise Exception(f"Note generation failed: {result_state['error']}")

        note: XCommunityNote | None = result_state["note"]
        if not note:
            raise Exception("No note generated")

        # Build the full note text for evaluation
        full_note_text = build_note_text(note) + f"\nMore Details: https://www.opennotenetwork.com/posts/{post_data['post_uid']}"

        # Evaluate the note (non-blocking, errors handled gracefully)
        evaluation_json = await evaluate_note(
            note_text=full_note_text,
            post_id=post_id
        )

        # Prepare submission JSON
        submission_json = {
            "info": {
                "classification": note.classification,
                "misleading_tags": note.misleading_tags,
                "text": full_note_text,
                "trustworthy_sources": note.trustworthy_sources,
            },
            "post_id": post_id,
        }

        # Prepare metadata
        metadata = {
            "llm_config": {
                "model": MODEL_NAME,
                "reasoning": {
                    "effort": REASONING_EFFORT,
                    "summary": REASONING_SUMMARY
                }
            },
            "workflow": {
                "iterations": result_state["iteration"],
                "invalid_urls_found": len(set(result_state["invalid_urls"])),
                "url_validation_results": result_state["url_validation_results"]
            },
            "evaluation": evaluation_json
        }

        # Return the result
        return NoteResult(
            text=note.text,
            links=[{"url": link} for link in note.links],
            submission_json=submission_json,
            raw_output=note.model_dump(),
            metadata=metadata,
            version=self.version
        )

    def get_configuration(self) -> dict[str, Any]:
        """Return configuration"""
        return {
            "max_note_length": 250,
            "max_links": MAX_LINKS,
            "max_iterations": MAX_ITERATIONS,
            "workflow_type": "langgraph_reflection",
            "url_validation": True
        }

# Prompts remain the same
DRAFT_NOTE_SYSTEM_PROMPT = """
You are part of a collaborative fact checking team. Your job is to write a
concise summary of the final fact check that will be submitted as a Community
Note on X.com via their new AI Community Notes API.

Write a neutral, fact-based summary no longer than 250 characters. Community
Notes must be informative and avoid derogatory, abusive, or dismissive language,
regardless of the original post's tone. Write for a sixth grade reading level
with absolutely no technical jargon. Write fact checks in a neutral, respectful
tone, avoiding dismissive or belittling phrases.

Structure your response as a JSON object with the following fields:

- text: A concise summary of the fact check. You need not cover every claim
  covered in the fact check. The system (not you) will automatically add a link
  that brings the reader to the full fact check. Covering the single, most
  important claim well is better than doing a mediocre job covering multiple
  claims.
- links: A list of URLs to include in the note. You can include up to three, but
  fewer is better. One link that supports all the points made in the note is
  better than two. If you provide zero URLs, it must be because the fact check
  does not provide any URLs. Arrange them with the most likely to be useful to
  the community at the top. ONLY provide URLs that are directly relevant to the
  note.
- classification: The classification of the note. Do not contradict the fact
checker's verdict.
    - misinformed_or_potentially_misleading: The fact check has concluded the
      post has errors or omissions that warrant a note.
    - not_misleading: The fact check has concluded the post is accurate.
- misleading_tags: The tags that best describe the note.
    - disputed_claim_as_fact: The post makes a claim that is disputed among
      reputable experts but portrays it as a fact.
    - factual_error: The post contains a factual error. This is the most likely
      tag.
    - manipulated_media: The post contains manipulated media.
    - misinterpreted_satire: The post contains a misinterpretation of satire.
    - missing_important_context: The claims in the post are accurate, but missing
      important context. Do NOT choose this if there are important errors in the
      post. Use factual_error instead.
    - outdated_information: The post contains outdated information.
    - other: The post contains other misleading information.
- trustworthy_sources: Whether the note includes at least one trustworthy URL.
- reason: Explain the classification and misleading_tags choices. If you provide
False for trustworthy_sources or zero URLs, explain your reason here.

Please write the note in the following fashion:
- Do not attempt to summarise the original post or say "This post is false"
- Only refer to "errors" in the original post if it is required to make clear
how the context is relevant.
- *DO NOT* discuss there being a lack of evidence/reports for something unless
the source you're going to include says exactly that. The world is fast moving
and new evidence may have appeared. ONLY say what you know from the source that
is linked
- *DO NOT* refer to sources that you have not provided a link to.
- Make sure the note addresses key claims in the original post, without being
perceived as expressing opinion or speculation.

# Note Examples

## Example

Bad note:
The claim that President Trump "has reportedly not been seen in several days"
and rumors of his death are false. Trump has had recent public activity and
political actions as recently as August 29, 2025, according to verified news
reports.
[links]

Good note:
Trump was seen golfing on August 29, 2025, according to Reuters.
[link to Reuters article]

Explanation:
Do not summarise or editorialise on the original post. His death might be real
for all we know. But what we do know is that there was evidence of his public
appearances and activities on August 29, 2025. So that is what we will say, and
then provide a link.

## Example

Bad note:
The screenshot of a “Donald J. Trump” post is fabricated, per AAP FactCheck.
Reuters reports Australia’s beef decision wasn’t prompted by Trump, and the
planned rule targets under‑16s, not all users.
[Links]

Good note:
AAP FactCheck reports the screenshot of a “Donald J. Trump” post is fabricated.
[One Link]

Explanation:
Since the post is fake, there's no need to fact check the fake claims.

## Example

Bad note:
Post falsely claims UP is #1 in factories (15.91%) and GVA (25.03%). ASI 2023-24
shows UP ranks 4th in factories with 8.51%, behind Tamil Nadu, Gujarat,
Maharashtra. UP's GVA share is 7%, not 25.03%.
[Links]

Good note:
ASI 2023-24 shows Uttar Pradesh ranks 4th in factories with 8.51%, behind Tamil
Nadu, Gujarat, Maharashtra. UP's GVA share is 7%, not 25.03% as claimed.
[Links]

Explanation:
Bad note attempts to summarise original post. Readers don't need this, they can
see it. Also it says the post is false. Instead we prefer to provide additional
context.

## Example

Bad note:
This photograph is not from Rudy Giuliani's car accident. News reports describe
Giuliani being "struck from behind at high speed," while this image shows a
head-on collision that doesn't match the incident description.

Good note
News reports describe Giuliani being "struck from behind at high speed," while
this image shows a head-on collision that doesn't match the incident
description.

Explanation:
We don't say what the photo is or is not. Instead we give context for why the
photo is likely wrong.

## Example

Bad note:
No evidence supports these claims. Nvidia filings list major holders, with no
20% stake by Steve Buscemi. OpenAI says it's controlled by its nonprofit, not a
30% individual owner. Also, Buscemi (1957) is older than Altman (1985).

Good note:
Nvidia filings list major holders, with no 20% stake by Steve Buscemi. OpenAI
says it's controlled by its nonprofit and does not mention a 30% individual
owner. Also, Buscemi (1957) is older than Altman (1985).

Explanation:
We don't start with an overall summary. Instead we give specific details that
support the claim.

## Example

Bad note:
Many female albums were Platinum long before, e.g., Alanis Morissette’s Jagged
Little Pill and Shania Twain's Come On Over.

Good note:
Earlier platinum albums from female artists include Alanis Morissette’s Jagged
Little Pill (1995) and Shania Twain's Come On Over (1997).

Explanation:
We avoid sounding like an opinion with phrases like "long before". Instead, we
directly state the facts.

## Example

Bad Note:
Reports put the Kirk memorial at tens of thousands to ~100,000. JFK's funeral
drew 250,000 at the Capitol and about 800,000–1,000,000 along the route. MLK's
funeral procession drew very large crowds in Atlanta.

Good note:
Reports put the Kirk memorial at tens of thousands to ~100,000. JFK's funeral
drew 250,000 at the Capitol and about 800,000–1,000,000 along the route. MLK's
funeral procession drew 150,000 in Atlanta.

Explanation:
We don't say things like "very large crowds" - we provide quantitative evidence
that can be compared to the other events.
"""

DRAFT_NOTE_HUMAN_PROMPT = """Author: {author}
Context: {context}
Content:
{content}"""

FACT_CHECK_PROMPT = """## Fact Check Summary
Summary: {fact_check_summary}

## Fact Check Verdict:
{verdict}"""
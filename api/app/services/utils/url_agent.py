import operator
import re
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from typing_extensions import TypedDict, Annotated
from typing import Any
from pydantic import BaseModel, Field
from app.config import settings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .url_utils import scrape_url

class ValidUrl(BaseModel):
    valid: bool = Field(description="Whether the URL is valid")

valid_url_llm = ChatOpenAI(
    model="gpt-5-mini",
    api_key=settings.openai_api_key,
    output_version="responses/v1",
    reasoning={"effort": "medium", "summary": "auto"},
    timeout=5 * 60,
    max_retries=1,
)

VALID_SYS_PROMPT = """
You will be provided with an LLM generated summary of a website. Determine if
the summary represents a valid URL. Invalid URLs are ones where the summary says
something like "This page could not be found" or "The page you are looking for
does not exist" or similar.
"""

VALID_USER_PROMPT = """
Summary:
{summary}
"""

prompt = ChatPromptTemplate([
    {"role": "system", "content": VALID_SYS_PROMPT},
    {"role": "human", "content": VALID_USER_PROMPT}
])
chain = prompt | valid_url_llm.with_structured_output(ValidUrl)

def clean_url_utm_params(url: str) -> str:
    """
    Remove UTM parameters from a URL.

    Args:
        url: URL string that might contain UTM parameters

    Returns:
        URL with UTM parameters removed
    """
    # Remove ?utm_source=openai and any following parameters
    cleaned = re.sub(r'\?utm_source=openai(?:&[^&\s]*)*', '', url)
    # Also handle case where utm_source is not the first parameter
    cleaned = re.sub(r'&utm_source=openai(?:&[^&\s]*)*', '', cleaned)
    return cleaned

class AnalyzeUrlsState(TypedDict):
    urls: list[str]
    analysis: Annotated[list[dict[str, Any]], operator.add]
    metadata: dict[str, Any]

async def analyze_url(state):
    url = state["url"]
    analysis = {
        "url": url,
    }
    try:
        scrape_result = await scrape_url(url, formats=['summary'], timeout=20*1000)
        url_status = await chain.ainvoke({"summary": scrape_result.summary})
        analysis["valid"] = url_status.valid
        analysis["summary"] = scrape_result.summary
        return {"analysis": [analysis]}
    except Exception as e:
        analysis["valid"] = False
        analysis["summary"] = f"URL RETRIEVAL ERROR: {e}"
        return {"analysis": [analysis]}

async def continue_to_analysis(state: AnalyzeUrlsState):
    # The Send operator allows you to send whatever state you want. I send
    # the url to be analyzed - after cleaning UTM params
    return [
        Send("analyze_url", {"url": clean_url_utm_params(url)})
        for url in state["urls"]
    ]

async def finalize(state: AnalyzeUrlsState):
    return {"metadata": {"status": "completed"}}

def build_url_agent_graph():
    builder = StateGraph(AnalyzeUrlsState)
    builder.add_node("analyze_url", analyze_url)
    builder.add_node("finalize", finalize)

    builder.add_conditional_edges(START, continue_to_analysis, ["analyze_url"])
    builder.add_edge("analyze_url", "finalize")
    builder.add_edge("finalize", END)
    graph = builder.compile()
    return graph

# Usage example
# from langchain_core.runnables import RunnableConfig
# urls = ["https://www.reuters.com/sustainability/boards-policy-regulation/tesla-drivers-can-pursue-class-action-over-self-driving-claims-judge-rules-2025-08-19/", "https://www.reuters.com/business/autos-transportation/tesla-settles-2019-california-crash-lawsuit-ahead-jury-trial-2025-09-16/", "https://www.tesla.com/support/full-self-driving-capability", "https://www.reuters.com/legal/tesla-drivers-can-pursue-class-action-over-self-driving-claims-judge-rules-2025-08-19/", "https://www.tesla.com/support/autopilot"]
# input = {"urls": urls}
# config = RunnableConfig(run_name="URLAgent")
# out = await graph.ainvoke(input, config=config)
# out
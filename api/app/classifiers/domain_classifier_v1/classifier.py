"""
Domain Classifier V1

A fact-checking domain classifier that uses OpenAI's structured output to categorize
social media posts into relevant fact-checkable domains.
"""

from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from app.classifiers.base import BaseClassifier
from app.classifiers.registry import register_classifier
from app.classifiers.shared.tweet_utils import prepare_fact_check_input, format_content_with_media, AUTHOR_CONTEXT_CONTENT_PROMPT
from app.config import settings

# Pydantic model for structured output
class DomainClassification(BaseModel):
    """Structured output for domain classification"""
    
    class DomainResult(BaseModel):
        """Individual domain classification result"""
        reason: str = Field(description="Explanation of why this domain applies")
        # From a list of literals
        domain: Literal[
            "science_engineering",
            "health_medicine",
            "nature_climate",
            "economy_business",
            "law_regulation",
            "politics_government",
            "crime_safety",
            "history",
            "education_society",
            "media_attribution",
            "culture_entertainment",
            "sports",
            "recent_news",
            "other",
            "no_claim",
        ]
        confidence: float = Field(description="Confidence score for the domain (0-1)")
    
    domains: List[DomainResult] = Field(
        description="List of applicable domains with reasoning",
        min_items=1,
        max_items=10
    )

@register_classifier
class DomainClassifierV1(BaseClassifier):
    slug = "domain-classifier-v1"
    """
    Domain Classifier
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
        Classify a post into fact-checkable domains
        
        Args:
            post_data: Dict containing post information
            
        Returns:
            Classification result with type and values array
        """
        post_text = post_data.get("text", "")
        self.logger.info("Classifying post domains", text_length=len(post_text))
                
        # Get cached LLM instance
        llm = self._get_llm()
        
        # Create structured output version
        structured_llm = llm.with_structured_output(DomainClassification)
        
        # Prepare content with media
        prepared = prepare_fact_check_input(post_data)
        msg = AUTHOR_CONTEXT_CONTENT_PROMPT.format(**prepared)
        content = format_content_with_media({
            "text": msg,
            "media": prepared.get("media", [])
        })
        
        # Get structured output from LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
        result = await structured_llm.ainvoke(messages)
        
        # Format the results to match the classification schema
        domains = result.domains
        values = [
            {
                "value": d.domain,
                "reason": d.reason,
                "confidence": d.confidence
            }
            for d in domains
        ]
        classification = {
            "type": "multi",
            "values": values
        }
        
        self.logger.info(
            "Domain classification completed",
            num_domains=len(domains),
            domains=[d.domain for d in domains]
        )
        
        # Validate output
        if not await self.validate_output(classification):
            self.logger.error("Invalid classification output", classification=classification)
            raise ValueError("Invalid classification output")
        
        self.logger.info("Domain classification complete", num_values=len(values))
        return classification

########################################################
# Prompts
########################################################

system_prompt = """You are an expert fact-checker and classifier. Your task is to analyze content and determine:
1. Whether it contains fact-checkable claims
2. If it does, classify it into appropriate domains

## Domain Taxonomy:

1. **science_engineering**: Physics, chemistry, biology, technology, engineering, energy systems
2. **health_medicine**: Epidemiology, clinical research, vaccines, nutrition, toxicology (NOT claims about the health status of specific individuals)
3. **nature_climate**: Climate change, ecology, pollution, forestry, oceans, trade-offs around renewable energy
4. **economy_business**: Macroeconomics, labor, inflation, prices, corporate performance, financial markets
5. **law_regulation**: Statutes, regulations, legal rulings, rights, mandates, court proceedings
6. **politics_government**: Government actions, election results or processes, official positions of agencies, statements or actions from politicians
7. **crime_safety**: Crime rates, gun violence, policing, cybersecurity incidents, terrorism
8. **history**: Past events, historical trends, archival facts
9. **education_society**: Census data, population trends, surveys, education statistics, social science descriptives
10. **media_attribution**: Authenticity or context of photos, videos, quotes, charts
11. **culture_entertainment**: Movies, music, awards, cultural event
12. **sports**: Scores, player trades, records, team performance
13. **recent_news**: Reports about ongoing or just-happened events relying on real-time or recent reporting
14. **other**: Fact-checkable claims that do not clearly fit into the above domains
15. **no_claim**: No fact-checkable claim (opinion, satire, anecdote, or rhetorical content)

## Classification Process:

**Step 1: Check for Fact-Checkable Claims**
A fact-checkable claim is a statement that:
- Can be verified using publicly available information
- Makes assertions about objective reality
- Is not purely opinion, speculation, or personal experience
- Is of interest to the general public

Examples of fact-checkable claims:
- "The unemployment rate is 5%"
- "Climate change is caused by human activity"
- "This vaccine prevents disease X"

Examples of NON fact-checkable claims:
- "I think the weather is nice today"
- "This movie is the best"
- Questions without assertions
- Pure speculation about the future

**Step 2: Assign Relevant Domains**
If fact-checkable claims exist:
- Identify ALL relevant domains (content can belong to multiple domains)
- Provide clear reasoning for each domain assignment
- Be specific about which part of the content relates to each domain 

**Step 3: Format Output**
Return a JSON array with each domain classification including:
- "reason": Explanation of why this domain applies
- "domain": The domain name from the taxonomy above
- "confidence": Confidence score for the domain (0-1)

## Important Guidelines:

1. If NO fact-checkable claims exist, return only "No Claim"
2. Content can have multiple domains
3. Be conservative - only assign domains when clearly relevant
4. Consider the primary focus of the content when limiting to max 5 domains
5. Always provide specific reasoning tied to the actual content"""

human_prompt = """Analyze the following social media post and classify it into appropriate domains:

POST TEXT:
{post_text}"""
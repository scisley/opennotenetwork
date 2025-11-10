"""Full Fact Classifier v1 - Academic Fact-Checking Annotation Schema

See https://dl.acm.org/doi/10.1145/3412869
"""

from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
from app.classifiers.base import BaseClassifier
from app.classifiers.registry import register_classifier
from app.classifiers.shared.tweet_utils import prepare_fact_check_input, format_content_with_media, AUTHOR_CONTEXT_CONTENT_PROMPT
from app.config import settings
import structlog
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

logger = structlog.get_logger()


# Pydantic model for structured output
class FullFactClassification(BaseModel):
    """Structured output for Full Fact classification"""
    
    category: Literal[
        "not_a_claim",
        "personal_experience",
        "quantity",
        "correlation_causation",
        "laws_rules",
        "prediction",
        "other_claim"
    ] = Field(description="Primary category from Full Fact schema")
    
    subcategory: Optional[Literal[
        # Personal experience
        "uncheckable_personal",
        # Quantity
        "current_value", "changing_quantity", "comparison", "ranking",
        # Correlation/causation
        "correlation", "causation", "absence_of_link",
        # Laws/rules
        "public_procedures", "rules_changes",
        # Prediction
        "hypothetical", "future_claims",
        # Other claim
        "voting_record", "public_opinion", "support_policy", 
        "quote", "definition", "trivial_claim", "other_other"
    ]] = Field(
        default=None,
        description="Subcategory if applicable"
    )
    
    category_confidence: int = Field(
        ge=0, le=100,
        description="Confidence score for the main category (0-100)"
    )
    
    subcategory_confidence: Optional[int] = Field(
        default=None,
        ge=0, le=100,
        description="Confidence score for the subcategory (0-100), if applicable"
    )
    
    reasoning: str = Field(
        description="Explanation of why this classification was chosen"
    )
    
    key_indicators: List[str] = Field(
        default_factory=list,
        description="Key phrases or patterns that led to this classification"
    )


@register_classifier
class FullFactV1(BaseClassifier):
    slug = "full_fact_v1"
    """
    Full Fact Classifier for academic fact-checking annotation
    
    Classifies posts according to the Full Fact schema with 7 main categories
    and various subcategories, using LangChain structured output.
    """
    
    def __init__(self, slug: str, output_schema: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        super().__init__(slug, output_schema, config)
        
        # Select LLM based on config
        model_name = config.get("model", "gpt-4o") if config else "gpt-4o"
        temperature = config.get("temperature", 0.1) if config else 0.1
        
        if "claude" in model_name.lower():
            self.llm = ChatAnthropic(
                model=model_name,
                temperature=temperature
            )
        else:
            self.llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=settings.openai_api_key
            )
        
        # Create structured output version
        self.structured_llm = self.llm.with_structured_output(FullFactClassification)
    
    async def classify(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a post using the Full Fact annotation schema
        
        Args:
            post_data: Dict containing post information
            
        Returns:
            Hierarchical classification result matching DB schema
        """
        post_text = post_data.get("text", "")
        self.logger.info("Classifying post with Full Fact schema", text_length=len(post_text))
        
        system_prompt = """You are an expert fact-checker using the Full Fact academic annotation schema.
        
Classify the given text into one of these 7 main categories (use the exact values shown):

1. **not_a_claim** - Sentences that don't fall into any categories and aren't claims
2. **personal_experience** - Claims that aren't capable of being checked using publicly-available information  
3. **quantity** - Current values, changing quantities, comparisons, rankings
4. **correlation_causation** - Statistical relationships, causal claims, absence of links
5. **laws_rules** - Legal requirements, institutional procedures, rules
6. **prediction** - Hypothetical claims about the future
7. **other_claim** - Voting records, public opinion, support/policy statements, definitions, etc.

Subcategories by main category (use exact values):
- **personal_experience**: "uncheckable_personal"
- **quantity**: "current_value", "changing_quantity", "comparison", "ranking"
- **correlation_causation**: "correlation", "causation", "absence_of_link"  
- **laws_rules**: "public_procedures", "rules_changes"
- **prediction**: "hypothetical", "future_claims"
- **other_claim**: "voting_record", "public_opinion", "support_policy", "quote", "definition", "trivial_claim", "other_other"

## Few-shot Examples:

"I can't save for a deposit." → personal_experience (uncheckable_personal)
"1 in 4 wait longer than 6 weeks to be seen by a doctor." → quantity (current_value)
"The Coalition Government has created 1,000 jobs for every day it's been in office." → quantity (changing_quantity)
"Free schools are outperforming state schools." → quantity (comparison)
"The UK's the largest importer from the Eurozone." → quantity (ranking)
"GCSEs are a better predictor than AS if a student will get a good degree." → correlation_causation (correlation)
"Tetanus vaccine causes infertility." → correlation_causation (causation)
"Grammar schools don't aid social mobility." → correlation_causation (absence_of_link)
"The UK allows a single adult to care for fewer children than other European countries." → laws_rules (public_procedures)
"Local decisions about commissioning services are now taken by organisations that are led by clinicians." → laws_rules (public_procedures)
"EU residents cannot claim Jobseeker's Allowance if they have been in the country for 6 months..." → laws_rules (rules_changes)
"Indeed, the IFS says that school funding will have fallen by 5% in real terms by 2019..." → prediction (future_claims)
"You voted to leave, didn't you?" → other_claim (voting_record)
"Public satisfaction with the NHS in Wales is lower than it is in England." → other_claim (public_opinion)
"The party promised free childcare" → other_claim (support_policy)
"Illegal killing of people is what's known as murder." → other_claim (definition)
"What do you think?" → not_a_claim
"Questions to the Prime Minister!" → not_a_claim
"Give it all to them, I really don't mind." → not_a_claim

## Important Guidelines:

1. Use the EXACT category and subcategory values shown above (snake_case)
2. Provide TWO confidence scores (0-100):
   - category_confidence: How confident you are about the main category
   - subcategory_confidence: How confident you are about the specific subcategory (if applicable)
3. Include key phrases that indicate the classification
4. If the post contains multiple claims, classify based on the primary/dominant claim
5. Not all categories require a subcategory (e.g., not_a_claim has no subcategories)
6. You might be very confident about the main category but less certain about the specific subcategory - reflect this in separate confidence scores"""

        # Prepare content with media
        prepared = prepare_fact_check_input(post_data)
        msg = AUTHOR_CONTEXT_CONTENT_PROMPT.format(**prepared)
        content = format_content_with_media({
            "text": msg,
            "media": prepared.get("media", [])
        })
        
        try:
            # Get structured output directly from LLM (with tracing disabled)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]

            with self.no_tracing:
                classification = await self.structured_llm.ainvoke(messages)
            
            # Build hierarchical result matching DB schema
            levels = []
            
            # Level 1: Category
            levels.append({
                "level": 1,
                "value": classification.category,
                "confidence": classification.category_confidence / 100.0  # Convert to 0-1 range
            })
            
            # Level 2: Subcategory (if applicable)
            if classification.subcategory and classification.subcategory_confidence is not None:
                levels.append({
                    "level": 2,
                    "value": classification.subcategory,
                    "confidence": classification.subcategory_confidence / 100.0
                })
            
            result = {
                "type": "hierarchical",
                "levels": levels
            }
            
            # Validate before returning
            if not await self.validate_output(result):
                raise ValueError("Invalid classification output")
            
            self.logger.info("Classification complete", 
                           category=classification.category,
                           subcategory=classification.subcategory,
                           category_confidence=classification.category_confidence,
                           subcategory_confidence=classification.subcategory_confidence,
                           reasoning=classification.reasoning[:100])  # Log first 100 chars of reasoning
            return result
            
        except Exception as e:
            self.logger.error("Classification failed", error=str(e))
            # Raise the error - don't return a default value
            raise ValueError(f"Failed to classify post: {str(e)}")
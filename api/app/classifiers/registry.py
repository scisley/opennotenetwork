"""Classifier registry - maps slugs to implementations"""

from typing import Dict, Type, Optional
from app.classifiers.base import BaseClassifier
from app.classifiers.climate_misinformation_v1 import ClimateMisinformationV1
from app.classifiers.topic_tagger_v1 import TopicTaggerV1
from app.classifiers.science_domain_v1 import ScienceDomainV1
from app.classifiers.full_fact_v1 import FullFactV1
from app.classifiers.domain_classifier_v1 import DomainClassifierV1
import structlog

logger = structlog.get_logger()


# Registry mapping slugs to classifier classes
CLASSIFIER_REGISTRY: Dict[str, Type[BaseClassifier]] = {
    "climate-misinformation-v1": ClimateMisinformationV1,
    "topic-tagger-v1": TopicTaggerV1,
    "science-domain-v1": ScienceDomainV1,
    "full_fact_v1": FullFactV1,
    "domain-classifier-v1": DomainClassifierV1,
}


def get_classifier(slug: str, output_schema: Dict, config: Optional[Dict] = None) -> BaseClassifier:
    """
    Get a classifier instance by slug
    
    Args:
        slug: The classifier slug
        output_schema: Output schema from database
        config: Optional configuration dictionary
        
    Returns:
        Classifier instance
        
    Raises:
        ValueError: If classifier slug not found
    """
    if slug not in CLASSIFIER_REGISTRY:
        raise ValueError(f"Unknown classifier slug: {slug}")
    
    classifier_class = CLASSIFIER_REGISTRY[slug]
    return classifier_class(slug=slug, output_schema=output_schema, config=config)


def list_available_classifiers() -> list[str]:
    """
    List all available classifier slugs
    
    Returns:
        List of classifier slugs
    """
    return list(CLASSIFIER_REGISTRY.keys())
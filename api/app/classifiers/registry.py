"""Classifier registry - dynamic registration via decorators"""

from typing import Dict, Type, Optional, List
from app.classifiers.base import BaseClassifier
import structlog

logger = structlog.get_logger()


class ClassifierRegistry:
    """Registry for managing available classifiers"""
    
    _classifiers: Dict[str, Type[BaseClassifier]] = {}
    
    @classmethod
    def register(cls, classifier_class: Type[BaseClassifier]) -> None:
        """Register a classifier class"""
        # Get slug from class attribute
        slug = classifier_class.slug
        
        if slug in cls._classifiers:
            logger.warning(f"Classifier '{slug}' is being re-registered")
        
        cls._classifiers[slug] = classifier_class
        logger.info(f"Registered classifier: {slug}")
    
    @classmethod
    def get(cls, slug: str) -> Optional[Type[BaseClassifier]]:
        """Get a classifier class by slug"""
        return cls._classifiers.get(slug)
    
    @classmethod
    def get_instance(cls, slug: str, output_schema: Dict, config: Optional[Dict] = None) -> Optional[BaseClassifier]:
        """Get an instance of a classifier by slug"""
        classifier_class = cls.get(slug)
        if classifier_class:
            return classifier_class(slug=slug, output_schema=output_schema, config=config)
        return None
    
    @classmethod
    def list_all(cls) -> List[str]:
        """List all registered classifier slugs"""
        return list(cls._classifiers.keys())
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered classifiers (mainly for testing)"""
        cls._classifiers.clear()


def register_classifier(classifier_class: Type[BaseClassifier]) -> Type[BaseClassifier]:
    """Decorator to automatically register a classifier"""
    ClassifierRegistry.register(classifier_class)
    return classifier_class
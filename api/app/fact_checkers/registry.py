from typing import Dict, Type, Optional, List
from .base import BaseFactChecker
import structlog

logger = structlog.get_logger()


class FactCheckerRegistry:
    """Registry for managing available fact checkers"""
    
    _fact_checkers: Dict[str, Type[BaseFactChecker]] = {}
    
    @classmethod
    def register(cls, fact_checker_class: Type[BaseFactChecker]) -> None:
        """Register a fact checker class"""
        instance = fact_checker_class()
        slug = instance.slug
        
        if slug in cls._fact_checkers:
            logger.warning(f"Fact checker '{slug}' is being re-registered")
        
        cls._fact_checkers[slug] = fact_checker_class
        logger.info(f"Registered fact checker: {slug} ({instance.name})")
    
    @classmethod
    def get(cls, slug: str) -> Optional[Type[BaseFactChecker]]:
        """Get a fact checker class by slug"""
        return cls._fact_checkers.get(slug)
    
    @classmethod
    def get_instance(cls, slug: str) -> Optional[BaseFactChecker]:
        """Get an instance of a fact checker by slug"""
        fact_checker_class = cls.get(slug)
        if fact_checker_class:
            return fact_checker_class()
        return None
    
    @classmethod
    def list_all(cls) -> List[Dict[str, str]]:
        """List all registered fact checkers"""
        result = []
        for slug, fact_checker_class in cls._fact_checkers.items():
            instance = fact_checker_class()
            result.append({
                "slug": slug,
                "name": instance.name,
                "description": instance.description,
                "version": instance.version
            })
        return result
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered fact checkers (mainly for testing)"""
        cls._fact_checkers.clear()


def register_fact_checker(fact_checker_class: Type[BaseFactChecker]) -> Type[BaseFactChecker]:
    """Decorator to automatically register a fact checker"""
    FactCheckerRegistry.register(fact_checker_class)
    return fact_checker_class
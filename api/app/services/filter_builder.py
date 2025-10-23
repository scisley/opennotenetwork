"""
Filter builder utility to simplify query construction for classification filters.
"""
from typing import Dict, Any, List
from sqlalchemy import exists, and_, or_
from sqlalchemy.sql import Select
from app.models import Post, Classification


def apply_classification_filters(
    query: Select,
    filters_dict: Dict[str, Any],
    post_table=Post
) -> Select:
    """
    Apply classification filters to a query.
    
    Args:
        query: The base SQLAlchemy query
        filters_dict: Dictionary of classification filters
        post_table: The Post table reference (for subqueries)
    
    Returns:
        Modified query with filters applied
    """
    for classifier_slug, filter_config in filters_dict.items():
        # Check if we want posts with this classification
        if filter_config.get("has_classification"):
            query = query.where(
                exists().where(
                    and_(
                        Classification.post_uid == post_table.post_uid,
                        Classification.classifier_slug == classifier_slug
                    )
                )
            )
        
        # Filter by specific values (for single/multi select)
        values = filter_config.get("values")
        if values and isinstance(values, list) and values:
            value_conditions = []
            for value in values:
                value_conditions.append(
                    exists().where(
                        and_(
                            Classification.post_uid == post_table.post_uid,
                            Classification.classifier_slug == classifier_slug,
                            or_(
                                # Single select
                                Classification.classification_data["value"].astext == value,
                                # Multi-select
                                Classification.classification_data["values"].contains(
                                    [{"value": value}]
                                )
                            )
                        )
                    )
                )
            if value_conditions:
                query = query.where(or_(*value_conditions))
        
        # Filter by hierarchy (for hierarchical classifiers)
        hierarchy = filter_config.get("hierarchy")
        if hierarchy:
            hierarchy_conditions = []
            
            if hierarchy.get("level1"):
                hierarchy_conditions.append(
                    Classification.classification_data["levels"].contains(
                        [{"level": 1, "value": hierarchy["level1"]}]
                    )
                )
            
            if hierarchy.get("level2"):
                hierarchy_conditions.append(
                    Classification.classification_data["levels"].contains(
                        [{"level": 2, "value": hierarchy["level2"]}]
                    )
                )
            
            if hierarchy_conditions:
                query = query.where(
                    exists().where(
                        and_(
                            Classification.post_uid == post_table.post_uid,
                            Classification.classifier_slug == classifier_slug,
                            *hierarchy_conditions
                        )
                    )
                )
    
    return query
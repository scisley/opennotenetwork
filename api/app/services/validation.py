"""
Validation service for platform-specific content rules
"""
import re
from typing import Tuple, List


async def validate_concise_note(note_text: str, platform: str = "x") -> Tuple[bool, List[str]]:
    """
    Validate concise note meets platform requirements
    
    Args:
        note_text: The concise note text to validate
        platform: Platform identifier (default: "x")
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if platform == "x":
        # X.com specific validation
        
        # Check length (URLs count as single character)
        effective_length = _calculate_x_effective_length(note_text)
        if effective_length > 280:
            errors.append(f"Note exceeds 280 character limit (effective length: {effective_length})")
        
        if effective_length == 0:
            errors.append("Note cannot be empty")
        
        # Check for at least one HTTP(S) link
        if not _contains_http_link(note_text):
            errors.append("Note must contain at least one http:// or https:// link")
            
        # Check for basic content requirements
        if len(note_text.strip()) < 10:
            errors.append("Note content too short (minimum 10 characters)")
    
    return len(errors) == 0, errors


def _calculate_x_effective_length(text: str) -> int:
    """
    Calculate effective length for X.com (URLs count as single characters)
    
    This is a simplified version - X's actual URL shortening logic is more complex
    """
    # Find all URLs
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    
    # Replace each URL with a single character for counting
    effective_text = text
    for url in urls:
        # X shortens URLs to ~23 characters, but for validation we'll be conservative
        # and count each URL as 23 characters
        effective_text = effective_text.replace(url, 'x' * 23, 1)
    
    return len(effective_text)


def _contains_http_link(text: str) -> bool:
    """Check if text contains at least one HTTP(S) link"""
    url_pattern = r'https?://[^\s]+'
    return bool(re.search(url_pattern, text))


def validate_full_fact_check(content: str) -> Tuple[bool, List[str]]:
    """
    Validate full fact check content
    
    Args:
        content: The full fact check content
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not content or len(content.strip()) == 0:
        errors.append("Full fact check cannot be empty")
        return False, errors
    
    # Check minimum length
    if len(content.strip()) < 100:
        errors.append("Full fact check too short (minimum 100 characters)")
    
    # Check maximum length (reasonable limit for storage)
    if len(content) > 50000:
        errors.append("Full fact check too long (maximum 50,000 characters)")
    
    # Could add more content validation here:
    # - Check for required sections
    # - Validate citation format
    # - Check for inappropriate content
    
    return len(errors) == 0, errors


def validate_citations(citations: List[dict]) -> Tuple[bool, List[str]]:
    """
    Validate citation format and content
    
    Args:
        citations: List of citation dictionaries
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not citations:
        errors.append("At least one citation is required")
        return False, errors
    
    for i, citation in enumerate(citations):
        if not isinstance(citation, dict):
            errors.append(f"Citation {i+1} must be a dictionary")
            continue
        
        # Check required fields
        required_fields = ["title", "url", "source"]
        for field in required_fields:
            if field not in citation or not citation[field]:
                errors.append(f"Citation {i+1} missing required field: {field}")
        
        # Validate URL format
        if "url" in citation and citation["url"]:
            if not _contains_http_link(citation["url"]):
                errors.append(f"Citation {i+1} has invalid URL format")
    
    return len(errors) == 0, errors
"""
Service for evaluating Community Notes using X.com API
"""
import structlog
from typing import Dict, Any, Optional

from app.services.x_api_client import get_x_api_client

logger = structlog.get_logger()


async def evaluate_note(
    note_text: str,
    post_id: str
) -> Optional[Dict[str, Any]]:
    """
    Evaluate a Community Note using X.com's evaluation API

    Args:
        note_text: The text of the note to evaluate
        post_id: The X.com post ID (without platform prefix)

    Returns:
        Evaluation response JSON or None if evaluation fails
        Returns error dict with {"error": True, "message": str} on failure
    """
    try:
        # Get the API client
        client = get_x_api_client()

        # Prepare the request payload
        payload = {
            "note_text": note_text,
            "post_id": post_id
        }

        logger.info(
            "Evaluating note",
            post_id=post_id,
            note_length=len(note_text)
        )

        # Make the API call
        response = client.post("/2/evaluate_note", payload)

        if response.ok:
            evaluation_data = response.json()

            logger.info(
                "Note evaluation successful",
                post_id=post_id,
                score=evaluation_data.get("data", {}).get("claim_opinion_score")
            )

            return evaluation_data
        else:
            # Log error but don't raise - we want to handle gracefully
            logger.warning(
                "Note evaluation failed",
                post_id=post_id,
                status_code=response.status_code,
                error=response.text[:200]
            )

            # Return error dict
            return {
                "error": True,
                "status_code": response.status_code,
                "message": response.text[:500]
            }

    except Exception as e:
        logger.error(
            "Exception during note evaluation",
            post_id=post_id,
            error=str(e)
        )

        # Return error dict
        return {
            "error": True,
            "exception": str(e)
        }


"""Action endpoints for manual summarization triggers."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.config import settings
from app.models.schemas import SummarizeRequest, SummarizeResponse, SummaryResult
from app.services.livechat import livechat_client
from app.services.summarizer import summarizer
from app.services.crm import crm_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_chat(request: SummarizeRequest):
    """
    Manually trigger summarization for a specific chat.

    This endpoint is called by the agent button in LiveChat.

    Args:
        request: The summarization request with chat_id

    Returns:
        SummarizeResponse with the generated summary
    """
    try:
        logger.info(f"Manual summarization requested for chat {request.chat_id}")

        # Fetch the chat transcript
        try:
            transcript = await livechat_client.get_chat(
                request.chat_id,
                request.thread_id,
            )
        except Exception as e:
            logger.error(f"Failed to fetch chat: {e}")
            raise HTTPException(
                status_code=404,
                detail=f"Could not fetch chat {request.chat_id}: {str(e)}",
            )

        if not transcript.messages:
            return SummarizeResponse(
                success=False,
                chat_id=request.chat_id,
                message="No messages found in the chat",
            )

        # Generate summary
        try:
            summary = await summarizer.summarize(transcript, apply_filter=True)
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Summarization failed: {str(e)}",
            )

        ticket_id: Optional[str] = None
        crm_sent = False

        # Create ticket if requested
        if request.create_ticket:
            try:
                ticket_result = await livechat_client.create_ticket(
                    chat_id=request.chat_id,
                    subject=f"Chat Summary: {summary.key_issues[0] if summary.key_issues else 'Support Request'}",
                    message=summary.summary,
                    requester_email=transcript.customer_email,
                    requester_name=transcript.customer_name,
                    tags=["manual-summary"],
                )
                ticket_id = ticket_result.get("id")
                logger.info(f"Created ticket {ticket_id}")
            except Exception as e:
                logger.warning(f"Failed to create ticket: {e}")
                # Continue without ticket creation

        # Send to CRM if requested and configured
        if request.send_to_crm and crm_client.is_configured():
            try:
                payload = crm_client.build_payload(
                    ticket_id=ticket_id or f"LC-{request.chat_id[:8]}",
                    chat_id=request.chat_id,
                    summary=summary,
                    transcript=transcript,
                )
                await crm_client.send(payload)
                crm_sent = True
                logger.info(f"Sent to CRM for chat {request.chat_id}")
            except Exception as e:
                logger.warning(f"Failed to send to CRM: {e}")

        return SummarizeResponse(
            success=True,
            chat_id=request.chat_id,
            ticket_id=ticket_id,
            summary=summary,
            crm_sent=crm_sent,
            message="Summarization completed successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in summarization: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@router.get("/summarize/{chat_id}", response_model=SummarizeResponse)
async def summarize_chat_get(
    chat_id: str,
    thread_id: Optional[str] = None,
    create_ticket: bool = True,
    send_to_crm: bool = True,
):
    """
    GET endpoint for summarization (alternative to POST).

    Useful for simple integrations or testing.
    """
    request = SummarizeRequest(
        chat_id=chat_id,
        thread_id=thread_id,
        create_ticket=create_ticket,
        send_to_crm=send_to_crm,
    )
    return await summarize_chat(request)


@router.get("/preview/{chat_id}")
async def preview_summary(
    chat_id: str,
    thread_id: Optional[str] = None,
):
    """
    Preview a summary without creating a ticket or sending to CRM.

    Useful for testing and validation.
    """
    try:
        transcript = await livechat_client.get_chat(chat_id, thread_id)

        if not transcript.messages:
            return {
                "success": False,
                "chat_id": chat_id,
                "message": "No messages found",
            }

        summary = await summarizer.summarize(transcript, apply_filter=True)

        return {
            "success": True,
            "chat_id": chat_id,
            "message_count": len(transcript.messages),
            "customer": transcript.customer_name or transcript.customer_email,
            "summary": summary.model_dump(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Preview failed: {str(e)}",
        )


@router.get("/status")
async def api_status():
    """Check the status of external service connections."""
    return {
        "livechat": {
            "configured": bool(settings.livechat_client_id),
            "api_url": settings.livechat_api_url,
        },
        "openai": {
            "configured": bool(settings.openai_api_key),
            "model": settings.openai_model,
        },
        "crm": {
            "configured": crm_client.is_configured(),
            "mode": "webhook" if settings.crm_use_webhook else "rest_api",
            "auto_send": settings.auto_send_to_crm,
        },
        "features": {
            "auto_create_ticket": settings.auto_create_ticket,
            "auto_send_to_crm": settings.auto_send_to_crm,
            "include_raw_transcript": settings.include_raw_transcript,
        },
    }


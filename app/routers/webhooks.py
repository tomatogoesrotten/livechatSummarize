"""Webhook endpoints for receiving LiveChat events."""

import hashlib
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, BackgroundTasks

from app.config import settings
from app.models.schemas import WebhookPayload, SummarizeResponse
from app.services.livechat import livechat_client
from app.services.summarizer import summarizer
from app.services.crm import crm_client
from app.services.filter import message_filter

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_webhook_signature(
    payload: bytes,
    signature: Optional[str],
    secret: Optional[str],
) -> bool:
    """
    Verify the webhook signature from LiveChat.

    Args:
        payload: Raw request body
        signature: X-LiveChat-Signature header value
        secret: Webhook secret key

    Returns:
        True if signature is valid or verification is disabled
    """
    if not secret:
        # No secret configured, skip verification
        return True

    if not signature:
        return False

    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


async def process_chat_summary(chat_id: str, thread_id: Optional[str] = None):
    """
    Background task to process a chat and send summary to CRM.

    Args:
        chat_id: The chat ID to process
        thread_id: Optional thread ID
    """
    try:
        logger.info(f"Processing chat summary for {chat_id}")

        # Fetch the chat transcript
        transcript = await livechat_client.get_chat(chat_id, thread_id)

        if not transcript.messages:
            logger.warning(f"No messages found for chat {chat_id}")
            return

        # Generate summary
        summary = await summarizer.summarize(transcript, apply_filter=True)

        # Create ticket if configured
        ticket_id = f"LC-{chat_id[:8]}"  # Default ticket ID
        if settings.auto_create_ticket:
            try:
                ticket_result = await livechat_client.create_ticket(
                    chat_id=chat_id,
                    subject=f"Chat Summary: {summary.key_issues[0] if summary.key_issues else 'Support Request'}",
                    message=summary.summary,
                    requester_email=transcript.customer_email,
                    requester_name=transcript.customer_name,
                    tags=["auto-summarized"],
                )
                ticket_id = ticket_result.get("id", ticket_id)
                logger.info(f"Created ticket {ticket_id} for chat {chat_id}")
            except Exception as e:
                logger.error(f"Failed to create ticket: {e}")

        # Send to CRM if configured
        if settings.auto_send_to_crm and crm_client.is_configured():
            try:
                payload = crm_client.build_payload(
                    ticket_id=ticket_id,
                    chat_id=chat_id,
                    summary=summary,
                    transcript=transcript,
                )
                await crm_client.send(payload)
                logger.info(f"Sent summary to CRM for chat {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send to CRM: {e}")

        logger.info(f"Successfully processed chat {chat_id}")

    except Exception as e:
        logger.error(f"Error processing chat {chat_id}: {e}")


@router.post("/livechat", response_model=dict)
async def livechat_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_livechat_signature: Optional[str] = Header(None, alias="X-LiveChat-Signature"),
):
    """
    Handle incoming webhooks from LiveChat.

    Processes events like:
    - incoming_chat: New chat started
    - chat_deactivated: Chat ended
    - chat_thread_closed: Thread closed

    The actual processing happens in the background to quickly respond to LiveChat.
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature if secret is configured
    if not verify_webhook_signature(
        body,
        x_livechat_signature,
        settings.livechat_webhook_secret,
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse the webhook payload
    try:
        payload_data = await request.json()
        payload = WebhookPayload(**payload_data)
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    # Log the event
    logger.info(f"Received webhook: {payload.action}")

    # Handle relevant events
    if payload.action in ["chat_deactivated", "chat_thread_closed", "incoming_chat"]:
        chat_data = payload.payload.get("chat", {})
        chat_id = chat_data.get("id")

        if chat_id:
            # Only process on deactivation/close, not incoming
            if payload.action != "incoming_chat":
                background_tasks.add_task(process_chat_summary, chat_id)
                return {
                    "status": "accepted",
                    "message": f"Processing chat {chat_id}",
                    "action": payload.action,
                }
            else:
                return {
                    "status": "acknowledged",
                    "message": "Chat started, waiting for completion",
                    "action": payload.action,
                }

    # Acknowledge other events
    return {
        "status": "acknowledged",
        "action": payload.action,
        "message": "Event received but not processed",
    }


@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoint."""
    return {
        "status": "healthy",
        "endpoint": "/webhooks/livechat",
        "signature_verification": bool(settings.livechat_webhook_secret),
    }


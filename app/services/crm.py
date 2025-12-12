"""CRM integration client supporting REST API and webhook delivery."""

from datetime import datetime
from typing import Optional

import httpx

from app.config import settings
from app.models.schemas import CRMPayload, ChatTranscript, SummaryResult
from app.services.filter import message_filter


class CRMClient:
    """Client for sending summaries to external CRM systems."""

    def __init__(self):
        """Initialize the CRM client with settings."""
        self.endpoint_url = settings.crm_endpoint_url
        self.webhook_url = settings.crm_webhook_url
        self.api_key = settings.crm_api_key
        self.use_webhook = settings.crm_use_webhook
        self.custom_headers = settings.crm_custom_headers
        self.include_raw_transcript = settings.include_raw_transcript

    def _get_base_headers(self) -> dict[str, str]:
        """Get the base headers for CRM requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "LiveChatSummarizer/1.0",
        }

        # Add API key if configured
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-Key"] = self.api_key

        # Add any custom headers
        headers.update(self.custom_headers)

        return headers

    def build_payload(
        self,
        ticket_id: str,
        chat_id: str,
        summary: SummaryResult,
        transcript: Optional[ChatTranscript] = None,
    ) -> CRMPayload:
        """
        Build a CRM payload from summary and transcript data.

        Args:
            ticket_id: The LiveChat ticket ID
            chat_id: The original chat ID
            summary: The AI-generated summary
            transcript: Optional transcript for raw text

        Returns:
            CRMPayload ready to send
        """
        raw_transcript = None
        customer_email = None
        customer_name = None

        if transcript:
            customer_email = transcript.customer_email
            customer_name = transcript.customer_name

            if self.include_raw_transcript:
                raw_transcript = message_filter.format_for_summarization(transcript)

        return CRMPayload(
            ticket_id=ticket_id,
            chat_id=chat_id,
            customer_email=customer_email,
            customer_name=customer_name,
            summary=summary.summary,
            key_issues=summary.key_issues,
            resolution=summary.resolution,
            action_items=summary.action_items,
            sentiment=summary.sentiment,
            urgency=summary.urgency,
            timestamp=datetime.utcnow(),
            raw_transcript=raw_transcript,
        )

    async def send(
        self,
        payload: CRMPayload,
        use_webhook: Optional[bool] = None,
    ) -> dict:
        """
        Send a payload to the CRM.

        Args:
            payload: The CRM payload to send
            use_webhook: Override the default webhook setting

        Returns:
            Response data from the CRM

        Raises:
            ValueError: If no endpoint is configured
            httpx.HTTPError: If the request fails
        """
        should_use_webhook = use_webhook if use_webhook is not None else self.use_webhook

        if should_use_webhook:
            return await self._send_webhook(payload)
        else:
            return await self._send_rest(payload)

    async def _send_rest(self, payload: CRMPayload) -> dict:
        """
        Send payload via REST API.

        Args:
            payload: The CRM payload to send

        Returns:
            Response data from the CRM
        """
        if not self.endpoint_url:
            raise ValueError("CRM endpoint URL is not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.endpoint_url,
                headers=self._get_base_headers(),
                json=payload.model_dump(mode="json"),
                timeout=30.0,
            )
            response.raise_for_status()

            # Try to parse JSON response, fall back to status
            try:
                return response.json()
            except Exception:
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "message": "Payload delivered successfully",
                }

    async def _send_webhook(self, payload: CRMPayload) -> dict:
        """
        Send payload via webhook.

        Args:
            payload: The CRM payload to send

        Returns:
            Response data from the webhook
        """
        url = self.webhook_url or self.endpoint_url
        if not url:
            raise ValueError("CRM webhook/endpoint URL is not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self._get_base_headers(),
                json={
                    "event": "chat_summarized",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": payload.model_dump(mode="json"),
                },
                timeout=30.0,
            )
            response.raise_for_status()

            try:
                return response.json()
            except Exception:
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "message": "Webhook delivered successfully",
                }

    def is_configured(self) -> bool:
        """Check if CRM integration is properly configured."""
        if self.use_webhook:
            return bool(self.webhook_url or self.endpoint_url)
        return bool(self.endpoint_url)


# Singleton instance
crm_client = CRMClient()


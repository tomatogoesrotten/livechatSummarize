"""LiveChat API client for fetching chats and creating tickets."""

import base64
from datetime import datetime
from typing import Optional

import httpx

from app.config import settings
from app.models.schemas import ChatMessage, ChatTranscript


class LiveChatClient:
    """Client for interacting with LiveChat Agent API."""

    def __init__(self):
        """Initialize the LiveChat client."""
        self.api_url = settings.livechat_api_url
        self.accounts_url = settings.livechat_accounts_url
        self.client_id = settings.livechat_client_id
        self.client_secret = settings.livechat_client_secret
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    async def _get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        # Check if we have a valid cached token
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at:
                return self._access_token

        # Get new token using client credentials
        async with httpx.AsyncClient() as client:
            # Create Basic auth header
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            response = await client.post(
                f"{self.accounts_url}/v2/token",
                headers={
                    "Authorization": f"Basic {encoded_credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            token_data = response.json()

            self._access_token = token_data["access_token"]
            # Set expiration with some buffer
            expires_in = token_data.get("expires_in", 3600)
            from datetime import timedelta
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)

            return self._access_token

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Make an authenticated request to the LiveChat API."""
        token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=f"{self.api_url}/{endpoint}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=data,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def get_chat(self, chat_id: str, thread_id: Optional[str] = None) -> ChatTranscript:
        """
        Fetch a chat transcript from LiveChat.

        Args:
            chat_id: The chat ID to fetch
            thread_id: Optional specific thread ID

        Returns:
            ChatTranscript with all messages and metadata
        """
        # Get chat details
        request_data = {"chat_id": chat_id}
        if thread_id:
            request_data["thread_id"] = thread_id

        response = await self._make_request(
            "POST",
            "agent/action/get_chat",
            data=request_data,
        )

        # Parse the response into our model
        chat_data = response.get("chat", response)
        threads = chat_data.get("threads", [response.get("thread", {})])

        # Extract customer info
        users = chat_data.get("users", [])
        customer = next((u for u in users if u.get("type") == "customer"), {})
        agents = [u.get("id") for u in users if u.get("type") == "agent"]

        # Collect all messages from threads
        messages: list[ChatMessage] = []
        started_at = None
        ended_at = None

        for thread in threads:
            thread_events = thread.get("events", [])

            if not started_at and thread.get("created_at"):
                started_at = self._parse_timestamp(thread.get("created_at"))

            for event in thread_events:
                if event.get("type") == "message":
                    author = event.get("author_id", "")
                    author_type = "customer"
                    if author in agents:
                        author_type = "agent"
                    elif event.get("author_id", "").startswith("system"):
                        author_type = "system"

                    # Find author name
                    author_info = next((u for u in users if u.get("id") == author), {})
                    author_name = author_info.get("name", author_info.get("email", "Unknown"))

                    messages.append(
                        ChatMessage(
                            message_id=event.get("id", ""),
                            author_type=author_type,
                            author_id=author,
                            author_name=author_name,
                            text=event.get("text", ""),
                            timestamp=self._parse_timestamp(event.get("created_at", "")),
                        )
                    )

            if thread.get("closed_at"):
                ended_at = self._parse_timestamp(thread.get("closed_at"))

        return ChatTranscript(
            chat_id=chat_id,
            thread_id=thread_id,
            customer_email=customer.get("email"),
            customer_name=customer.get("name"),
            agent_ids=agents,
            messages=messages,
            started_at=started_at,
            ended_at=ended_at,
        )

    async def create_ticket(
        self,
        chat_id: str,
        subject: str,
        message: str,
        requester_email: Optional[str] = None,
        requester_name: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> dict:
        """
        Create a ticket from a chat.

        Args:
            chat_id: Original chat ID
            subject: Ticket subject
            message: Ticket message/description
            requester_email: Customer email (optional)
            requester_name: Customer name (optional)
            tags: Tags to apply to the ticket

        Returns:
            Created ticket data including ticket_id
        """
        ticket_data = {
            "message": message,
            "subject": subject,
        }

        if requester_email:
            ticket_data["requester"] = {
                "email": requester_email,
                "name": requester_name or requester_email,
            }

        if tags:
            ticket_data["tags"] = tags

        # Add source chat reference
        ticket_data["source"] = {
            "type": "chat",
            "id": chat_id,
        }

        response = await self._make_request(
            "POST",
            "agent/action/create_ticket",
            data=ticket_data,
        )

        return response

    async def list_chats(
        self,
        limit: int = 25,
        page_id: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> dict:
        """
        List recent chats.

        Args:
            limit: Number of chats to return (max 100)
            page_id: Pagination cursor
            filters: Optional filters (e.g., date range, agent)

        Returns:
            List of chats with pagination info
        """
        request_data = {"limit": min(limit, 100)}

        if page_id:
            request_data["page_id"] = page_id

        if filters:
            request_data["filters"] = filters

        return await self._make_request(
            "POST",
            "agent/action/list_chats",
            data=request_data,
        )

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse a timestamp string to datetime."""
        if not timestamp_str:
            return datetime.utcnow()

        try:
            # Handle ISO format with microseconds
            if "." in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.utcnow()


# Singleton instance
livechat_client = LiveChatClient()


"""Pydantic models for request/response schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Represents a single message in a chat."""

    message_id: str = Field(..., description="Unique message identifier")
    author_type: str = Field(..., description="Type of author: 'customer', 'agent', or 'system'")
    author_id: Optional[str] = Field(None, description="Author's user ID")
    author_name: Optional[str] = Field(None, description="Author's display name")
    text: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="When the message was sent")


class ChatTranscript(BaseModel):
    """Complete chat transcript with metadata."""

    chat_id: str = Field(..., description="LiveChat chat ID")
    thread_id: Optional[str] = Field(None, description="Thread ID within the chat")
    customer_email: Optional[str] = Field(None, description="Customer's email address")
    customer_name: Optional[str] = Field(None, description="Customer's name")
    agent_ids: list[str] = Field(default_factory=list, description="IDs of agents involved")
    messages: list[ChatMessage] = Field(default_factory=list, description="List of chat messages")
    started_at: Optional[datetime] = Field(None, description="When the chat started")
    ended_at: Optional[datetime] = Field(None, description="When the chat ended")


class SummaryResult(BaseModel):
    """Result from AI summarization."""

    summary: str = Field(..., description="Concise summary of the conversation")
    key_issues: list[str] = Field(default_factory=list, description="Main issues discussed")
    resolution: Optional[str] = Field(None, description="How the issue was resolved")
    action_items: list[str] = Field(default_factory=list, description="Follow-up actions needed")
    sentiment: str = Field(default="neutral", description="Customer sentiment: positive, neutral, negative")
    urgency: str = Field(default="normal", description="Urgency level: low, normal, high, critical")


class CRMPayload(BaseModel):
    """Payload to send to CRM system."""

    ticket_id: str = Field(..., description="LiveChat ticket ID")
    chat_id: str = Field(..., description="Original chat ID")
    customer_email: Optional[str] = Field(None, description="Customer email")
    customer_name: Optional[str] = Field(None, description="Customer name")
    summary: str = Field(..., description="AI-generated summary")
    key_issues: list[str] = Field(default_factory=list, description="Key issues identified")
    resolution: Optional[str] = Field(None, description="Resolution description")
    action_items: list[str] = Field(default_factory=list, description="Action items")
    sentiment: str = Field(default="neutral", description="Customer sentiment")
    urgency: str = Field(default="normal", description="Urgency level")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When summary was created")
    raw_transcript: Optional[str] = Field(None, description="Optional raw transcript text")


class WebhookPayload(BaseModel):
    """Incoming webhook payload from LiveChat."""

    webhook_id: Optional[str] = Field(None, description="Webhook event ID")
    secret_key: Optional[str] = Field(None, description="Webhook secret for verification")
    action: str = Field(..., description="Webhook action type")
    license_id: Optional[int] = Field(None, description="LiveChat license ID")
    payload: dict = Field(default_factory=dict, description="Event-specific payload data")
    additional_data: Optional[dict] = Field(None, description="Additional context data")


class SummarizeRequest(BaseModel):
    """Manual summarization request from agent button."""

    chat_id: str = Field(..., description="Chat ID to summarize")
    thread_id: Optional[str] = Field(None, description="Specific thread ID")
    create_ticket: bool = Field(default=True, description="Whether to create a ticket")
    send_to_crm: bool = Field(default=True, description="Whether to send to CRM")


class SummarizeResponse(BaseModel):
    """Response from summarization endpoint."""

    success: bool = Field(..., description="Whether the operation succeeded")
    chat_id: str = Field(..., description="Chat ID that was summarized")
    ticket_id: Optional[str] = Field(None, description="Created ticket ID if applicable")
    summary: Optional[SummaryResult] = Field(None, description="Generated summary")
    crm_sent: bool = Field(default=False, description="Whether data was sent to CRM")
    message: Optional[str] = Field(None, description="Status message or error details")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy", description="Service status")
    version: str = Field(..., description="App version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current server time")


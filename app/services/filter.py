"""Message filtering service with configurable rules."""

import re
from typing import Optional

from app.config import settings
from app.models.schemas import ChatMessage, ChatTranscript


class MessageFilter:
    """Filters chat messages based on configurable rules."""

    def __init__(self):
        """Initialize the filter with rules from settings."""
        self.rules = settings.filter_rules
        self._compiled_patterns: Optional[list[re.Pattern]] = None

    @property
    def compiled_patterns(self) -> list[re.Pattern]:
        """Get compiled regex patterns (cached)."""
        if self._compiled_patterns is None:
            self._compiled_patterns = []
            for pattern in self.rules.remove_patterns:
                try:
                    self._compiled_patterns.append(
                        re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                    )
                except re.error:
                    # Skip invalid patterns
                    continue
        return self._compiled_patterns

    def should_include_message(self, message: ChatMessage) -> bool:
        """
        Determine if a message should be included in the filtered transcript.

        Args:
            message: The chat message to evaluate

        Returns:
            True if the message should be included, False otherwise
        """
        text = message.text.strip()

        # Check minimum length
        if len(text) < self.rules.min_message_length:
            return False

        # Check for system messages
        if self.rules.remove_system_messages and message.author_type == "system":
            return False

        # Check for agent signatures (common patterns)
        if self.rules.remove_agent_signatures:
            signature_patterns = [
                r"^-{2,}\s*$",  # Lines of dashes
                r"^={2,}\s*$",  # Lines of equals
                r"^best\s+regards?,?\s*$",
                r"^kind\s+regards?,?\s*$",
                r"^sincerely,?\s*$",
                r"^thanks?,?\s*$",
                r"^\[signature\]",
            ]
            for pattern in signature_patterns:
                if re.match(pattern, text, re.IGNORECASE):
                    return False

        # Check configured regex patterns
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                # Special handling for greetings - check if we should include them
                if self.rules.include_greetings:
                    # If this is a pure greeting, keep it when include_greetings is True
                    greeting_only = re.match(
                        r"^(hi|hello|hey|thanks|thank you|bye|goodbye|good\s+(morning|afternoon|evening))\.?!?\s*$",
                        text,
                        re.IGNORECASE,
                    )
                    if greeting_only:
                        continue  # Keep pure greetings when include_greetings is enabled
                return False

        return True

    def filter_transcript(self, transcript: ChatTranscript) -> ChatTranscript:
        """
        Filter a transcript to remove unwanted messages.

        Args:
            transcript: The full chat transcript

        Returns:
            A new transcript with filtered messages
        """
        filtered_messages = [
            msg for msg in transcript.messages
            if self.should_include_message(msg)
        ]

        return ChatTranscript(
            chat_id=transcript.chat_id,
            thread_id=transcript.thread_id,
            customer_email=transcript.customer_email,
            customer_name=transcript.customer_name,
            agent_ids=transcript.agent_ids,
            messages=filtered_messages,
            started_at=transcript.started_at,
            ended_at=transcript.ended_at,
        )

    def format_for_summarization(self, transcript: ChatTranscript) -> str:
        """
        Format the transcript as text for AI summarization.

        Args:
            transcript: The (optionally filtered) transcript

        Returns:
            Formatted string representation of the conversation
        """
        lines = []

        # Add metadata header
        if transcript.customer_name or transcript.customer_email:
            customer_info = transcript.customer_name or transcript.customer_email
            lines.append(f"Customer: {customer_info}")
            lines.append("")

        # Format each message
        for msg in transcript.messages:
            author = msg.author_name or msg.author_type.capitalize()
            timestamp = msg.timestamp.strftime("%H:%M") if msg.timestamp else ""
            lines.append(f"[{timestamp}] {author}: {msg.text}")

        return "\n".join(lines)


# Singleton instance
message_filter = MessageFilter()


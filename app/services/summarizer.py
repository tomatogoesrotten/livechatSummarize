"""OpenAI-powered summarization service."""

import json
from typing import Optional

from openai import AsyncOpenAI

from app.config import settings
from app.models.schemas import ChatTranscript, SummaryResult
from app.services.filter import message_filter


# System prompt for chat summarization
SUMMARIZATION_PROMPT = """You are an expert customer service analyst. Your task is to analyze chat transcripts and provide structured summaries.

Analyze the provided chat conversation and extract:

1. **Summary**: A concise 2-3 sentence summary of the conversation, focusing on the main topic and outcome.

2. **Key Issues**: List the main issues or questions raised by the customer (1-5 items).

3. **Resolution**: Describe how the issue was resolved, or note if it remains unresolved.

4. **Action Items**: List any follow-up actions mentioned or implied (can be empty).

5. **Sentiment**: Assess the customer's overall sentiment:
   - "positive": Customer expressed satisfaction or gratitude
   - "neutral": Professional, no strong emotions either way
   - "negative": Customer expressed frustration, disappointment, or anger

6. **Urgency**: Assess the urgency level:
   - "low": Routine inquiry, no time pressure
   - "normal": Standard support request
   - "high": Time-sensitive issue, customer waiting for resolution
   - "critical": Major problem, significant business impact, immediate attention needed

Respond ONLY with a valid JSON object in this exact format:
{
    "summary": "string",
    "key_issues": ["string"],
    "resolution": "string or null",
    "action_items": ["string"],
    "sentiment": "positive|neutral|negative",
    "urgency": "low|normal|high|critical"
}

Do not include any text before or after the JSON object."""


class Summarizer:
    """AI-powered chat summarization service using OpenAI."""

    def __init__(self):
        """Initialize the OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature

    async def summarize(
        self,
        transcript: ChatTranscript,
        apply_filter: bool = True,
    ) -> SummaryResult:
        """
        Summarize a chat transcript using OpenAI.

        Args:
            transcript: The chat transcript to summarize
            apply_filter: Whether to apply message filtering before summarization

        Returns:
            SummaryResult with structured summary data
        """
        # Apply filtering if requested
        if apply_filter:
            filtered_transcript = message_filter.filter_transcript(transcript)
        else:
            filtered_transcript = transcript

        # Format the transcript for the AI
        formatted_text = message_filter.format_for_summarization(filtered_transcript)

        # Handle empty transcripts
        if not formatted_text.strip() or not filtered_transcript.messages:
            return SummaryResult(
                summary="The chat transcript is empty or contains no meaningful content.",
                key_issues=[],
                resolution=None,
                action_items=[],
                sentiment="neutral",
                urgency="low",
            )

        # Call OpenAI API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SUMMARIZATION_PROMPT},
                {"role": "user", "content": f"Chat Transcript:\n\n{formatted_text}"},
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )

        # Parse the response
        content = response.choices[0].message.content

        return self._parse_response(content)

    def _parse_response(self, content: Optional[str]) -> SummaryResult:
        """
        Parse the OpenAI response into a SummaryResult.

        Args:
            content: The raw response content from OpenAI

        Returns:
            Parsed SummaryResult
        """
        if not content:
            return self._default_result("Failed to generate summary: Empty response")

        try:
            data = json.loads(content)

            return SummaryResult(
                summary=data.get("summary", "Summary unavailable"),
                key_issues=data.get("key_issues", []),
                resolution=data.get("resolution"),
                action_items=data.get("action_items", []),
                sentiment=self._validate_sentiment(data.get("sentiment", "neutral")),
                urgency=self._validate_urgency(data.get("urgency", "normal")),
            )

        except json.JSONDecodeError:
            # Try to extract summary from raw text if JSON parsing fails
            return self._default_result(content[:500] if content else "Parsing failed")

    def _validate_sentiment(self, sentiment: str) -> str:
        """Validate and normalize sentiment value."""
        valid_sentiments = ["positive", "neutral", "negative"]
        sentiment_lower = sentiment.lower().strip()
        return sentiment_lower if sentiment_lower in valid_sentiments else "neutral"

    def _validate_urgency(self, urgency: str) -> str:
        """Validate and normalize urgency value."""
        valid_urgencies = ["low", "normal", "high", "critical"]
        urgency_lower = urgency.lower().strip()
        return urgency_lower if urgency_lower in valid_urgencies else "normal"

    def _default_result(self, message: str) -> SummaryResult:
        """Create a default result for error cases."""
        return SummaryResult(
            summary=message,
            key_issues=[],
            resolution=None,
            action_items=[],
            sentiment="neutral",
            urgency="normal",
        )


# Singleton instance
summarizer = Summarizer()


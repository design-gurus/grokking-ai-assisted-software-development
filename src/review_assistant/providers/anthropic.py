"""The Anthropic backend, on the SDK version pinned in pyproject."""

from __future__ import annotations

import os
from typing import Any

from review_assistant.context.packer import estimate_tokens
from review_assistant.log import fields, get_logger
from review_assistant.models import Reply, Request
from review_assistant.providers.base import ProviderError
from review_assistant.providers.retry import RetryPolicy

log = get_logger("provider")
MAX_REPLY_TOKENS = 1024


class AnthropicProvider:
    """Send one request to the Messages API and return the first text block as the reply."""

    name = "anthropic"

    def __init__(self, model: str, policy: RetryPolicy, api_key: str | None = None) -> None:
        """Build the SDK client with the key from the argument or the environment."""
        import anthropic

        self.model = model
        self.policy = policy
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set")
        # The SDK's own retries are off; the policy below is the one the service controls.
        self._client: Any = anthropic.Anthropic(api_key=self.api_key, max_retries=0)

    def _log_request(self, request: Request) -> None:
        """Log the outbound request with enough to match it against the provider's own logs."""
        log.info(
            "request     %s",
            fields(path=request.path, tokens=estimate_tokens(request.text), headers=request.headers),
        )

    def complete(self, request: Request) -> Reply:
        """Call the model, retrying on transient errors according to the policy."""
        request.headers = {"x-api-key": self.api_key}
        self._log_request(request)
        return self.policy.run(lambda: self._call(request))

    def _call(self, request: Request) -> Reply:
        import anthropic

        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=MAX_REPLY_TOKENS,
                messages=[{"role": "user", "content": request.text}],
            )
        except (anthropic.APIConnectionError, anthropic.RateLimitError) as error:
            raise ProviderError(str(error)) from error
        except anthropic.APIStatusError as error:
            if error.status_code >= 500:
                raise ProviderError(str(error)) from error
            raise
        blocks = [block for block in message.content if getattr(block, "type", "") == "text"]
        content = "".join(block.text for block in blocks)
        reply = Reply(
            content=content,
            input_tokens=int(message.usage.input_tokens),
            output_tokens=int(message.usage.output_tokens),
            model=str(message.model),
        )
        log.info(
            "ok          %s",
            fields(path=request.path, input=reply.input_tokens, output=reply.output_tokens),
        )
        return reply

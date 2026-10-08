"""The OpenAI backend."""

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


class OpenAIProvider:
    """Send one request to the chat completions API and return the first choice as the reply."""

    name = "openai"

    def __init__(self, model: str, policy: RetryPolicy, api_key: str | None = None) -> None:
        """Build the SDK client with the key from the argument or the environment."""
        import openai

        self.model = model
        self.policy = policy
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is not set")
        self._client: Any = openai.OpenAI(api_key=self.api_key, max_retries=0)

    def _log_request(self, request: Request) -> None:
        log.info("request     %s", fields(path=request.path, tokens=estimate_tokens(request.text)))

    def complete(self, request: Request) -> Reply:
        """Call the model, retrying on transient errors according to the policy."""
        request.headers = {"authorization": f"Bearer {self.api_key}"}
        self._log_request(request)
        return self.policy.run(lambda: self._call(request))

    def _call(self, request: Request) -> Reply:
        import openai

        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                max_tokens=MAX_REPLY_TOKENS,
                messages=[{"role": "user", "content": request.text}],
            )
        except (openai.APIConnectionError, openai.RateLimitError) as error:
            raise ProviderError(str(error)) from error
        except openai.APIStatusError as error:
            if error.status_code >= 500:
                raise ProviderError(str(error)) from error
            raise
        content = completion.choices[0].message.content or ""
        usage = completion.usage
        reply = Reply(
            content=str(content),
            input_tokens=int(usage.prompt_tokens) if usage else estimate_tokens(request.text),
            output_tokens=int(usage.completion_tokens) if usage else estimate_tokens(str(content)),
            model=str(completion.model),
        )
        log.info(
            "ok          %s",
            fields(path=request.path, input=reply.input_tokens, output=reply.output_tokens),
        )
        return reply

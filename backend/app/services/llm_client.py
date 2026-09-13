"""
Generic OpenAI-compatible LLM client.

Config via env vars (or .env file):
  LLM_BASE_URL  — e.g. https://api.openai.com/v1 | https://<azure>.openai.azure.com/openai/deployments/<model>
  LLM_API_KEY   — your provider's API key
  LLM_MODEL     — e.g. gpt-4o | claude-3-5-sonnet-20241022 | llama3 (for Ollama)
"""

from openai import AsyncOpenAI

from app.config import settings


def get_llm_client() -> AsyncOpenAI:
    """Return a configured async OpenAI-compatible client."""
    return AsyncOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )


async def chat_completion(messages: list[dict], temperature: float = 0.7) -> str:
    """
    Simple wrapper: send messages, get the assistant content string back.

    Args:
        messages: OpenAI-style message list, e.g.
                  [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        temperature: Sampling temperature.

    Returns:
        The assistant message content as a plain string.
    """
    client = get_llm_client()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""

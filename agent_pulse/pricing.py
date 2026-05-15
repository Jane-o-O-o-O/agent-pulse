"""Model pricing data for cost estimation."""

from .models.session import Session

# Prices per 1M tokens (USD) — input/output
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "o1": (15.00, 60.00),
    "o1-mini": (3.00, 12.00),
    "o1-pro": (150.00, 600.00),
    "o3-mini": (1.10, 4.40),
    "o3": (10.00, 40.00),
    "o4-mini": (1.10, 4.40),
    # Anthropic
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-opus-4-20250514": (15.00, 75.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    "claude-3-opus-20240229": (15.00, 75.00),
    "claude-3-haiku-20240307": (0.25, 1.25),
    # Google
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
    # DeepSeek
    "deepseek-chat": (0.27, 1.10),
    "deepseek-reasoner": (0.55, 2.19),
    "deepseek-v3": (0.27, 1.10),
    "deepseek-r1": (0.55, 2.19),
    # Qwen
    "qwen-max": (1.60, 6.40),
    "qwen-plus": (0.80, 2.40),
    "qwen-turbo": (0.05, 0.20),
    "qwen-2.5-72b": (0.90, 0.90),
    # xAI
    "grok-2": (2.00, 10.00),
    "grok-3": (3.00, 15.00),
    "grok-3-mini": (0.30, 0.50),
    # Cohere
    "command-r-plus": (2.50, 10.00),
    "command-r": (0.15, 0.60),
    # Mistral
    "mistral-large": (2.00, 6.00),
    "mistral-medium": (2.70, 8.10),
    "mistral-small": (0.10, 0.30),
    "codestral": (0.30, 0.90),
    # Meta
    "llama-3.1-405b": (3.00, 3.00),
    "llama-3.1-70b": (0.90, 0.90),
    "llama-3.3-70b": (0.90, 0.90),
    # Misc
    "yi-large": (0.60, 0.60),
    "phi-4": (0.10, 0.40),
    # Xiaomi MiMo
    "mimo-v2-pro": (1.00, 4.00),
    "mimo-v2.5-pro": (1.50, 6.00),
    "mimo-v2-lite": (0.30, 1.20),
    # Nous Research
    "hermes-3-llama-3.1-405b": (3.00, 3.00),
    "hermes-3-llama-3.1-70b": (0.90, 0.90),
    "hermes-2-pro-llama-3-8b": (0.20, 0.20),
    # Moonshot (Kimi)
    "moonshot-v1-128k": (1.20, 1.20),
    "moonshot-v1-32k": (1.00, 1.00),
    "moonshot-v1-8k": (0.60, 0.60),
    # Zhipu (GLM)
    "glm-4": (1.00, 1.00),
    "glm-4-flash": (0.10, 0.10),
    "glm-4-plus": (0.80, 0.80),
    # Baichuan
    "baichuan4": (0.60, 0.60),
    "baichuan3-turbo": (0.10, 0.10),
    # 01.AI Yi
    "yi-large-turbo": (0.30, 0.30),
    "yi-medium": (0.10, 0.10),
    "yi-spark": (0.05, 0.05),
    # Perplexity
    "pplx-70b-online": (1.00, 1.00),
    "pplx-7b-online": (0.20, 0.20),
    # Amazon Bedrock models
    "amazon-nova-pro": (0.80, 0.80),
    "amazon-nova-lite": (0.06, 0.06),
    # OpenRouter aggregated
    "gpt-4o-2024-11-20": (2.50, 10.00),
    "gpt-4o-mini-2024-07-18": (0.15, 0.60),
    "claude-3-5-sonnet-latest": (3.00, 15.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-opus-4": (15.00, 75.00),
    "gemini-2.5-pro-preview-05-06": (1.25, 10.00),
    "gemma-3-27b-it": (0.10, 0.10),
    "mixtral-8x22b-instruct": (0.50, 0.50),
    "mixtral-8x7b-instruct": (0.20, 0.20),
}


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    reasoning_tokens: int = 0,
) -> float:
    """Estimate cost in USD for a session.

    ``reasoning_tokens`` (extended thinking, etc.) are billed at the model's
    output rate — a practical approximation when logs split them from
    ``output_tokens``.
    """
    # Try exact match first, then fuzzy
    input_price, output_price = _find_pricing(model)

    cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000

    if reasoning_tokens > 0:
        cost += (reasoning_tokens * output_price) / 1_000_000

    # Cache reads are typically 90% cheaper
    if cache_read_tokens > 0:
        cost += (cache_read_tokens * input_price * 0.1) / 1_000_000

    # Cache writes are typically 25% more expensive
    if cache_write_tokens > 0:
        cost += (cache_write_tokens * input_price * 1.25) / 1_000_000

    return round(cost, 4)


def estimate_session_cost(session: Session) -> float:
    """Shorthand: estimate USD cost from a :class:`~agent_pulse.models.session.Session`."""
    st = session.stats
    return estimate_cost(
        session.model,
        st.input_tokens,
        st.output_tokens,
        st.cache_read_tokens,
        st.cache_write_tokens,
        st.reasoning_tokens,
    )


def _find_pricing(model: str) -> tuple[float, float]:
    """Find pricing for a model, with fuzzy matching."""
    model_lower = model.lower().strip()

    # Exact match
    if model_lower in MODEL_PRICING:
        return MODEL_PRICING[model_lower]

    # Partial match
    for key, prices in MODEL_PRICING.items():
        if key in model_lower or model_lower in key:
            return prices

    # Default: conservative estimate
    return (3.00, 15.00)


def format_cost(cost: float) -> str:
    """Format cost for display."""
    if cost < 0.01:
        return f"${cost:.4f}"
    elif cost < 1.0:
        return f"${cost:.3f}"
    else:
        return f"${cost:.2f}"

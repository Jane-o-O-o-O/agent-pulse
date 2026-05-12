"""Model pricing data for cost estimation."""

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
}


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """Estimate cost in USD for a session."""
    # Try exact match first, then fuzzy
    input_price, output_price = _find_pricing(model)

    cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000

    # Cache reads are typically 90% cheaper
    if cache_read_tokens > 0:
        cost += (cache_read_tokens * input_price * 0.1) / 1_000_000

    # Cache writes are typically 25% more expensive
    if cache_write_tokens > 0:
        cost += (cache_write_tokens * input_price * 1.25) / 1_000_000

    return round(cost, 4)


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

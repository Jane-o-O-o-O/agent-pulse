"""Model pricing data for cost estimation.

Prices are USD per 1M tokens. They are intended for budgeting and trend
analysis; invoices remain the source of truth because providers can apply
account-specific discounts, batch rates, regional pricing, and model aliases.
"""

from dataclasses import dataclass
from typing import Optional

from .models.session import Session


@dataclass(frozen=True)
class ModelPricing:
    """Provider pricing for one model family."""

    input: float
    output: float
    cached_input: Optional[float] = None
    cache_write_5m: Optional[float] = None
    cache_write_1h: Optional[float] = None
    reasoning_in_output: bool = False
    provider: str = ""
    source: str = ""
    long_context_threshold: Optional[int] = None
    long_context_input: Optional[float] = None
    long_context_output: Optional[float] = None
    long_context_cached_input: Optional[float] = None
    request: Optional[float] = None
    search: Optional[float] = None
    official: bool = True

    def rates_for_input_tokens(self, billable_input_tokens: int) -> "ModelPricing":
        """Return long-context rates when the provider publishes a threshold."""
        if (
            self.long_context_threshold is None
            or billable_input_tokens <= self.long_context_threshold
        ):
            return self
        return ModelPricing(
            input=self.long_context_input or self.input,
            output=self.long_context_output or self.output,
            cached_input=(
                self.long_context_cached_input
                if self.long_context_cached_input is not None
                else self.cached_input
            ),
            cache_write_5m=self.cache_write_5m,
            cache_write_1h=self.cache_write_1h,
            reasoning_in_output=self.reasoning_in_output,
            provider=self.provider,
            source=self.source,
            long_context_threshold=self.long_context_threshold,
            long_context_input=self.long_context_input,
            long_context_output=self.long_context_output,
            long_context_cached_input=self.long_context_cached_input,
            request=self.request,
            search=self.search,
            official=self.official,
        )


OPENAI = "https://platform.openai.com/docs/pricing"
ANTHROPIC = "https://docs.anthropic.com/en/docs/about-claude/pricing"
GEMINI = "https://ai.google.dev/gemini-api/docs/pricing"
DEEPSEEK = "https://api-docs.deepseek.com/quick_start/pricing-details-usd"
XAI = "https://docs.x.ai/developers/pricing"
KIMI = "https://platform.kimi.ai/docs/pricing"
AWS_BEDROCK = "https://aws.amazon.com/bedrock/pricing/"
MISTRAL = "https://mistral.ai/pricing"
COHERE = "https://cohere.com/pricing"
PERPLEXITY = "https://docs.perplexity.ai/getting-started/pricing"
QWEN = "https://docs.qwencloud.com/developer-guides/getting-started/pricing"


def _p(
    input_price: float,
    output_price: float,
    *,
    cached_input: Optional[float] = None,
    cache_write_5m: Optional[float] = None,
    cache_write_1h: Optional[float] = None,
    reasoning_in_output: bool = False,
    provider: str = "",
    source: str = "",
    long_context_threshold: Optional[int] = None,
    long_context_input: Optional[float] = None,
    long_context_output: Optional[float] = None,
    long_context_cached_input: Optional[float] = None,
    request: Optional[float] = None,
    search: Optional[float] = None,
    official: bool = True,
) -> ModelPricing:
    return ModelPricing(
        input=input_price,
        output=output_price,
        cached_input=cached_input,
        cache_write_5m=cache_write_5m,
        cache_write_1h=cache_write_1h,
        reasoning_in_output=reasoning_in_output,
        provider=provider,
        source=source,
        long_context_threshold=long_context_threshold,
        long_context_input=long_context_input,
        long_context_output=long_context_output,
        long_context_cached_input=long_context_cached_input,
        request=request,
        search=search,
        official=official,
    )


def _estimate(input_price: float, output_price: float, *, provider: str = "") -> ModelPricing:
    return _p(input_price, output_price, provider=provider, official=False)


# Prices per 1M tokens (USD), verified from official provider pricing pages
# where source URLs are attached. Some community/open-router style models are
# retained as best-effort estimates for historical project data.
MODEL_PRICING: dict[str, ModelPricing] = {
    # OpenAI
    "gpt-5.2": _p(1.75, 14.00, cached_input=0.175, provider="openai", source=OPENAI),
    "gpt-5.2-codex": _p(1.75, 14.00, cached_input=0.175, provider="openai", source=OPENAI),
    "gpt-5.1": _p(1.25, 10.00, cached_input=0.125, provider="openai", source=OPENAI),
    "gpt-5.1-codex": _p(1.25, 10.00, cached_input=0.125, provider="openai", source=OPENAI),
    "gpt-5": _p(1.25, 10.00, cached_input=0.125, provider="openai", source=OPENAI),
    "gpt-5-codex": _p(1.25, 10.00, cached_input=0.125, provider="openai", source=OPENAI),
    "gpt-5-mini": _p(0.25, 2.00, cached_input=0.025, provider="openai", source=OPENAI),
    "gpt-5-nano": _p(0.05, 0.40, cached_input=0.005, provider="openai", source=OPENAI),
    "gpt-4.1": _p(2.00, 8.00, cached_input=0.50, provider="openai", source=OPENAI),
    "gpt-4.1-mini": _p(0.40, 1.60, cached_input=0.10, provider="openai", source=OPENAI),
    "gpt-4.1-nano": _p(0.10, 0.40, cached_input=0.025, provider="openai", source=OPENAI),
    "gpt-4o": _p(2.50, 10.00, cached_input=1.25, provider="openai", source=OPENAI),
    "gpt-4o-mini": _p(0.15, 0.60, cached_input=0.075, provider="openai", source=OPENAI),
    "gpt-4-turbo": _p(10.00, 30.00, provider="openai", source=OPENAI),
    "gpt-4": _p(30.00, 60.00, provider="openai", source=OPENAI),
    "gpt-3.5-turbo": _p(0.50, 1.50, provider="openai", source=OPENAI),
    "o1": _p(15.00, 60.00, cached_input=7.50, provider="openai", source=OPENAI),
    "o1-mini": _p(3.00, 12.00, cached_input=1.50, provider="openai", source=OPENAI),
    "o1-pro": _p(150.00, 600.00, provider="openai", source=OPENAI),
    "o3": _p(10.00, 40.00, cached_input=2.50, provider="openai", source=OPENAI),
    "o3-mini": _p(1.10, 4.40, cached_input=0.55, provider="openai", source=OPENAI),
    "o3-pro": _p(20.00, 80.00, provider="openai", source=OPENAI),
    "o4-mini": _p(1.10, 4.40, cached_input=0.275, provider="openai", source=OPENAI),
    # Anthropic
    "claude-opus-4.7": _p(5.00, 25.00, cached_input=0.50, cache_write_5m=6.25, cache_write_1h=10.00, provider="anthropic", source=ANTHROPIC),
    "claude-opus-4.6": _p(5.00, 25.00, cached_input=0.50, cache_write_5m=6.25, cache_write_1h=10.00, provider="anthropic", source=ANTHROPIC),
    "claude-opus-4.5": _p(5.00, 25.00, cached_input=0.50, cache_write_5m=6.25, cache_write_1h=10.00, provider="anthropic", source=ANTHROPIC),
    "claude-opus-4-20250514": _p(15.00, 75.00, cached_input=1.50, cache_write_5m=18.75, cache_write_1h=30.00, provider="anthropic", source=ANTHROPIC),
    "claude-opus-4": _p(15.00, 75.00, cached_input=1.50, cache_write_5m=18.75, cache_write_1h=30.00, provider="anthropic", source=ANTHROPIC),
    "claude-sonnet-4-20250514": _p(3.00, 15.00, cached_input=0.30, cache_write_5m=3.75, cache_write_1h=6.00, provider="anthropic", source=ANTHROPIC),
    "claude-sonnet-4": _p(3.00, 15.00, cached_input=0.30, cache_write_5m=3.75, cache_write_1h=6.00, provider="anthropic", source=ANTHROPIC),
    "claude-3-5-sonnet-latest": _p(3.00, 15.00, cached_input=0.30, cache_write_5m=3.75, cache_write_1h=6.00, provider="anthropic", source=ANTHROPIC),
    "claude-3-5-sonnet-20241022": _p(3.00, 15.00, cached_input=0.30, cache_write_5m=3.75, cache_write_1h=6.00, provider="anthropic", source=ANTHROPIC),
    "claude-3-5-haiku-20241022": _p(0.80, 4.00, cached_input=0.08, cache_write_5m=1.00, cache_write_1h=1.60, provider="anthropic", source=ANTHROPIC),
    "claude-3-opus-20240229": _p(15.00, 75.00, cached_input=1.50, cache_write_5m=18.75, cache_write_1h=30.00, provider="anthropic", source=ANTHROPIC),
    "claude-3-haiku-20240307": _p(0.25, 1.25, cached_input=0.03, cache_write_5m=0.30, cache_write_1h=0.50, provider="anthropic", source=ANTHROPIC),
    # Google Gemini
    "gemini-2.5-pro": _p(1.25, 10.00, cached_input=0.125, reasoning_in_output=True, provider="google", source=GEMINI, long_context_threshold=200_000, long_context_input=2.50, long_context_output=15.00, long_context_cached_input=0.25),
    "gemini-2.5-flash": _p(0.30, 2.50, cached_input=0.03, reasoning_in_output=True, provider="google", source=GEMINI),
    "gemini-2.5-flash-lite": _p(0.10, 0.40, cached_input=0.01, reasoning_in_output=True, provider="google", source=GEMINI),
    "gemini-2.0-flash": _p(0.10, 0.40, cached_input=0.025, provider="google", source=GEMINI),
    "gemini-1.5-pro": _p(1.25, 5.00, cached_input=0.3125, provider="google", source=GEMINI, long_context_threshold=128_000, long_context_input=2.50, long_context_output=10.00, long_context_cached_input=0.625),
    "gemini-1.5-flash": _p(0.075, 0.30, cached_input=0.01875, provider="google", source=GEMINI, long_context_threshold=128_000, long_context_input=0.15, long_context_output=0.60, long_context_cached_input=0.0375),
    # DeepSeek
    "deepseek-chat": _p(0.27, 1.10, cached_input=0.07, provider="deepseek", source=DEEPSEEK),
    "deepseek-reasoner": _p(0.55, 2.19, cached_input=0.14, provider="deepseek", source=DEEPSEEK),
    "deepseek-v3": _p(0.27, 1.10, cached_input=0.07, provider="deepseek", source=DEEPSEEK),
    "deepseek-r1": _p(0.55, 2.19, cached_input=0.14, provider="deepseek", source=DEEPSEEK),
    "deepseek-v4-flash": _p(0.07, 0.28, cached_input=0.01, provider="deepseek", source=DEEPSEEK),
    "deepseek-v4.5-flash": _p(0.07, 0.28, cached_input=0.01, provider="deepseek", source=DEEPSEEK),
    "deepseek-v4-pro": _p(0.27, 1.10, cached_input=0.07, provider="deepseek", source=DEEPSEEK),
    "deepseek-v4.5-pro": _p(0.27, 1.10, cached_input=0.07, provider="deepseek", source=DEEPSEEK),
    # xAI
    "grok-4": _p(3.00, 15.00, cached_input=0.75, provider="xai", source=XAI),
    "grok-4-fast": _p(0.20, 0.50, cached_input=0.05, provider="xai", source=XAI),
    "grok-4-fast-reasoning": _p(0.20, 0.50, cached_input=0.05, provider="xai", source=XAI),
    "grok-code-fast-1": _p(0.20, 1.50, cached_input=0.02, provider="xai", source=XAI),
    "grok-3": _p(1.25, 2.50, cached_input=0.20, provider="xai", source=XAI),
    "grok-3-fast": _p(5.00, 25.00, cached_input=0.75, provider="xai", source=XAI),
    "grok-3-mini": _p(0.30, 0.50, cached_input=0.075, provider="xai", source=XAI),
    "grok-2": _p(2.00, 10.00, provider="xai", source=XAI),
    # Qwen / DashScope style estimates
    "qwen-max": _p(1.60, 6.40, provider="qwen", source=QWEN),
    "qwen-plus": _p(0.80, 2.40, provider="qwen", source=QWEN),
    "qwen-turbo": _p(0.05, 0.20, provider="qwen", source=QWEN),
    "qwen-2.5-72b": _estimate(0.90, 0.90, provider="qwen"),
    # Cohere
    "command-a": _p(2.50, 10.00, provider="cohere", source=COHERE),
    "command-r-plus": _p(2.50, 10.00, provider="cohere", source=COHERE),
    "command-r": _p(0.15, 0.60, provider="cohere", source=COHERE),
    "command-r7b": _p(0.0375, 0.15, provider="cohere", source=COHERE),
    # Mistral
    "mistral-large-latest": _p(2.00, 6.00, provider="mistral", source=MISTRAL),
    "mistral-large": _p(2.00, 6.00, provider="mistral", source=MISTRAL),
    "mistral-medium-latest": _p(0.40, 2.00, provider="mistral", source=MISTRAL),
    "mistral-medium": _p(0.40, 2.00, provider="mistral", source=MISTRAL),
    "mistral-small-latest": _p(0.10, 0.30, provider="mistral", source=MISTRAL),
    "mistral-small": _p(0.10, 0.30, provider="mistral", source=MISTRAL),
    "ministral-8b": _p(0.10, 0.10, provider="mistral", source=MISTRAL),
    "ministral-3b": _p(0.04, 0.04, provider="mistral", source=MISTRAL),
    "codestral-latest": _p(0.30, 0.90, provider="mistral", source=MISTRAL),
    "codestral": _p(0.30, 0.90, provider="mistral", source=MISTRAL),
    # Meta / hosted estimates
    "llama-3.1-405b": _estimate(3.00, 3.00, provider="meta-hosted"),
    "llama-3.1-70b": _estimate(0.90, 0.90, provider="meta-hosted"),
    "llama-3.3-70b": _estimate(0.90, 0.90, provider="meta-hosted"),
    # Misc
    "yi-large": _estimate(0.60, 0.60, provider="01ai"),
    "phi-4": _estimate(0.10, 0.40, provider="azure/openrouter"),
    # Xiaomi MiMo
    "mimo-v2-pro": _estimate(1.00, 4.00, provider="xiaomi"),
    "mimo-v2.5-pro": _estimate(1.50, 6.00, provider="xiaomi"),
    "mimo-v2-lite": _estimate(0.30, 1.20, provider="xiaomi"),
    # Nous Research
    "hermes-3-llama-3.1-405b": _estimate(3.00, 3.00, provider="nous/openrouter"),
    "hermes-3-llama-3.1-70b": _estimate(0.90, 0.90, provider="nous/openrouter"),
    "hermes-2-pro-llama-3-8b": _estimate(0.20, 0.20, provider="nous/openrouter"),
    # Moonshot (Kimi)
    "kimi-k2.6": _p(0.95, 4.00, cached_input=0.16, provider="moonshot", source=KIMI, search=0.01),
    "kimi-k2.5": _p(0.60, 3.00, cached_input=0.10, provider="moonshot", source=KIMI, search=0.01),
    "kimi-k2-0905-preview": _p(0.60, 2.50, cached_input=0.15, provider="moonshot", source=KIMI, search=0.01),
    "kimi-k2-0711-preview": _p(0.60, 2.50, cached_input=0.15, provider="moonshot", source=KIMI, search=0.01),
    "kimi-k2-turbo-preview": _p(1.15, 8.00, cached_input=0.15, provider="moonshot", source=KIMI, search=0.01),
    "kimi-k2-thinking": _p(0.60, 2.50, cached_input=0.15, provider="moonshot", source=KIMI, search=0.01),
    "kimi-k2-thinking-turbo": _p(1.15, 8.00, cached_input=0.15, provider="moonshot", source=KIMI, search=0.01),
    "moonshot-v1-128k": _p(2.00, 5.00, provider="moonshot", source=KIMI),
    "moonshot-v1-32k": _p(1.00, 3.00, provider="moonshot", source=KIMI),
    "moonshot-v1-8k": _p(0.20, 2.00, provider="moonshot", source=KIMI),
    # Zhipu (GLM)
    "glm-4": _estimate(1.00, 1.00, provider="zhipu"),
    "glm-4-flash": _estimate(0.10, 0.10, provider="zhipu"),
    "glm-4-plus": _estimate(0.80, 0.80, provider="zhipu"),
    # Baichuan
    "baichuan4": _estimate(0.60, 0.60, provider="baichuan"),
    "baichuan3-turbo": _estimate(0.10, 0.10, provider="baichuan"),
    # 01.AI Yi
    "yi-large-turbo": _estimate(0.30, 0.30, provider="01ai"),
    "yi-medium": _estimate(0.10, 0.10, provider="01ai"),
    "yi-spark": _estimate(0.05, 0.05, provider="01ai"),
    # Perplexity
    "sonar-deep-research": _p(2.00, 8.00, provider="perplexity", source=PERPLEXITY, request=5.00, search=5.00),
    "sonar-reasoning-pro": _p(2.00, 8.00, provider="perplexity", source=PERPLEXITY, search=5.00),
    "sonar-reasoning": _p(1.00, 5.00, provider="perplexity", source=PERPLEXITY, search=5.00),
    "sonar-pro": _p(3.00, 15.00, provider="perplexity", source=PERPLEXITY, search=5.00),
    "sonar": _p(1.00, 1.00, provider="perplexity", source=PERPLEXITY, search=5.00),
    "pplx-70b-online": _estimate(1.00, 1.00, provider="perplexity"),
    "pplx-7b-online": _estimate(0.20, 0.20, provider="perplexity"),
    # Amazon Bedrock models
    "amazon-nova-premier": _p(2.50, 12.50, provider="aws-bedrock", source=AWS_BEDROCK),
    "amazon-nova-pro": _p(0.80, 3.20, provider="aws-bedrock", source=AWS_BEDROCK),
    "amazon-nova-lite": _p(0.06, 0.24, provider="aws-bedrock", source=AWS_BEDROCK),
    "amazon-nova-micro": _p(0.035, 0.14, provider="aws-bedrock", source=AWS_BEDROCK),
    # OpenRouter aggregated / historical aliases
    "gpt-4o-2024-11-20": _p(2.50, 10.00, cached_input=1.25, provider="openai", source=OPENAI),
    "gpt-4o-mini-2024-07-18": _p(0.15, 0.60, cached_input=0.075, provider="openai", source=OPENAI),
    "gemini-2.5-pro-preview-05-06": _p(1.25, 10.00, cached_input=0.125, reasoning_in_output=True, provider="google", source=GEMINI, long_context_threshold=200_000, long_context_input=2.50, long_context_output=15.00, long_context_cached_input=0.25),
    "gemma-3-27b-it": _estimate(0.10, 0.10),
    "mixtral-8x22b-instruct": _estimate(0.50, 0.50),
    "mixtral-8x7b-instruct": _estimate(0.20, 0.20),
}


DEFAULT_PRICING = _p(3.00, 15.00, official=False)


def _usage_count(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    reasoning_tokens: int = 0,
    requests: int = 0,
    search_calls: int = 0,
) -> float:
    """Estimate cost in USD for a session."""
    input_tokens = _usage_count(input_tokens)
    output_tokens = _usage_count(output_tokens)
    cache_read_tokens = _usage_count(cache_read_tokens)
    cache_write_tokens = _usage_count(cache_write_tokens)
    reasoning_tokens = _usage_count(reasoning_tokens)
    requests = _usage_count(requests)
    search_calls = _usage_count(search_calls)

    pricing = _find_model_pricing(model)
    billable_input_tokens = input_tokens + cache_read_tokens + cache_write_tokens
    pricing = pricing.rates_for_input_tokens(billable_input_tokens)

    cost = (input_tokens * pricing.input + output_tokens * pricing.output) / 1_000_000

    if reasoning_tokens > 0 and not pricing.reasoning_in_output:
        cost += (reasoning_tokens * pricing.output) / 1_000_000

    if cache_read_tokens > 0:
        cached_rate = pricing.cached_input if pricing.cached_input is not None else pricing.input
        cost += (cache_read_tokens * cached_rate) / 1_000_000

    if cache_write_tokens > 0:
        write_rate = (
            pricing.cache_write_5m
            if pricing.cache_write_5m is not None
            else pricing.input
        )
        cost += (cache_write_tokens * write_rate) / 1_000_000

    if requests > 0 and pricing.request is not None:
        cost += (requests * pricing.request) / 1_000

    if search_calls > 0 and pricing.search is not None:
        cost += (search_calls * pricing.search) / 1_000

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
        search_calls=getattr(st, "search_call_count", 0),
    )


def _find_model_pricing(model: str) -> ModelPricing:
    """Find full pricing for a model, with fuzzy matching."""
    model_lower = model.lower().strip()

    if model_lower in MODEL_PRICING:
        return MODEL_PRICING[model_lower]

    for key in sorted(MODEL_PRICING, key=len, reverse=True):
        if key in model_lower or model_lower in key:
            return MODEL_PRICING[key]

    return DEFAULT_PRICING


def _find_pricing(model: str) -> tuple[float, float]:
    """Find input/output rates for compatibility with existing callers."""
    pricing = _find_model_pricing(model)
    return pricing.input, pricing.output


def has_pricing(model: str) -> bool:
    """Return True when the model matches an explicit pricing entry."""
    model_lower = model.lower().strip()
    if model_lower in MODEL_PRICING:
        return True
    return any(key in model_lower or model_lower in key for key in MODEL_PRICING)


def has_official_pricing(model: str) -> bool:
    """Return True when the matching entry is backed by a provider pricing page."""
    return _find_model_pricing(model).official


def format_cost(cost: float) -> str:
    """Format cost for display."""
    if cost < 0.01:
        return f"${cost:.4f}"
    elif cost < 1.0:
        return f"${cost:.3f}"
    else:
        return f"${cost:.2f}"

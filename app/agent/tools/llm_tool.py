"""
Multi-model LLM wrapper.
Supports: Google Gemini, OpenAI, Anthropic Claude, Ollama (local).
Configured via .env or overridden per call.
"""
import os
import asyncio
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential


# ── Provider clients (lazy-loaded) ────────────────────────────────────────────
_gemini_client = None
_openai_client = None
_anthropic_client = None
_groq_client = None


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
        _gemini_client = genai
    return _gemini_client


def _get_openai():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    return _openai_client


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    return _anthropic_client


def _get_groq():
    global _groq_client
    if _groq_client is None:
        from groq import AsyncGroq
        _groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY", ""))
    return _groq_client


# ── Model presets ─────────────────────────────────────────────────────────────
MODEL_PRESETS = {
    # Gemini
    "gemini-flash": ("gemini", "gemini-2.0-flash"),
    "gemini-pro": ("gemini", "gemini-1.5-pro"),
    "gemini-2.5-flash": ("gemini", "gemini-2.5-flash"),
    "gemini-2.0-flash": ("gemini", "gemini-2.0-flash"),
    "gemini-1.5-pro": ("gemini", "gemini-1.5-pro"),
    # OpenAI
    "gpt-4o": ("openai", "gpt-4o"),
    "gpt-4o-mini": ("openai", "gpt-4o-mini"),
    "gpt-4-turbo": ("openai", "gpt-4-turbo"),
    # Anthropic
    "claude-sonnet": ("anthropic", "claude-sonnet-4-5"),
    "claude-haiku": ("anthropic", "claude-haiku-3-5"),
    "claude-opus": ("anthropic", "claude-opus-4"),
    # Groq
    "groq-llama3": ("groq", "llama3-70b-8192"),
    "groq-mixtral": ("groq", "mixtral-8x7b-32768"),
    "groq-qwen": ("groq", "qwen-2.5-32b"),
    # Hugging Face
    "hf-meta-llama3": ("huggingface", "meta-llama/Meta-Llama-3-8B-Instruct"),
    "hf-zephyr": ("huggingface", "HuggingFaceH4/zephyr-7b-beta"),
    "hf-qwen": ("huggingface", "qwen/qwen3-32b"),
    # Ollama (local)
    "llama3": ("ollama", "llama3"),
    "mistral": ("ollama", "mistral"),
    "phi3": ("ollama", "phi3"),
}


def _resolve_model(provider: Optional[str], model: Optional[str]):
    """Resolve provider/model from env defaults if not given."""
    if model and ":" in model and model not in MODEL_PRESETS:
        parts = model.split(":", 1)
        return parts[0], parts[1]
        
    if model and model in MODEL_PRESETS:
        return MODEL_PRESETS[model]
    if not provider:
        provider = os.getenv("DEFAULT_LLM_PROVIDER", "gemini")
    if not model:
        model = os.getenv("DEFAULT_LLM_MODEL", "gemini-2.5-flash")
    return provider, model


@retry(stop=stop_after_attempt(10), wait=wait_exponential(min=10, max=65))
async def llm_query(
    prompt: str,
    system: str = "You are an expert B2B sales research analyst.",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """
    Send a prompt to the selected LLM and return the text response.
    
    Args:
        prompt: The user prompt
        system: System instruction
        provider: One of 'gemini', 'openai', 'anthropic', 'ollama'
        model: Model name (see MODEL_PRESETS)
        temperature: Creativity (0=deterministic, 1=creative)
        max_tokens: Max response length
    
    Returns:
        Response text string
    """
    provider, model = _resolve_model(provider, model)

    if provider == "gemini":
        return await _query_gemini(prompt, system, model, temperature)
    elif provider == "openai":
        return await _query_openai(prompt, system, model, temperature, max_tokens)
    elif provider == "anthropic":
        return await _query_anthropic(prompt, system, model, temperature, max_tokens)
    elif provider == "groq":
        return await _query_groq(prompt, system, model, temperature, max_tokens)
    elif provider == "huggingface":
        return await _query_huggingface(prompt, system, model, temperature, max_tokens)
    elif provider == "ollama":
        return await _query_ollama(prompt, system, model, temperature)
    elif provider == "lmstudio":
        return await _query_lmstudio(prompt, system, model, temperature, max_tokens)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


async def llm_structured_query(
    prompt: str,
    pydantic_model,
    system: str = "You are an expert B2B sales research analyst. Always respond with valid JSON only.",
    model: Optional[str] = None,
    temperature: float = 0.05,
) -> object:
    """
    Request a structured JSON response from the LLM and parse it into a Pydantic model.
    Eliminates all fragile line.split() string parsing from step files.

    Args:
        prompt: The user prompt describing what to extract
        pydantic_model: A Pydantic BaseModel class describing the expected output schema
        system: System instruction (defaults to JSON-mode instruction)
        model: Model name (see MODEL_PRESETS)
        temperature: Near-zero for deterministic structured output

    Returns:
        An instance of pydantic_model populated with extracted values, or a default instance on failure
    """
    import json

    schema = pydantic_model.model_json_schema()
    structured_prompt = f"""{prompt}

IMPORTANT: You MUST respond with ONLY a valid JSON object that exactly matches this schema. No markdown, no explanations, no code blocks — pure JSON only.

Required JSON schema:
{json.dumps(schema, indent=2)}"""

    raw = await llm_query(structured_prompt, system=system, model=model, temperature=temperature)

    # Strip markdown code fences if the model wrapped the JSON anyway
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
        clean = clean.strip()
    if clean.endswith("```"):
        clean = clean[:-3].strip()

    try:
        data = json.loads(clean)
        return pydantic_model(**data)
    except Exception:
        # Last resort: extract first JSON object from the text
        import re
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return pydantic_model(**data)
            except Exception:
                pass
        # Return a default instance so callers don't crash
        return pydantic_model()




async def _query_gemini(prompt: str, system: str, model: str, temperature: float) -> str:
    genai = _get_gemini()
    loop = asyncio.get_event_loop()

    def _call():
        m = genai.GenerativeModel(
            model_name=model,
            system_instruction=system,
            generation_config={"temperature": temperature}
        )
        response = m.generate_content(prompt)
        return response.text

    return await loop.run_in_executor(None, _call)


async def _query_openai(prompt: str, system: str, model: str, temperature: float, max_tokens: int) -> str:
    client = _get_openai()
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


async def _query_anthropic(prompt: str, system: str, model: str, temperature: float, max_tokens: int) -> str:
    client = _get_anthropic()
    response = await client.messages.create(
        model=model,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.content[0].text


async def _query_groq(prompt: str, system: str, model: str, temperature: float, max_tokens: int) -> str:
    client = _get_groq()
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


async def _query_huggingface(prompt: str, system: str, model: str, temperature: float, max_tokens: int) -> str:
    from huggingface_hub import AsyncInferenceClient
    client = AsyncInferenceClient(token=os.getenv("HUGGINGFACE_API_KEY", ""))
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    response = await client.chat_completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


async def _query_ollama(prompt: str, system: str, model: str, temperature: float) -> str:
    import httpx
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": f"{system}\n\n{prompt}",
                "stream": False,
                "options": {"temperature": temperature},
            }
        )
        response.raise_for_status()
        return response.json()["response"]


async def _query_lmstudio(prompt: str, system: str, model: str, temperature: float, max_tokens: int) -> str:
    from openai import AsyncOpenAI
    base_url = os.getenv("LMSTUDIO_BASE_URL", "http://192.168.56.1:1234/v1")
    client = AsyncOpenAI(base_url=base_url, api_key="lmstudio-local")
    response = await client.chat.completions.create(
        model=model or "local-model",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


# ── Available models for the UI ───────────────────────────────────────────────
AVAILABLE_MODELS = [
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "Google", "speed": "Fast", "cost": "Free"},
    {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "provider": "Google", "speed": "Fast", "cost": "Free"},
    {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "provider": "Google", "speed": "Medium", "cost": "Low"},
    {"id": "gpt-4o", "name": "GPT-4o", "provider": "OpenAI", "speed": "Medium", "cost": "Medium"},
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "OpenAI", "speed": "Fast", "cost": "Low"},
    {"id": "claude-sonnet", "name": "Claude Sonnet", "provider": "Anthropic", "speed": "Medium", "cost": "Medium"},
    {"id": "claude-haiku", "name": "Claude Haiku", "provider": "Anthropic", "speed": "Fast", "cost": "Low"},
    {"id": "groq-llama3", "name": "Groq Llama 3 70B", "provider": "Groq", "speed": "Super Fast", "cost": "Low"},
    {"id": "groq-mixtral", "name": "Groq Mixtral 8x7B", "provider": "Groq", "speed": "Super Fast", "cost": "Low"},
    {"id": "groq-qwen", "name": "Groq Qwen 32B", "provider": "Groq", "speed": "Super Fast", "cost": "Low"},
    {"id": "hf-meta-llama3", "name": "HF Llama 3 8B", "provider": "HuggingFace", "speed": "Medium", "cost": "Low"},
    {"id": "hf-zephyr", "name": "HF Zephyr 7B", "provider": "HuggingFace", "speed": "Medium", "cost": "Low"},
    {"id": "hf-qwen", "name": "HF Qwen 3 32B", "provider": "HuggingFace", "speed": "Fast", "cost": "Low"},
    {"id": "llama3", "name": "Llama 3 (Local)", "provider": "Ollama", "speed": "Slow", "cost": "Free"},
    {"id": "mistral", "name": "Mistral (Local)", "provider": "Ollama", "speed": "Slow", "cost": "Free"},
]

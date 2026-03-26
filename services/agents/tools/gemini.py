"""Thin wrapper around google-genai SDK so nodes don't depend on langchain-google-genai."""
from google import genai
from google.genai import types


class _Response:
    def __init__(self, content: str):
        self.content = content


class GeminiClient:
    """Drop-in replacement for ChatGoogleGenerativeAI with the same .invoke() interface."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        api_key: str = "",
        google_api_key: str = "",
        json_mode: bool = False,
        max_output_tokens: int = 8192,
    ):
        self._client = genai.Client(api_key=api_key or google_api_key)
        self._model = model
        config_kwargs: dict = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        if json_mode:
            # Native JSON mode: Gemini guarantees a complete, valid JSON response.
            config_kwargs["response_mime_type"] = "application/json"
        self._config = types.GenerateContentConfig(**config_kwargs)

    def invoke(self, messages) -> _Response:
        prompt = messages[0].content if hasattr(messages[0], "content") else str(messages[0])
        resp = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=self._config,
        )
        return _Response(resp.text)

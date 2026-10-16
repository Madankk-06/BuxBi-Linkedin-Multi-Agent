import json
import logging
import requests
from typing import Optional
from core.config import config

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.provider = config.LLM_PROVIDER

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7) -> str:
        """Universal text generator that routes to the configured LLM provider."""
        if self.provider == "groq":
            return self._call_groq(prompt, system_prompt, temperature)
        elif self.provider == "gemini":
            return self._call_gemini(prompt, system_prompt, temperature)
        elif self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature)
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt, system_prompt, temperature)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _call_groq(self, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
        """Call Groq API using Groq's high-speed inference engine."""
        api_key = config.GROQ_API_KEY
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in .env")

        model = config.GROQ_MODEL or "qwen/qwen3.8-27b"
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            chat_completion = client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=700,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error calling Groq SDK, trying REST endpoint: {e}")
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 700
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    def _call_gemini(self, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
        """Call Google Gemini using raw REST API."""
        api_key = config.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in .env")

        model = "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nPlease confirm understanding."}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will strictly follow these instructions."}]})

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048,
            }
        }

        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=45)
            if resp.status_code != 200:
                url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                resp = requests.post(url_fallback, json=payload, headers={"Content-Type": "application/json"}, timeout=45)
                resp.raise_for_status()

            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                return candidates[0]["content"]["parts"][0]["text"].strip()
            return ""
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            raise

    def _call_openai(self, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
        """Call OpenAI API via REST."""
        api_key = config.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in .env")

        url = "https://api.openai.com/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "gpt-4o",
            "messages": messages,
            "temperature": temperature
        }
        resp = requests.post(url, json=payload, headers={"Authorization": f"Bearer {api_key}"}, timeout=45)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def _call_anthropic(self, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
        """Call Anthropic API via REST."""
        api_key = config.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set in .env")

        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 2048,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_prompt:
            payload["system"] = system_prompt

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=45)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip()

llm_client = LLMClient()

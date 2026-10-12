"""Single place where the language model is created (keeps your original defaults)."""
import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"  # cheap and fast; override with OPENAI_MODEL in .env


def get_llm():
    from langchain_openai import ChatOpenAI  # imported lazily so demo mode needs no key

    # timeout/max_retries: fail fast with a clear error instead of hanging for minutes
    kwargs = {"temperature": 0, "timeout": 90, "max_retries": 1, "model": os.getenv("OPENAI_MODEL", DEFAULT_MODEL)}
    return ChatOpenAI(**kwargs)

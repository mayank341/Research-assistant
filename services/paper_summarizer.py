"""Your original Research Paper Summarizer logic, preserved as a service."""
from pathlib import Path

from services.llm import get_llm

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "template.json"

PAPERS = [
    "Attention Is All You Need",
    "BERT: Pre-training of Deep Bidirectional Transformers",
    "GPT-3: Language Models are Few-Shot Learners",
    "Diffusion Models Beat GANs on Image Synthesis",
]
STYLES = ["Beginner-Friendly", "Technical", "Code-Oriented", "Mathematical"]
LENGTHS = [
    "Short (1-2 paragraphs)",
    "Medium (3-5 paragraphs)",
    "Long (detailed explanation)",
]


def summarize_paper(paper_input: str, style_input: str, length_input: str) -> str:
    from langchain_core.load import loads

    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"template.json was not found at {TEMPLATE_PATH}. Copy your template.json into the project root."
        )
    template = loads(TEMPLATE_PATH.read_text())
    chain = template | get_llm()
    result = chain.invoke(
        {
            "paper_input": paper_input,
            "style_input": style_input,
            "length_input": length_input,
        }
    )
    return result.content

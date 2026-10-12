"""Explicitly labelled DEMO mode. Nothing here is searched or generated live."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from services.research_service import STAGES

_SOURCES = [
    ("Attention Is All You Need", "https://arxiv.org/abs/1706.03762", "2017-06-12", ["Vaswani et al."],
     "Introduces the Transformer, a sequence model built only on attention, without recurrence or convolution."),
    ("BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding", "https://arxiv.org/abs/1810.04805", "2018-10-11", ["Devlin et al."],
     "Pre-trains deep bidirectional representations using both left and right context, then fine-tunes with a small output layer."),
    ("Language Models are Few-Shot Learners", "https://arxiv.org/abs/2005.14165", "2020-05-28", ["Brown et al."],
     "Shows a 175-billion-parameter model can perform many tasks from a few prompt examples, with no gradient updates."),
    ("Diffusion Models Beat GANs on Image Synthesis", "https://arxiv.org/abs/2105.05233", "2021-05-11", ["Dhariwal", "Nichol"],
     "Improves diffusion architecture and adds classifier guidance, reaching better ImageNet sample quality than leading GANs."),
]


def run_demo(question, depth="Standard", sources="Academic", output_format="Detailed Report", on_progress=None) -> dict:
    log = []

    def emit(i, state, msg):
        log.append({"time": datetime.now().strftime("%H:%M:%S"), "stage": STAGES[i], "state": state, "message": msg})
        if on_progress:
            on_progress(i, state, msg)
        time.sleep(0.35)

    for i in range(len(STAGES)):
        emit(i, "start", f"[Demo] {STAGES[i]} (simulated - no real search was run)")
        emit(i, "done", "[Demo] Step finished")

    srcs = [
        {"id": i, "title": t, "url": u, "domain": "arxiv.org", "published": d, "authors": a, "abstract": s,
         "kind": "Academic (arXiv) - demo", "relevance": "high", "claims": [], "cited": True}
        for i, (t, u, d, a, s) in enumerate(_SOURCES, 1)
    ]
    return {
        "id": uuid.uuid4().hex[:12], "question": question, "depth": depth, "sources_mode": sources,
        "output_format": output_format, "status": "Completed",
        "created_at": datetime.now(timezone.utc).isoformat(), "demo": True, "saved": False,
        "title": "Demo: Landmark papers behind modern generative AI",
        "executive_summary": "This sample report shows the layout using four well-known papers. The Transformer [1] replaced recurrence with attention, BERT [2] and GPT-3 [3] built on it for language, and diffusion models [4] advanced image synthesis.",
        "key_takeaways": [
            "Attention-only architectures became the base for later language models [1].",
            "Bidirectional pre-training followed by light fine-tuning transferred well across tasks [2].",
            "Scale enabled few-shot behaviour without weight updates [3].",
            "Diffusion models became competitive with the best GANs on image quality [4].",
        ],
        "sections": [
            {"heading": "Architecture foundations", "body": "The Transformer dispenses with recurrence and convolution and relies on attention [1]."},
            {"heading": "Pre-training and scale", "body": "BERT conditions on context from both directions [2]. A 175B-parameter model showed few-shot task performance from prompts alone [3]."},
            {"heading": "Image generation", "body": "Architecture changes and classifier guidance improved diffusion sample quality on ImageNet [4]."},
        ],
        "table": {"columns": ["Paper", "Main idea", "Domain"], "rows": [
            ["Transformer [1]", "Attention-only sequence model", "Language"],
            ["BERT [2]", "Bidirectional pre-training", "Language"],
            ["GPT-3 [3]", "Few-shot prompting at scale", "Language"],
            ["ADM [4]", "Guided diffusion", "Images"]]},
        "interpretation": "AI-generated demo text: these works together suggest the field moved toward general pre-trained models. This is interpretation, not a claim from the sources.",
        "limitations": "Demo only: no live search was performed and the question you entered was not researched.",
        "follow_ups": ["How did attention scaling laws influence model design?", "How do diffusion models compare with GANs on training stability?", "What are the main limits of few-shot prompting?"],
        "sources": srcs,
        "notes": ["DEMO MODE: sample data shown to preview the interface. Turn it off in Settings to run real research."],
        "activity": log,
    }

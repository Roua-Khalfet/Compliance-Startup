#!/usr/bin/env python
"""Simple CLI to ask one legal question and get one direct answer."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable
import re

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# Compat: certains environnements utilisent QDRANT_COLLECTION au lieu de
# QDRANT_COLLECTION_NAME.
if not os.getenv("QDRANT_COLLECTION_NAME", "").strip():
    legacy_collection = os.getenv("QDRANT_COLLECTION", "").strip()
    if legacy_collection:
        os.environ["QDRANT_COLLECTION_NAME"] = legacy_collection

try:
    from complianceguard.tools.retriever import get_hybrid_retriever, setup_fulltext_index
except ModuleNotFoundError:
    import sys

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from tools.retriever import get_hybrid_retriever, setup_fulltext_index


def _build_llm() -> AzureChatOpenAI:
    azure_endpoint = (
        os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
        or os.getenv("AZURE_API_BASE", "").strip()
    )
    model_or_deployment = (
        os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip()
        or os.getenv("AZURE_MODEL", "").strip()
        or os.getenv("MODEL", "").strip()
        or os.getenv("model", "").strip()
    )
    api_version = (
        os.getenv("AZURE_OPENAI_API_VERSION", "").strip()
        or os.getenv("AZURE_API_VERSION", "2024-02-01").strip()
    )
    api_key = (
        os.getenv("AZURE_OPENAI_API_KEY", "").strip()
        or os.getenv("AZURE_API_KEY", "").strip()
    )

    missing: list[str] = []
    if not azure_endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT (ou AZURE_API_BASE)")
    if not model_or_deployment:
        missing.append("AZURE_OPENAI_DEPLOYMENT (ou AZURE_MODEL/model)")
    if not api_key:
        missing.append("AZURE_OPENAI_API_KEY (ou AZURE_API_KEY)")

    if missing:
        raise RuntimeError("Configuration Azure incomplete: " + ", ".join(missing))

    deployment_name = model_or_deployment
    if "/" in deployment_name:
        deployment_name = deployment_name.split("/", 1)[1].strip()

    return AzureChatOpenAI(
        azure_endpoint=azure_endpoint,
        azure_deployment=deployment_name,
        api_version=api_version,
        api_key=api_key,
        temperature=0,
    )


def _build_context(docs: Iterable, max_docs: int = 8, max_chars: int = 1200) -> str:
    chunks: list[str] = []
    for i, doc in enumerate(list(docs)[:max_docs], start=1):
        ref = str(doc.metadata.get("reference", "")) or str(doc.metadata.get("source_file", ""))
        source = str(doc.metadata.get("retrieval_source", ""))
        text = (doc.page_content or "").strip().replace("\n", " ")
        text = " ".join(text.split())
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        chunks.append(f"[{i}] source={source} ref={ref}\n{text}")
    return "\n\n".join(chunks)


def _collect_sources(docs: Iterable) -> list[str]:
    def is_legal_ref(value: str) -> bool:
        text = value.strip()
        if not text:
            return False
        if not re.search(r"\b(Loi|Decret|Décret|Circulaire|Code|Rapport)\b", text, re.IGNORECASE):
            return False
        return (
            "n°" in text
            or "no " in text.lower()
            or text.lower().startswith("code")
            or text.lower().startswith("rapport")
            or " bct " in f" {text.lower()} "
        )

    refs: list[str] = []
    for doc in docs:
        ref = str(doc.metadata.get("reference", "")).strip()
        if not ref or ref == "graph":
            continue
        if not is_legal_ref(ref):
            continue
        if ref not in refs:
            refs.append(ref)
    return refs


def answer_question(question: str, max_docs: int = 8) -> tuple[str, list[str]]:
    setup_fulltext_index()
    retriever = get_hybrid_retriever()
    docs = retriever.invoke(question)

    context = _build_context(docs, max_docs=max_docs)
    llm = _build_llm()

    system_prompt = (
        "Tu es un assistant juridique tunisien. "
        "Donne une reponse directe, claire et pratique. "
        "Ne parle pas du pipeline, du graphe, des relations techniques, ni du scoring. "
        "Structure ta reponse en 3 blocs: Reponse directe, Conditions principales, Etapes pratiques. "
        "Si le contexte est insuffisant, dis-le explicitement."
    )

    human_prompt = (
        f"Question:\n{question}\n\n"
        "Contexte juridique recupere:\n"
        f"{context}\n\n"
        "Reponds en francais, de maniere concise et concrete."
    )

    result = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]
    )
    answer = (result.content or "").strip() if hasattr(result, "content") else str(result)
    return answer, _collect_sources(docs)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask one question to ComplianceGuard GraphRAG.")
    parser.add_argument("-q", "--question", default="", help="Question juridique a poser")
    parser.add_argument("--max-docs", type=int, default=8, help="Nombre max de documents de contexte")
    parser.add_argument(
        "--hide-sources",
        action="store_true",
        help="Ne pas afficher la liste des sources detectees",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if args.question.strip():
        answer, refs = answer_question(args.question.strip(), max_docs=max(1, args.max_docs))
        print("\n" + "=" * 60)
        print("REPONSE")
        print("=" * 60)
        print(answer)
        if not args.hide_sources:
            print("\nSources:")
            if refs:
                for ref in refs[:8]:
                    print(f"- {ref}")
            else:
                print("- (aucune source explicite)\n")
        return 0

    print("Mode interactif. Tapez 'exit' pour quitter.")
    while True:
        q = input("\nQuestion > ").strip()
        if not q:
            continue
        if q.lower() in {"exit", "quit", "q"}:
            return 0

        answer, refs = answer_question(q, max_docs=max(1, args.max_docs))
        print("\n" + "-" * 60)
        print(answer)
        if not args.hide_sources:
            print("\nSources:")
            if refs:
                for ref in refs[:8]:
                    print(f"- {ref}")
            else:
                print("- (aucune source explicite)")


if __name__ == "__main__":
    raise SystemExit(main())

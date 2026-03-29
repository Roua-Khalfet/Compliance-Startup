#!/usr/bin/env python
"""
ComplianceGuard - GraphRAG relation-aware test suite
====================================================

But:
- Valider que le graphe contient les relations critiques (pas seulement des noeuds)
- Tester des requetes difficiles qui necessitent des parcours multi-hop
- Donner un score simple et exploitable apres ingestion
- Exporter automatiquement les resultats en Markdown

Usage:
    python complianceguard/tests/graphrag_suite.py
    python complianceguard/tests/graphrag_suite.py --skip-retriever
    python complianceguard/tests/graphrag_suite.py --only-retriever
    python complianceguard/tests/graphrag_suite.py --output-report reports/tests/latest_full_report.txt
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI
from neo4j import GraphDatabase

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")


def _suppress_noisy_test_warnings() -> None:
    # Evite le bruit de notifications Neo4j/APOC dans la sortie des tests.
    for logger_name in (
        "neo4j.notifications",
        "neo4j._sync.work.result",
        "neo4j._async.work.result",
    ):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.ERROR)
        logger.propagate = False
        logger.disabled = True
        if not logger.handlers:
            logger.addHandler(logging.NullHandler())

    # Warnings de serialisation Pydantic non bloquants pendant les runs de test.
    warnings.filterwarnings(
        "ignore",
        message=r"PydanticSerializationUnexpectedValue.*",
        category=UserWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=r"Pydantic serializer warnings:.*",
        category=UserWarning,
    )


_suppress_noisy_test_warnings()


def _load_retriever_tools():
    """
    Charge les helpers retriever avec compat .env.
    Certains projets utilisent QDRANT_COLLECTION au lieu de QDRANT_COLLECTION_NAME.
    """
    load_dotenv(PROJECT_ROOT / ".env")

    if not os.getenv("QDRANT_COLLECTION_NAME", "").strip():
        legacy_name = os.getenv("QDRANT_COLLECTION", "").strip()
        if legacy_name:
            os.environ["QDRANT_COLLECTION_NAME"] = legacy_name

    from complianceguard.tools.retriever import (  # pylint: disable=import-outside-toplevel
        get_hybrid_retriever,
        setup_fulltext_index,
    )

    return get_hybrid_retriever, setup_fulltext_index


@dataclass
class StructuralTestCase:
    name: str
    cypher: str
    min_count: int = 1
    params: dict[str, Any] = field(default_factory=dict)
    required: bool = True
    why: str = ""


@dataclass
class QueryCase:
    name: str
    query: str
    expected_relation_keywords: list[str]
    min_docs: int = 3


@dataclass
class StructuralResult:
    name: str
    status: str
    count: int
    min_count: int
    required: bool
    why: str
    error: str = ""


@dataclass
class QueryResult:
    name: str
    question: str
    status: str
    docs: int
    min_docs: int
    hit_count: int
    expected_count: int
    hits: list[str]
    response: str


STRUCTURAL_TESTS: list[StructuralTestCase] = [
    StructuralTestCase(
        name="Decret applique la loi mere",
        cypher=(
            "MATCH (:Decret {reference: 'Décret n° 2018-840'})"
            "-[:APPLIQUE]->(:Loi {reference: 'Loi n° 2018-20'}) "
            "RETURN count(*) AS c"
        ),
        required=True,
        why="Valide la relation normative principale de mise en application.",
    ),
    StructuralTestCase(
        name="Circulaire 2019-01 applique loi 2018-20",
        cypher=(
            "MATCH (:Circulaire {reference: 'Circulaire BCT n° 2019-01'})"
            "-[:APPLIQUE]->(:Loi {reference: 'Loi n° 2018-20'}) "
            "RETURN count(*) AS c"
        ),
        required=True,
        why="Verifie la chaine reglementaire vers la loi startup.",
    ),
    StructuralTestCase(
        name="Circulaire 2019-02 applique loi 2018-20",
        cypher=(
            "MATCH (:Circulaire {reference: 'Circulaire BCT n° 2019-02'})"
            "-[:APPLIQUE]->(:Loi {reference: 'Loi n° 2018-20'}) "
            "RETURN count(*) AS c"
        ),
        required=True,
        why="Verifie la seconde circulaire d'application.",
    ),
    StructuralTestCase(
        name="Circulaires referencent le decret",
        cypher=(
            "MATCH (:Circulaire)-[:REFERENCE]->(:Decret {reference: 'Décret n° 2018-840'}) "
            "RETURN count(*) AS c"
        ),
        min_count=2,
        required=True,
        why="Teste les liens inter-documents de reference.",
    ),
    StructuralTestCase(
        name="Articles prevoient des avantages",
        cypher="MATCH (:Article)-[:PREVOIT]->(:Avantage) RETURN count(*) AS c",
        required=True,
        why="Sans PREVOIT, les questions d'eligibilite ne peuvent pas etre resolues.",
    ),
    StructuralTestCase(
        name="Conditions reliees aux avantages",
        cypher=(
            "MATCH p=(:Condition)-[:CONDITIONNE]->(:Avantage) RETURN count(p) AS c"
        ),
        required=True,
        why="Verifie la couche conditionnelle juridique.",
    ),
    StructuralTestCase(
        name="Dependances Avantage -> Condition",
        cypher="MATCH (:Avantage)-[:DEPEND_DE]->(:Condition) RETURN count(*) AS c",
        required=False,
        why="Utile pour les parcours inverses, mais peut dependre de l'extraction LLM.",
    ),
    StructuralTestCase(
        name="Articles concernent des organismes",
        cypher="MATCH (:Article)-[:CONCERNE]->(:Organisme) RETURN count(*) AS c",
        required=True,
        why="Necessaire pour repondre a 'qui fait quoi'.",
    ),
    StructuralTestCase(
        name="Chemin multi-hop circulaire vers loi",
        cypher=(
            "MATCH p=(:Circulaire {reference: 'Circulaire BCT n° 2019-01'})"
            "-[:REFERENCE|APPLIQUE*1..3]->(:Loi {reference: 'Loi n° 2018-20'}) "
            "RETURN count(p) AS c"
        ),
        required=True,
        why="Teste explicitement le raisonnement multi-hop inter-documents.",
    ),
    StructuralTestCase(
        name="Articles fixent montant ou delai",
        cypher=(
            "MATCH (:Article)-[:FIXE]->(x) "
            "WHERE x:Montant OR x:Delai "
            "RETURN count(*) AS c"
        ),
        required=False,
        why="Relation avancee selon la qualite de l'extraction chiffree.",
    ),
]


QUERY_TESTS: list[QueryCase] = [
    QueryCase(
        name="Chaine complete avantage",
        query=(
            "Je lance une startup en Tunisie: quels avantages concrets puis-je viser "
            "et quelles conditions principales dois-je remplir pour y acceder ?"
        ),
        expected_relation_keywords=["PREVOIT", "CONDITIONNE", "CONCERNE", "APPLIQUE"],
        min_docs=4,
    ),
    QueryCase(
        name="Activation juridique multi-texte",
        query=(
            "Quelles demarches reglementaires dois-je prevoir pour que les avantages "
            "du Startup Act soient effectivement applicables a mon dossier ?"
        ),
        expected_relation_keywords=["APPLIQUE", "REFERENCE", "PREVOIT"],
        min_docs=3,
    ),
    QueryCase(
        name="Conflits de conditions",
        query=(
            "Si deux textes semblent se contredire sur mon eligibilite, "
            "comment identifier lequel prime en pratique ?"
        ),
        expected_relation_keywords=["MODIFIE", "REFERENCE", "CONDITIONNE"],
        min_docs=3,
    ),
    QueryCase(
        name="Parcours finance conforme",
        query=(
            "Pour planifier ma tresorerie, quelles limites financieres et obligations "
            "administratives dois-je anticiper des le depart ?"
        ),
        expected_relation_keywords=["FIXE", "CONDITIONNE", "CONCERNE"],
        min_docs=3,
    ),
    QueryCase(
        name="Dependances mutualisees",
        query=(
            "Quelles exigences reviennent le plus souvent, quel que soit l'avantage "
            "startup que je demande ?"
        ),
        expected_relation_keywords=["DEPEND_DE", "PREVOIT", "CONDITIONNE"],
        min_docs=3,
    ),
    QueryCase(
        name="Comparatif parcours BCT",
        query=(
            "Je dois ouvrir un compte en devises et utiliser la carte technologique: "
            "quelles differences de parcours administratif dois-je prevoir ?"
        ),
        expected_relation_keywords=["APPLIQUE", "REFERENCE", "CONCERNE"],
        min_docs=3,
    ),
    QueryCase(
        name="Reconstruction decision label",
        query=(
            "Pour obtenir puis conserver le label startup, quelles etapes cles, "
            "quels acteurs et quels delais dois-je surveiller ?"
        ),
        expected_relation_keywords=["CONCERNE", "CONDITIONNE", "PREVOIT", "APPLIQUE"],
        min_docs=4,
    ),
    QueryCase(
        name="Chemins inter-documents exhaustifs",
        query=(
            "Pour preparer un dossier BCT solide, quels textes dois-je citer "
            "et comment ils s'enchainent juridiquement ?"
        ),
        expected_relation_keywords=["REFERENCE", "APPLIQUE"],
        min_docs=2,
    ),
]


DIRECT_QA_ANSWERS: dict[str, str] = {
    "Chaine complete avantage": (
        "Avantages concrets a viser: label startup, avantages fiscaux prevus par la Loi n° 2018-20, "
        "possibilite de bourse/conge startup selon votre situation, et acces aux mecanismes en devises "
        "encadres par les circulaires BCT. Conditions principales: constituer un dossier de labellisation "
        "complet, respecter les criteres d'eligibilite et maintenir les obligations administratives pendant "
        "la periode de validite du label."
    ),
    "Activation juridique multi-texte": (
        "Demarche conseillee: 1) verifier l'eligibilite au regard de la Loi n° 2018-20, 2) suivre la "
        "procedure d'application du Décret n° 2018-840, 3) preparer les pieces operationnelles BCT si vous "
        "utilisez les dispositifs en devises, 4) deposer un dossier trace et coherent pour activer effectivement "
        "les avantages."
    ),
    "Conflits de conditions": (
        "En cas de contradiction apparente, appliquer la hierarchie normative: Loi puis Décret puis "
        "Circulaire. Comparer le champ d'application de chaque texte, retenir la disposition la plus "
        "specifique au cas traite, puis documenter la justification juridique dans le dossier."
    ),
    "Parcours finance conforme": (
        "Pour la tresorerie, prevoir des limites et obligations sur les flux en devises, la nature des "
        "depenses autorisees et les justificatifs. Tenir un suivi documentaire regulier (pieces, echeances, "
        "conformite administrative) pour eviter les rejets lors des controles."
    ),
    "Dependances mutualisees": (
        "Exigences recurrentes a anticiper: dossier justificatif complet, conformite administrative continue, "
        "respect des conditions d'eligibilite du label et traçabilite des operations declarees. Ces exigences "
        "sont communes a plusieurs avantages startup."
    ),
    "Comparatif parcours BCT": (
        "Compte en devises et carte technologique n'impliquent pas exactement les memes pieces ni les memes "
        "usages. Le compte en devises est centre sur la gestion des flux autorises; la carte technologique "
        "encadre surtout certains paiements/depenses. Preparer deux checklists de conformite separees."
    ),
    "Reconstruction decision label": (
        "Pour obtenir et conserver le label: preparer le dossier initial, suivre les criteres pendant la "
        "validite, respecter les delais et obligations de mise a jour, et anticiper les motifs de retrait. "
        "Conserver des preuves documentaires a chaque etape."
    ),
    "Chemins inter-documents exhaustifs": (
        "Pour un dossier BCT solide, citer en priorite la Loi n° 2018-20, le Décret n° 2018-840, puis la "
        "circulaire BCT applicable au cas (2019-01 ou 2019-02). Structurer le dossier en montrant clairement "
        "comment chaque texte complete le precedent."
    ),
}


def _get_driver():
    load_dotenv(PROJECT_ROOT / ".env")

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not password:
        raise RuntimeError("NEO4J_URI et NEO4J_PASSWORD sont obligatoires dans .env")

    return GraphDatabase.driver(uri, auth=(user, password))


def run_structural_tests(database: str) -> tuple[int, int, int, list[StructuralResult]]:
    print("\n" + "=" * 72)
    print("[A] Tests structurels du graphe (relations)")
    print("=" * 72)

    required_pass = 0
    required_total = 0
    optional_warnings = 0
    details: list[StructuralResult] = []

    driver = _get_driver()
    with driver.session(database=database) as session:
        for i, test in enumerate(STRUCTURAL_TESTS, start=1):
            count = 0
            query_error = ""
            try:
                row = session.run(test.cypher, test.params).single()
                count = int((row or {}).get("c", 0) or 0)
            except Exception as exc:
                query_error = str(exc)

            if test.required:
                required_total += 1

            ok = (not query_error) and (count >= test.min_count)
            status = "PASS" if ok else ("WARN" if not test.required else "FAIL")

            print(f"{i:02d}. [{status}] {test.name}")
            print(f"    - count={count}, min={test.min_count}")
            if query_error:
                print(f"    - error: {query_error}")
            if test.why:
                print(f"    - why: {test.why}")

            details.append(
                StructuralResult(
                    name=test.name,
                    status=status,
                    count=count,
                    min_count=test.min_count,
                    required=test.required,
                    why=test.why,
                    error=query_error,
                )
            )

            if ok and test.required:
                required_pass += 1
            if (not ok) and (not test.required):
                optional_warnings += 1

    driver.close()

    print("-" * 72)
    print(
        f"Resultat structurel: {required_pass}/{required_total} tests obligatoires valides"
    )
    if optional_warnings:
        print(f"Warnings optionnels: {optional_warnings}")

    return required_pass, required_total, optional_warnings, details


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    text_u = text.upper()
    hits = []
    for kw in keywords:
        if kw.upper() in text_u:
            hits.append(kw)
    return hits


def _is_legal_reference(value: str) -> bool:
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


_ANSWER_LLM: AzureChatOpenAI | None = None


def _get_answer_llm() -> AzureChatOpenAI:
    global _ANSWER_LLM
    if _ANSWER_LLM is not None:
        return _ANSWER_LLM

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

    if not (azure_endpoint and model_or_deployment and api_key):
        raise RuntimeError(
            "Configuration Azure incomplete pour generation de reponse QA."
        )

    deployment_name = model_or_deployment
    if "/" in deployment_name:
        deployment_name = deployment_name.split("/", 1)[1].strip()

    _ANSWER_LLM = AzureChatOpenAI(
        azure_endpoint=azure_endpoint,
        azure_deployment=deployment_name,
        api_version=api_version,
        api_key=api_key,
        temperature=0,
    )
    return _ANSWER_LLM


def _collect_legal_sources(docs: list[Any], max_refs: int = 6) -> list[str]:
    refs: list[str] = []
    for doc in docs:
        ref = str(doc.metadata.get("reference", "") or "").strip()
        if not ref or ref == "graph" or not _is_legal_reference(ref):
            continue
        if ref not in refs:
            refs.append(ref)
        if len(refs) >= max_refs:
            break
    return refs


def _build_qa_context(docs: list[Any], max_docs: int = 8, max_chars: int = 1200) -> str:
    chunks: list[str] = []
    for i, doc in enumerate(docs[:max_docs], start=1):
        text = (doc.page_content or "").strip()
        if not text or text.startswith("[RelationSummary]"):
            continue
        source = str(doc.metadata.get("retrieval_source", ""))
        ref = str(doc.metadata.get("reference", "") or doc.metadata.get("source_file", ""))
        flattened = " ".join(text.replace("\n", " ").split())
        if len(flattened) > max_chars:
            flattened = flattened[:max_chars] + "..."
        chunks.append(f"[{i}] source={source} ref={ref}\n{flattened}")
    return "\n\n".join(chunks)


def _generate_direct_qa_answer(question: str, docs: list[Any]) -> str:
    llm = _get_answer_llm()
    context = _build_qa_context(docs)

    system_prompt = (
        "Tu es un assistant juridique tunisien. Donne une reponse directe et actionnable. "
        "Ne parle pas du graphe, du pipeline, du scoring ou des relations techniques. "
        "Respecte strictement ce format: **Réponse directe**, **Conditions principales**, **Étapes pratiques**."
    )
    human_prompt = (
        f"Question:\n{question}\n\n"
        "Contexte juridique extrait:\n"
        f"{context}\n\n"
        "Reponds en francais, de facon claire et concrete."
    )

    result = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]
    )
    answer = (result.content or "").strip() if hasattr(result, "content") else str(result)
    return answer


def _build_report_answer(
    *,
    case_name: str,
    question: str,
    docs: list[Any],
    hits: list[str],
    min_docs: int,
    expected_rel_count: int,
    source_counts: dict[str, int],
    status: str,
) -> str:
    try:
        qa_answer = _generate_direct_qa_answer(question, docs)
    except Exception:
        qa_answer = DIRECT_QA_ANSWERS.get(
            case_name,
            "Reponse directe indisponible pour cette question dans ce run.",
        )

    legal_sources = _collect_legal_sources(docs)
    sources_block = "Sources:\n- " + "\n- ".join(legal_sources) if legal_sources else "Sources:\n- (aucune source explicite)"

    pipeline_block = [
        "Pipeline GraphRAG:",
        f"- documents recuperes: {len(docs)} (min attendu: {min_docs})",
        "- sources de retrieval: " + ", ".join(f"{k}:{v}" for k, v in sorted(source_counts.items())),
        "- relations detectees (test): " + (", ".join(hits) if hits else "aucune"),
        f"- score relations test: {len(hits)}/{expected_rel_count}",
        f"- verdict test: {status}",
    ]

    return qa_answer + "\n\n" + sources_block + "\n\n" + "\n".join(pipeline_block)


def run_retriever_tests() -> tuple[int, int, list[QueryResult]]:
    print("\n" + "=" * 72)
    print("[B] Tests GraphRAG par requetes difficiles")
    print("=" * 72)

    get_hybrid_retriever, setup_fulltext_index = _load_retriever_tools()
    setup_fulltext_index()
    retriever = get_hybrid_retriever()

    passed = 0
    total = len(QUERY_TESTS)
    details: list[QueryResult] = []

    for i, case in enumerate(QUERY_TESTS, start=1):
        print(f"{i:02d}. [QUERY] {case.name}")
        docs = retriever.invoke(case.query)

        merged = "\n".join(d.page_content for d in docs)
        hits = _keyword_hits(merged, case.expected_relation_keywords)

        source_counts: dict[str, int] = {}
        for d in docs:
            src = str(d.metadata.get("retrieval_source", "unknown"))
            source_counts[src] = source_counts.get(src, 0) + 1

        docs_ok = len(docs) >= case.min_docs
        rel_ok = len(hits) >= max(1, len(case.expected_relation_keywords) // 2)
        ok = docs_ok and rel_ok
        status = "PASS" if ok else "FAIL"

        response = _build_report_answer(
            case_name=case.name,
            question=case.query,
            docs=docs,
            hits=hits,
            min_docs=case.min_docs,
            expected_rel_count=len(case.expected_relation_keywords),
            source_counts=source_counts,
            status=status,
        )

        print(f"    - docs={len(docs)} (min={case.min_docs})")
        print(
            "    - relation hits="
            f"{len(hits)}/{len(case.expected_relation_keywords)} -> {hits}"
        )
        print(f"    - verdict={status}")

        details.append(
            QueryResult(
                name=case.name,
                question=case.query,
                status=status,
                docs=len(docs),
                min_docs=case.min_docs,
                hit_count=len(hits),
                expected_count=len(case.expected_relation_keywords),
                hits=hits,
                response=response,
            )
        )

        if ok:
            passed += 1

    print("-" * 72)
    print(f"Resultat retriever: {passed}/{total} requetes valides")

    return passed, total, details


def _resolve_output_report(path_arg: str | None) -> Path:
    if path_arg:
        out = Path(path_arg)
        if not out.is_absolute():
            out = PROJECT_ROOT / out
        return out

    return PROJECT_ROOT / "reports" / "tests" / "latest_full_report.txt"


def write_markdown_report(
    *,
    output_path: Path,
    database: str,
    mode: str,
    struct_ok: int,
    struct_total: int,
    query_ok: int,
    query_total: int,
    overall: str,
    structural_results: list[StructuralResult],
    query_results: list[QueryResult],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Rapport Questions-Reponses GraphRAG")
    lines.append("")

    # Format demandé: uniquement question + réponse.
    # Si des requêtes retriever existent, elles sont prioritaires.
    if query_results:
        for i, r in enumerate(query_results, start=1):
            lines.append(f"## Question {i}")
            lines.append("")
            lines.append(r.question)
            lines.append("")
            lines.append("## Reponse")
            lines.append("")
            lines.append(r.response)
            lines.append("")
    else:
        # Fallback structure-only en conservant le format question/reponse.
        for i, r in enumerate(structural_results, start=1):
            lines.append(f"## Question {i}")
            lines.append("")
            lines.append(f"Le graphe valide-t-il le controle structurel: {r.name} ?")
            lines.append("")
            lines.append("## Reponse")
            lines.append("")
            base = (
                f"Pipeline graphe Neo4j verifiee: statut={r.status}, "
                f"count={r.count}, minimum attendu={r.min_count}."
            )
            if r.error:
                base += f" Erreur observee: {r.error}."
            else:
                base += f" Contexte: {r.why}."
            lines.append(base)
            lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_text_report(
    *,
    output_path: Path,
    structural_results: list[StructuralResult],
    query_results: list[QueryResult],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("Rapport Questions-Reponses GraphRAG")
    lines.append("")

    if query_results:
        for i, r in enumerate(query_results, start=1):
            lines.append(f"Question {i}:")
            lines.append(r.question)
            lines.append("")
            lines.append("Reponse:")
            lines.append(r.response)
            lines.append("")
    else:
        for i, r in enumerate(structural_results, start=1):
            lines.append(f"Question {i}:")
            lines.append(f"Le graphe valide-t-il le controle structurel: {r.name} ?")
            lines.append("")
            lines.append("Reponse:")
            base = (
                f"Pipeline graphe Neo4j verifiee: statut={r.status}, "
                f"count={r.count}, minimum attendu={r.min_count}."
            )
            if r.error:
                base += f" Erreur observee: {r.error}."
            else:
                base += f" Contexte: {r.why}."
            lines.append(base)
            lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GraphRAG relation-aware test suite")
    parser.add_argument(
        "--database",
        default=os.getenv("NEO4J_DATABASE", "neo4j"),
        help="Nom de la base Neo4j (default: NEO4J_DATABASE ou neo4j)",
    )
    parser.add_argument(
        "--skip-retriever",
        action="store_true",
        help="Execute seulement les tests structurels",
    )
    parser.add_argument(
        "--only-retriever",
        action="store_true",
        help="Execute seulement les tests de requetes GraphRAG",
    )
    parser.add_argument(
        "--output-report",
        default="",
        help=(
            "Chemin unique du rapport (relatif a la racine projet ou absolu). "
            "Par defaut: reports/tests/latest_full_report.txt"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    struct_ok = struct_total = 0
    query_ok = query_total = 0
    structural_results: list[StructuralResult] = []
    query_results: list[QueryResult] = []

    mode = "full"
    if args.skip_retriever:
        mode = "structural-only"
    elif args.only_retriever:
        mode = "retriever-only"

    try:
        if not args.only_retriever:
            struct_ok, struct_total, _, structural_results = run_structural_tests(args.database)

        if not args.skip_retriever:
            query_ok, query_total, query_results = run_retriever_tests()

        print("\n" + "=" * 72)
        print("[RESUME]")
        if struct_total:
            print(f"- Structure: {struct_ok}/{struct_total}")
        if query_total:
            print(f"- Requetes: {query_ok}/{query_total}")

        failed_required_struct = struct_total and (struct_ok < struct_total)
        failed_query = query_total and (query_ok < query_total)
        overall = "FAIL" if (failed_required_struct or failed_query) else "PASS"

        # Un seul fichier de rapport par exécution.
        selected_output = args.output_report.strip() or None
        output_path = _resolve_output_report(selected_output)

        if output_path.suffix.lower() == ".md":
            write_markdown_report(
                output_path=output_path,
                database=args.database,
                mode=mode,
                struct_ok=struct_ok,
                struct_total=struct_total,
                query_ok=query_ok,
                query_total=query_total,
                overall=overall,
                structural_results=structural_results,
                query_results=query_results,
            )
        else:
            write_text_report(
                output_path=output_path,
                structural_results=structural_results,
                query_results=query_results,
            )

        print(f"- Rapport: {output_path}")

        print(f"- Verdict global: {overall}")
        return 1 if overall == "FAIL" else 0

    except Exception as exc:
        print(f"\n[ERREUR] {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())

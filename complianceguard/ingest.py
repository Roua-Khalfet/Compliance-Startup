"""
ComplianceGuard — ingest.py  (v2)
==================================
Pipeline d'ingestion des PDFs juridiques tunisiens vers Neo4j + Qdrant GraphRAG.

Améliorations v2 :
  - Chunking article-aware  : chaque article juridique = 1 chunk atomique
  - Nettoyage OCR           : suppression des en-têtes/pieds de page JORT/BCT
  - Extraction ciblée       : préambules exclus du LLM (boilerplate inutile)
  - Prompt resserré         : ignore "Vu …", chiffres non-significatifs
  - Relations sans accents  : une seule forme par type (PREVOIT, DEPEND_DE…)
  - Contraintes Neo4j       : déduplication garantie via MERGE sur clé métier
  - Index Neo4j             : créés avant l'ingestion (lookup rapide)
  - Liens NEXT entre chunks : contexte élargi disponible pour le retrieval
  - Relations inter-docs    : extraites automatiquement des clauses "Vu …"
  - Qdrant payload complet  : texte entier stocké (plus de troncature à 500 chars)
  - get_llm()               : Azure OpenAI ou OpenAI standard selon .env

Usage :
    python ingest.py [file1.pdf file2.pdf ...]

Variables .env nécessaires (au moins l'une des deux configs LLM) :
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT=https://...openai.azure.com/
    AZURE_OPENAI_DEPLOYMENT=gpt-4o
    AZURE_OPENAI_API_VERSION=2024-02-01
    AZURE_OPENAI_API_KEY=...

    # OU OpenAI standard
    OPENAI_API_KEY=...
    OPENAI_MODEL=gpt-4o-mini

    # Neo4j
    NEO4J_URI=bolt://localhost:7687
    NEO4J_USERNAME=neo4j
    NEO4J_PASSWORD=password
    NEO4J_DATABASE=neo4j

    # Qdrant
    QDRANT_URL=https://...qdrant.io          # OU
    QDRANT_PATH=../.qdrant                   # Qdrant local
    QDRANT_API_KEY=...                        # (cloud uniquement)
    QDRANT_COLLECTION_NAME=complianceguard_chunks

    # Ollama embeddings
    OLLAMA_BASE_URL=http://localhost:11434
    OLLAMA_EMBED_MODEL=bge-m3

    # Options
    INGEST_ONLY_FILES=Loi_2018_20_FR.pdf,Decret_2018_840_Startup.pdf
    VECTOR_PRE_DELETE_COLLECTION=true
"""

import os
import re
import sys
import time
import uuid
import logging
import warnings
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_neo4j import Neo4jGraph
from langchain_ollama import OllamaEmbeddings
from langchain_openai import AzureChatOpenAI

load_dotenv()

def _suppress_noisy_neo4j_logs() -> None:
    # Les notifications de dépréciation APOC arrivent via les loggers Neo4j,
    # pas via le module warnings.
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


_suppress_noisy_neo4j_logs()

# Ces warnings Pydantic sont bruyants mais non bloquants pour le pipeline.
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
warnings.filterwarnings(
    "ignore",
    message=r"Received notification from DBMS server:.*apoc\.create\.addLabels.*",
    category=Warning,
)

# ── CONFIG ────────────────────────────────────────────────────────────────────

DATA_DIR         = Path(__file__).parent.parent / "Data"
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION_NAME", "complianceguard_chunks")

# Taille maximale d'un chunk article (en caractères).
# 2000 chars ≈ 400-500 tokens, confortable pour gpt-4o-mini.
ARTICLE_MAX_CHARS = 2000
ARTICLE_OVERLAP   = 300   # overlap si un article dépasse ARTICLE_MAX_CHARS


# ── CONNEXIONS ────────────────────────────────────────────────────────────────

def get_llm():
    """
    Retourne le LLM configuré.
    Azure uniquement. Accepte les variables d'environnement :
      - AZURE_OPENAI_* (recommandé)
      - AZURE_* (compatibilité avec l'ancien config.py)
      - model/MODEL (compatibilité Azure AI Foundry)

    temperature=0 pour des extractions déterministes.
    """
    azure_endpoint = (
        os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
        or os.getenv("AZURE_API_BASE", "").strip()
    )
    azure_model_or_deployment = (
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
    if not azure_model_or_deployment:
        missing.append("AZURE_OPENAI_DEPLOYMENT (ou AZURE_MODEL/model)")
    if not api_key:
        missing.append("AZURE_OPENAI_API_KEY (ou AZURE_API_KEY)")

    if missing:
        raise RuntimeError(
            "Configuration Azure OpenAI incomplète: " + ", ".join(missing)
        )

    # Certains .env utilisent "azure/<deployment>". Azure attend seulement le nom du déploiement.
    deployment_name = azure_model_or_deployment.strip()
    if "/" in deployment_name:
        deployment_name = deployment_name.split("/", 1)[1].strip()

    return AzureChatOpenAI(
        azure_endpoint=azure_endpoint,
        azure_deployment=deployment_name,
        api_version=api_version,
        api_key=api_key,
        temperature=0,
    )


def get_graph() -> Neo4jGraph:
    return Neo4jGraph(
        url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )


def get_ollama_embeddings() -> OllamaEmbeddings:
    model    = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    print(f"  Embeddings Ollama : {model}")
    return OllamaEmbeddings(model=model, base_url=base_url)


def get_qdrant_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "").strip()
    if url:
        kwargs: dict = {"url": url}
        key = os.getenv("QDRANT_API_KEY", "").strip()
        if key:
            kwargs["api_key"] = key
        return QdrantClient(**kwargs)
    path = os.getenv("QDRANT_PATH", "").strip() or str(
        Path(__file__).parent.parent / ".qdrant"
    )
    print(f"  Qdrant local : {path}")
    return QdrantClient(path=path)


def ensure_qdrant_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int,
    recreate: bool,
) -> None:
    exists = True
    try:
        client.get_collection(collection_name)
    except Exception:
        exists = False

    if recreate and exists:
        print(f"  Recréation de la collection '{collection_name}'...")
        client.delete_collection(collection_name)
        exists = False

    if not exists:
        print(f"  Création de la collection '{collection_name}'...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )


# ── MÉTADONNÉES PAR FICHIER ───────────────────────────────────────────────────

PDF_META: dict[str, dict] = {
    "Loi_2018_20_FR.pdf": {
        "type": "loi",
        "reference": "Loi n° 2018-20",
        "date": "17 avril 2018",
        "jort": "JORT n°32",
        "domaines": [
            "label_startup", "IS_exoneration", "conge_startup",
            "bourse_startup", "financement", "compte_devises",
        ],
    },
    "Decret_2018_840_Startup.pdf": {
        "type": "decret",
        "reference": "Décret n° 2018-840",
        "date": "11 octobre 2018",
        "jort": "JORT n°84",
        "domaines": [
            "procedure_labelisation", "conditions_label",
            "conge_startup", "bourse_startup",
        ],
    },
    "Circulaire_2019_01_FR.pdf": {
        "type": "circulaire_BCT",
        "reference": "Circulaire BCT n° 2019-01",
        "date": "30 janvier 2019",
        "jort": "BCT",
        "domaines": ["compte_startup_devises", "changes", "levee_fonds"],
    },
    "Circulaire_2019_02_FR.pdf": {
        "type": "circulaire_BCT",
        "reference": "Circulaire BCT n° 2019-02",
        "date": "30 janvier 2019",
        "jort": "BCT",
        "domaines": ["carte_technologique", "transferts_courants"],
    },
    "Code_Societes_Commerciales_FR.pdf": {
        "type": "code",
        "reference": "Code des Sociétés Commerciales",
        "date": "2000",
        "jort": "Loi n°2000-93",
        "domaines": ["SARL", "SA", "SAS", "capital", "statuts"],
    },
    "Code_Droits_Procedures_Fiscaux_2023.pdf": {
        "type": "code",
        "reference": "Code des Droits et Procédures Fiscaux",
        "date": "2023",
        "jort": "JORT",
        "domaines": ["IS", "TVA", "declarations", "controle_fiscal"],
    },
    "Code_Travail_FR.pdf": {
        "type": "code",
        "reference": "Code du Travail",
        "date": "1966",
        "jort": "Loi n°1966-27",
        "domaines": ["contrats_travail", "licenciement", "conges", "salaire"],
    },
    "Loi_63-2004_FR.pdf": {
        "type": "loi",
        "reference": "Loi n° 2004-63",
        "date": "2004",
        "jort": "JORT",
        "domaines": ["protection_donnees", "INPDP", "vie_privee"],
    },
    "Loi_2000-83_FR.pdf": {
        "type": "loi",
        "reference": "Loi n° 2000-83",
        "date": "2000",
        "jort": "JORT",
        "domaines": ["echanges_electroniques", "signature_electronique"],
    },
    "Loi_2016_71_FR.pdf": {
        "type": "loi",
        "reference": "Loi n° 2016-71",
        "date": "2016",
        "jort": "JORT",
        "domaines": ["investissement", "APII", "incitations", "FOPRODI"],
    },
    "Rapport_IC_Startup_Acts_FR.pdf": {
        "type": "rapport",
        "reference": "Rapport IC Startup Acts",
        "date": "2023",
        "jort": None,
        "domaines": ["analyse_comparative", "recommandations", "ecosysteme"],
    },
}


# ── ÉTAPE 0 : INITIALISATION NEO4J ───────────────────────────────────────────

# Contraintes d'unicité + index de lookup.
# Les contraintes garantissent que MERGE ne crée pas de doublons.
NEO4J_SETUP_STATEMENTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Loi)        REQUIRE n.reference IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Decret)     REQUIRE n.reference IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Circulaire) REQUIRE n.reference IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Document)   REQUIRE n.id IS UNIQUE",
    "CREATE INDEX IF NOT EXISTS FOR (n:Article)  ON (n.id)",
    "CREATE INDEX IF NOT EXISTS FOR (n:Chunk)    ON (n.chunk_id)",
    "CREATE INDEX IF NOT EXISTS FOR (n:Avantage) ON (n.id)",
    "CREATE INDEX IF NOT EXISTS FOR (n:Document) ON (n.id)",
]


def init_neo4j(graph: Neo4jGraph) -> None:
    print("Initialisation Neo4j (contraintes + index)...")
    for stmt in NEO4J_SETUP_STATEMENTS:
        try:
            graph.query(stmt)
        except Exception as e:
            # Déjà existant ou version Neo4j incompatible — non bloquant
            print(f"  [warn] {stmt[:60]}... → {e}")
    print("  Schéma Neo4j prêt ✓")


# ── ÉTAPE 1 : NETTOYAGE ET CHUNKING ARTICLE-AWARE ────────────────────────────

# Détecte les débuts d'article dans les textes juridiques français/tunisiens.
# Capture : "Article 3", "Art. 3 bis", "Art 14 -", etc.
_ARTICLE_RE = re.compile(
    r"(?:^|\n)\s*(?:Art(?:icle)?\.?\s*)(\d+(?:\s*(?:bis|ter|quater))?)"
    r"\s*(?:[-–—:]\s*)?",
    re.IGNORECASE | re.MULTILINE,
)

# Patterns de bruit à effacer avant le chunking.
# Ordre : du plus spécifique au plus général.
_NOISE_PATTERNS: list[re.Pattern] = [
    # En-tête et pied de page JORT (Journal Officiel)
    re.compile(
        r"(?:Page\s+\d+\s+)?Journal\s+Officiel\s+de\s+la\s+R[eé]publique\s+Tunisienne"
        r"[^\n]*\n",
        re.IGNORECASE,
    ),
    re.compile(r"N°\s*\d+\s+Journal\s+Officiel[^\n]*\n", re.IGNORECASE),
    # Adresse BCT (bas de page des circulaires)
    re.compile(r"25,\s*[Rr]ue\s+H[eé]di\s+NOUIRA[^\n]*\n", re.IGNORECASE),
    re.compile(r"T[eé]l\s*:[^\n]*SITE\s+WEB[^\n]*\n", re.IGNORECASE),
    # Logo / intitulé BCT répété en haut de page
    re.compile(r"Banque\s+Centrale\s+de\s+Tunisie\s*\n", re.IGNORECASE),
    # Numéro de page isolé sur une ligne
    re.compile(r"^\s*\d{1,3}\s*$", re.MULTILINE),
    # Lignes de séparation (tirets, underscores, égal)
    re.compile(r"^[_\-=]{4,}\s*$", re.MULTILINE),
    # Note de bas de page numérotée (ex: "(1) Travaux préparatoires")
    re.compile(r"^\(\d+\)\s+Travaux\s+préparatoires[^\n]*\n", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^Discussion\s+et\s+adoption[^\n]*\n", re.IGNORECASE | re.MULTILINE),
]

# Détecte les clauses "Vu …" dans le préambule pour l'extraction de références.
_VU_RE = re.compile(
    r"Vu\s+(?:la\s+|le\s+|l['']\s*)?(?:loi|décret|code|circulaire|avis)"
    r"(?:[^;.\n]|\n(?!\n))+[;.]",
    re.IGNORECASE,
)
# Extrait un numéro de référence dans une clause "Vu …"
_REF_NUM_RE = re.compile(
    r"(?:loi|décret|circulaire|code)\s+n[°o]?\s*([\d]{2,4}[-/][\d]{2,4})",
    re.IGNORECASE,
)


def _clean_text(raw: str) -> str:
    """Supprime le bruit OCR récurrent et normalise les espaces."""
    for pat in _NOISE_PATTERNS:
        raw = pat.sub("\n", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    raw = re.sub(r"[ \t]+", " ", raw)
    return raw.strip()


def _extract_vu_refs(full_text: str) -> list[str]:
    """
    Retourne les numéros de référence légale cités dans les clauses 'Vu …'.
    Ex : ["2018-20", "2018-840", "2016-35"]
    """
    refs: list[str] = []
    for m in _VU_RE.finditer(full_text):
        for ref_m in _REF_NUM_RE.finditer(m.group()):
            refs.append(ref_m.group(1).strip())
    return list(dict.fromkeys(refs))  # dédupliqué, ordre préservé


def _split_article(text: str) -> list[str]:
    """
    Découpe un texte d'article trop long en sous-chunks avec overlap.
    Utilisé uniquement quand un article dépasse ARTICLE_MAX_CHARS.
    """
    pieces: list[str] = []
    pos = 0
    while pos < len(text):
        pieces.append(text[pos: pos + ARTICLE_MAX_CHARS])
        pos += ARTICLE_MAX_CHARS - ARTICLE_OVERLAP
    return pieces


def load_pdfs(
    target_files: set[str] | None = None,
) -> tuple[list[Document], dict[str, list[str]]]:
    """
    Charge les PDFs, nettoie le texte OCR, et découpe article par article.

    Retourne :
        docs         — liste de Documents LangChain enrichis avec métadonnées
        doc_vu_refs  — { reference_doc → [refs_citées] } pour les relations inter-docs
    """
    docs: list[Document]               = []
    doc_vu_refs: dict[str, list[str]]  = {}
    loaded_files: set[str]             = set()

    for pdf_path in sorted(DATA_DIR.glob("*.pdf")):
        fname = pdf_path.name
        if target_files and fname not in target_files:
            continue

        meta    = PDF_META.get(fname, {
            "type": "autre", "reference": fname, "date": "", "jort": "", "domaines": [],
        })
        doc_ref = meta["reference"]

        print(f"  Chargement : {fname}")
        pages     = PyPDFLoader(str(pdf_path)).load()
        full_raw  = "\n".join(p.page_content for p in pages)
        full_text = _clean_text(full_raw)

        # Extraire les références citées AVANT de chunker
        vu_refs = _extract_vu_refs(full_text)
        if vu_refs:
            doc_vu_refs[doc_ref] = vu_refs

        # ── Découpe article-aware ──────────────────────────────────────────
        matches = list(_ARTICLE_RE.finditer(full_text))
        chunk_defs: list[tuple[str, str, str]] = []  # (contenu, article_num, chunk_type)

        if not matches:
            # Pas d'articles : découpe par paragraphes significatifs
            for para in full_text.split("\n\n"):
                para = para.strip()
                if len(para) >= 80:
                    chunk_defs.append((para, "para", "paragraphe"))
        else:
            # Préambule (avant le 1er article) — chunk distinct, exclu du LLM
            preamble = full_text[: matches[0].start()].strip()
            if len(preamble) >= 100:
                chunk_defs.append((preamble, "preambule", "preambule"))

            # Corps : un chunk par article
            for idx, match in enumerate(matches):
                art_num = match.group(1).strip()
                start   = match.start()
                end     = matches[idx + 1].start() if idx + 1 < len(matches) else len(full_text)
                content = full_text[start:end].strip()

                if not content or len(content) < 60:
                    continue

                if len(content) <= ARTICLE_MAX_CHARS:
                    chunk_defs.append((content, art_num, "article"))
                else:
                    # Gros article → sous-chunks avec overlap
                    for sub_idx, piece in enumerate(_split_article(content)):
                        chunk_defs.append((
                            piece,
                            f"{art_num}.{sub_idx}",
                            "article_fragment",
                        ))

        # ── Construire les Documents LangChain ────────────────────────────
        for chunk_index, (content, art_num, chunk_type) in enumerate(chunk_defs):
            seed     = f"{fname}:{art_num}:{chunk_index}:{content[:80]}"
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

            docs.append(Document(
                page_content=content,
                metadata={
                    "id":          chunk_id,   # utilisé par Neo4j comme Document.id
                    "chunk_id":    chunk_id,   # utilisé par Qdrant comme point id
                    "chunk_index": chunk_index,
                    "chunk_type":  chunk_type,
                    "article_num": art_num,
                    "source_file": fname,
                    "doc_type":    meta["type"],
                    "reference":   doc_ref,
                    "date":        meta.get("date", ""),
                    "jort":        meta.get("jort") or "",
                    "domaines":    ",".join(meta.get("domaines") or []),
                },
            ))

        loaded_files.add(fname)
        n_arts = sum(1 for _, _, t in chunk_defs if t == "article")
        n_frags = sum(1 for _, _, t in chunk_defs if t == "article_fragment")
        print(
            f"    → {len(pages)} pages | "
            f"{n_arts} articles | {n_frags} fragments | "
            f"{len(chunk_defs)} chunks total"
        )

    if target_files:
        for m in sorted(target_files - loaded_files):
            print(f"  [Avertissement] Fichier introuvable dans /Data : {m}")

    if not docs:
        raise ValueError("Aucun chunk généré. Vérifie les noms de fichiers et le dossier /Data.")

    return docs, doc_vu_refs


# ── ÉTAPE 2 : EXTRACTION DES ENTITÉS JURIDIQUES ──────────────────────────────

# Prompt resserré, orienté qualité plutôt que exhaustivité.
# Règles explicites pour éviter le bruit (boilerplate, numéros non-significatifs).
LEGAL_ENTITY_PROMPT = """
Tu es un juriste expert en droit tunisien chargé de construire un knowledge graph de conformité.
Le texte fourni est un ARTICLE ou un FRAGMENT D'ARTICLE de texte juridique.

RÈGLES STRICTES — à suivre impérativement :

1. PÉRIMÈTRE : extrait uniquement les entités et relations présentes dans la partie
   OPÉRATIONNELLE (le corps de l'article). Ignore tout ce qui ressemble à un préambule
   ("Vu le …", "Sur proposition de …", "Après délibération de …").

2. NŒUDS UTILES SEULEMENT :
   - Un nœud "Loi" ou "Decret" n'est créé que si le texte le MODIFIE ou en DÉPEND directement.
     Une simple citation en référence ne justifie pas un nœud.
   - Un nœud "Montant" ou "Delai" n'est créé que si la valeur est une limite légale
     actionnable (ex: "100.000 DT", "30 jours"). Ignore les numéros d'articles,
     les années, les numéros de page.
   - Un nœud "Organisme" n'est créé que s'il a un rôle actif dans la disposition.

3. DÉDUPLICATION : si la même entité apparaît plusieurs fois, crée UN SEUL nœud.

4. RELATIONS DIRECTES : évite les chaînes A→B→C quand A→C suffit.

5. PROPRIÉTÉS OBLIGATOIRES selon le type :
   - Article  : numero (ex: "14"), titre_court (≤ 5 mots), source (ex: "Circulaire BCT 2019-02")
   - Montant  : valeur (nombre seul), devise ("DT" ou "EUR"), contexte (usage de ce montant)
   - Delai    : duree (nombre seul), unite ("jours", "mois", "ans")
   - Avantage : description (phrase courte résumant le bénéfice)
   - Condition : description (critère précis et quantifié si possible)

Types de nœuds autorisés :
  Article, Loi, Decret, Circulaire, Organisme, Avantage, Obligation, Condition, Delai, Montant

Types de relations autorisés (SANS ACCENTS) :
  PREVOIT    — (Article/Loi/Decret) → (Avantage/Obligation)
  CONDITIONNE — (Condition) → (Avantage)
  CONCERNE   — (Article) → (Organisme)
  MODIFIE    — (Loi/Decret/Circulaire) → (Loi/Decret/Circulaire)
  APPLIQUE   — (Decret/Circulaire) → (Loi)
  DEPEND_DE  — (Avantage) → (Condition)
  FIXE       — (Article) → (Montant/Delai)
"""


def build_graph_from_docs(docs: list[Document], graph: Neo4jGraph) -> None:
    """
    Extraction entités + relations → Neo4j via LLMGraphTransformer.

    Seuls les chunks "article" et "article_fragment" sont envoyés au LLM.
    Les préambules sont exclus : ils ne contiennent que du boilerplate.
    Batch = 5 pour maximiser la précision (1 article ≈ 1 appel LLM).
    """
    llm = get_llm()

    transformer = LLMGraphTransformer(
        llm=llm,
        allowed_nodes=[
            "Article", "Loi", "Decret", "Circulaire",
            "Organisme", "Avantage", "Obligation",
            "Condition", "Delai", "Montant",
        ],
        allowed_relationships=[
            "PREVOIT", "CONDITIONNE", "CONCERNE",
            "MODIFIE", "APPLIQUE", "DEPEND_DE", "FIXE",
        ],
        node_properties=[
            "description", "valeur", "reference", "date",
            "numero", "titre_court", "source",
            "duree", "unite", "devise", "contexte",
        ],
        relationship_properties=["note"],
        additional_instructions=LEGAL_ENTITY_PROMPT,
    )

    # Filtrer : uniquement les chunks opérationnels
    operative = [
        d for d in docs
        if d.metadata.get("chunk_type") in ("article", "article_fragment", "paragraphe")
    ]
    excluded  = len(docs) - len(operative)
    print(
        f"\n  Extraction sur {len(operative)} chunks opérationnels "
        f"({excluded} préambules exclus)"
    )

    batch_size    = 5
    total_batches = max(1, (len(operative) - 1) // batch_size + 1)
    max_retries   = 3

    for i in range(0, len(operative), batch_size):
        batch     = operative[i: i + batch_size]
        batch_num = i // batch_size + 1
        success   = False

        for attempt in range(1, max_retries + 1):
            try:
                graph_docs = transformer.convert_to_graph_documents(batch)
                graph.add_graph_documents(
                    graph_docs,
                    baseEntityLabel=True,
                    include_source=True,
                )
                print(f"  Batch {batch_num}/{total_batches} ✓")
                success = True
                break
            except Exception as e:
                err = str(e)
                if "DeploymentNotFound" in err:
                    raise RuntimeError(
                        "Azure LLM introuvable (DeploymentNotFound). "
                        "Vérifiez la cohérence endpoint/modele dans .env: "
                        "AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_DEPLOYMENT (Azure OpenAI) "
                        "ou AZURE_API_BASE + model/AZURE_MODEL (Azure AI Foundry)."
                    ) from e
                if "429" in err:
                    wait = 2 ** attempt * 5  # 10s, 20s, 40s
                    print(
                        f"  Batch {batch_num} rate-limited "
                        f"(tentative {attempt}/{max_retries}), attente {wait}s..."
                    )
                    time.sleep(wait)
                else:
                    print(f"  Batch {batch_num} erreur : {e}")
                    break  # erreur non-récupérable → passer au batch suivant

        if not success:
            print(f"  Batch {batch_num} abandonné après {max_retries} tentatives.")

        time.sleep(2)  # throttle entre batches


# ── ÉTAPE 3 : LIENS NEXT ENTRE CHUNKS ────────────────────────────────────────

def add_chunk_links(docs: list[Document], graph: Neo4jGraph) -> None:
    """
    Crée des relations NEXT entre chunks consécutifs du même document.
    Permet au retriever de récupérer le contexte autour d'un résultat vectoriel
    sans ré-émettre un appel LLM.
    """
    print("\nCréation des liens NEXT entre chunks...")

    by_file: dict[str, list[Document]] = defaultdict(list)
    for doc in docs:
        by_file[doc.metadata["source_file"]].append(doc)

    total_links = 0
    for fname, file_docs in by_file.items():
        sorted_docs = sorted(file_docs, key=lambda d: d.metadata["chunk_index"])
        for prev_doc, next_doc in zip(sorted_docs, sorted_docs[1:]):
            try:
                graph.query(
                    """
                    MATCH (a:Document {id: $prev_id})
                    MATCH (b:Document {id: $next_id})
                    MERGE (a)-[:NEXT]->(b)
                    """,
                    params={
                        "prev_id": prev_doc.metadata["chunk_id"],
                        "next_id": next_doc.metadata["chunk_id"],
                    },
                )
                total_links += 1
            except Exception as e:
                print(f"  [warn] lien NEXT {fname} : {e}")

    print(f"  {total_links} liens NEXT créés ✓")


# ── ÉTAPE 4 : INDEX VECTORIEL QDRANT ─────────────────────────────────────────

def build_vector_index(
    docs: list[Document],
    pre_delete_collection: bool = True,
) -> None:
    """
    Indexe tous les chunks dans Qdrant.

    Payload stocké :
      - text         : texte complet (pas tronqué)
      - chunk_id     : lien vers le nœud Document Neo4j
      - article_num  : numéro de l'article source
      - chunk_type   : preambule | article | article_fragment | paragraphe
      - domaines     : tags métier pour le filtrage
    """
    embeddings  = get_ollama_embeddings()
    vector_size = len(embeddings.embed_query("probe"))
    batch_size  = 64

    print(f"\nConnexion à Qdrant (collection : {QDRANT_COLLECTION})...")
    client = get_qdrant_client()
    ensure_qdrant_collection(client, QDRANT_COLLECTION, vector_size, pre_delete_collection)

    total_batches = max(1, (len(docs) - 1) // batch_size + 1)
    print(f"Indexation de {len(docs)} chunks...")

    for i in range(0, len(docs), batch_size):
        batch     = docs[i: i + batch_size]
        batch_num = i // batch_size + 1

        vectors = embeddings.embed_documents([d.page_content for d in batch])
        points: list[models.PointStruct] = []

        for doc, vector in zip(batch, vectors):
            chunk_id = str(doc.metadata.get("chunk_id") or uuid.uuid4())
            points.append(models.PointStruct(
                id=chunk_id,
                vector=vector,
                payload={
                    "chunk_id":    chunk_id,
                    "source_file": doc.metadata.get("source_file", ""),
                    "reference":   doc.metadata.get("reference", ""),
                    "doc_type":    doc.metadata.get("doc_type", ""),
                    "chunk_type":  doc.metadata.get("chunk_type", ""),
                    "article_num": doc.metadata.get("article_num", ""),
                    "chunk_index": int(doc.metadata.get("chunk_index", 0) or 0),
                    "domaines":    doc.metadata.get("domaines", ""),
                    "date":        doc.metadata.get("date", ""),
                    # Texte COMPLET stocké — pas de troncature à 500 chars
                    "text":        doc.page_content,
                },
            ))

        client.upsert(collection_name=QDRANT_COLLECTION, points=points, wait=True)
        print(f"  Batch Qdrant {batch_num}/{total_batches} ✓")

    print("  Index vectoriel Qdrant ✓")


# ── ÉTAPE 5 : RELATIONS INTER-DOCUMENTS ──────────────────────────────────────

# Relations connues et vérifiées entre les textes du corpus Startup Act.
# Format : (référence_source, TYPE_RELATION, référence_cible, note)
_STATIC_RELATIONS: list[tuple[str, str, str, str]] = [
    (
        "Décret n° 2018-840",
        "APPLIQUE",
        "Loi n° 2018-20",
        "Art. 3,6,7,8,9,10,13 de la Loi 2018-20",
    ),
    (
        "Circulaire BCT n° 2019-01",
        "APPLIQUE",
        "Loi n° 2018-20",
        "Art. 17 — comptes devises startup",
    ),
    (
        "Circulaire BCT n° 2019-02",
        "APPLIQUE",
        "Loi n° 2018-20",
        "Carte Technologique Internationale",
    ),
    (
        "Circulaire BCT n° 2019-01",
        "REFERENCE",
        "Décret n° 2018-840",
        "",
    ),
    (
        "Circulaire BCT n° 2019-02",
        "REFERENCE",
        "Décret n° 2018-840",
        "",
    ),
]

# Map numéro court → (label Neo4j, référence complète)
# Utilisé pour résoudre les références extraites dynamiquement des "Vu …".
_KNOWN_REFS: dict[str, tuple[str, str]] = {
    "2018-20":  ("Loi",        "Loi n° 2018-20"),
    "840-2018": ("Decret",     "Décret n° 2018-840"),
    "2018-840": ("Decret",     "Décret n° 2018-840"),
    "2019-01":  ("Circulaire", "Circulaire BCT n° 2019-01"),
    "2019-02":  ("Circulaire", "Circulaire BCT n° 2019-02"),
    "2016-35":  ("Loi",        "Loi n° 2016-35"),
}

_DOC_LABEL_BY_TYPE: dict[str, str] = {
    "loi": "Loi",
    "decret": "Decret",
    "circulaire_BCT": "Circulaire",
    "code": "Code",
    "rapport": "Rapport",
}

# Référence canonique -> label Neo4j canonique
_REFERENCE_LABELS: dict[str, str] = {
    meta["reference"]: _DOC_LABEL_BY_TYPE.get(meta.get("type", ""), "Document")
    for meta in PDF_META.values()
}

for _, (lbl, full_ref) in _KNOWN_REFS.items():
    _REFERENCE_LABELS.setdefault(full_ref, lbl)


def _label_for_reference(reference: str) -> str:
    return _REFERENCE_LABELS.get(reference, "Document")


def add_inter_doc_relations(
    graph: Neo4jGraph,
    doc_vu_refs: dict[str, list[str]],
) -> None:
    """
    Construit les relations entre documents dans Neo4j :
      1. Relations statiques vérifiées (corpus Startup Act)
      2. Relations dynamiques extraites des clauses "Vu …" de chaque document
    """
    print("\nRelations inter-documents...")

    # 1. Statiques
    for src_ref, rel_type, tgt_ref, note in _STATIC_RELATIONS:
        src_label = _label_for_reference(src_ref)
        tgt_label = _label_for_reference(tgt_ref)
        try:
            graph.query(
                f"""
                MERGE (src:{src_label} {{reference: $src}})
                MERGE (tgt:{tgt_label} {{reference: $tgt}})
                MERGE (src)-[:{rel_type} {{note: $note}}]->(tgt)
                """,
                params={"src": src_ref, "tgt": tgt_ref, "note": note},
            )
        except Exception as e:
            print(f"  [warn] relation statique {src_ref} → {tgt_ref} : {e}")

    # 2. Dynamiques (depuis "Vu …")
    dynamic_count = 0
    for citing_ref, cited_numbers in doc_vu_refs.items():
        src_label = _label_for_reference(citing_ref)
        for num in cited_numbers:
            if num not in _KNOWN_REFS:
                continue  # référence inconnue, on ignore
            tgt_label, cited_full_ref = _KNOWN_REFS[num]
            if cited_full_ref == citing_ref:
                continue  # pas d'auto-référence
            try:
                graph.query(
                    f"""
                    MERGE (src:{src_label} {{reference: $citing}})
                    MERGE (tgt:{tgt_label} {{reference: $cited}})
                    MERGE (src)-[:REFERENCE {{note: 'extrait_preambule'}}]->(tgt)
                    """,
                    params={"citing": citing_ref, "cited": cited_full_ref},
                )
                dynamic_count += 1
            except Exception as e:
                print(f"  [warn] relation dynamique {citing_ref} → {cited_full_ref} : {e}")

    print(
        f"  {len(_STATIC_RELATIONS)} statiques + {dynamic_count} dynamiques créées ✓"
    )


# ── UTILS CLI ─────────────────────────────────────────────────────────────────

def parse_target_files(cli_args: list[str]) -> set[str] | None:
    """
    Construit la liste des PDFs ciblés depuis :
      1. Arguments CLI : python ingest.py file1.pdf file2.pdf
      2. Variable .env : INGEST_ONLY_FILES=file1.pdf,file2.pdf
    Retourne None si aucun ciblage → tous les PDFs seront traités.
    """
    selected: set[str] = set()
    env_value = os.getenv("INGEST_ONLY_FILES", "").strip()
    if env_value:
        selected.update(p.strip() for p in env_value.split(",") if p.strip())
    if cli_args:
        selected.update(Path(a).name for a in cli_args if a.strip())
    return selected or None


# ── PIPELINE PRINCIPAL ────────────────────────────────────────────────────────

def run_ingestion() -> None:
    print("=" * 60)
    print("ComplianceGuard — Pipeline d'ingestion GraphRAG v2")
    print("=" * 60)

    graph = get_graph()

    # ── 0. Schéma Neo4j ───────────────────────────────────────────
    print("\n[0/5] Initialisation Neo4j...")
    init_neo4j(graph)

    # ── Sélection des fichiers ────────────────────────────────────
    target_files = parse_target_files(sys.argv[1:])
    if target_files:
        print("\nMode ingestion ciblée :")
        for n in sorted(target_files):
            print(f"  - {n}")

    # ── 1. Chargement + chunking article-aware ────────────────────
    print("\n[1/5] Chargement et chunking article-aware...")
    docs, doc_vu_refs = load_pdfs(target_files=target_files)
    by_type: dict[str, int] = defaultdict(int)
    for d in docs:
        by_type[d.metadata["chunk_type"]] += 1
    print(f"  Total : {len(docs)} chunks")
    for ctype, count in sorted(by_type.items()):
        print(f"    {ctype:<20} : {count}")

    # ── 2. Extraction entités → Neo4j ─────────────────────────────
    print("\n[2/5] Extraction des entités juridiques → Neo4j...")
    build_graph_from_docs(docs, graph)

    # ── 3. Liens NEXT entre chunks ────────────────────────────────
    print("\n[3/5] Liens de séquence (NEXT) dans Neo4j...")
    add_chunk_links(docs, graph)

    # ── 4. Index vectoriel Qdrant ─────────────────────────────────
    print("\n[4/5] Index vectoriel Qdrant...")
    pre_delete_env = os.getenv("VECTOR_PRE_DELETE_COLLECTION", "").strip().lower()
    if pre_delete_env:
        pre_delete = pre_delete_env in {"1", "true", "yes", "y", "on"}
    else:
        pre_delete = target_files is None  # plein rechargement = recréer, mode ciblé = conserver
    if not pre_delete:
        print("  Mode incrémental : collection Qdrant existante conservée.")
    build_vector_index(docs, pre_delete_collection=pre_delete)

    # ── 5. Relations inter-documents ──────────────────────────────
    print("\n[5/5] Relations inter-documents...")
    add_inter_doc_relations(graph, doc_vu_refs)

    # ── Résumé ────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Ingestion terminée avec succès !")
    print(f"  Chunks générés  : {len(docs)}")
    print(f"  Neo4j           : graphe peuplé + liens NEXT + relations inter-docs")
    print(f"  Qdrant          : collection '{QDRANT_COLLECTION}' indexée")
    print("=" * 60)


if __name__ == "__main__":
    run_ingestion()
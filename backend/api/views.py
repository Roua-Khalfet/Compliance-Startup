"""
API Views for ComplianceGuard - Django REST Framework.

Endpoints:
- POST /api/chat/ - Chat avec l'agent GraphRAG
- POST /api/conformite/ - Analyse de conformité avec scoring
- POST /api/documents/ - Génération de documents
- GET /api/graph/ - Données du graphe Neo4j
- GET /api/veille/ - État de la veille web
- POST /api/suggestions/ - Questions suggérées
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .serializers import (
    ChatRequestSerializer,
    ConformiteRequestSerializer,
    DocumentRequestSerializer,
    SuggestionsRequestSerializer,
)

# Add complianceguard to path and load .env
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Force load .env from project root
load_dotenv(PROJECT_ROOT / ".env", override=True)

# ============================================================================
# Import agents (lazy loading to avoid startup errors)
# ============================================================================

def get_answer_function():
    """Lazy import of answer_question."""
    try:
        from complianceguard.ask_question import answer_question, _is_greeting_or_non_question
        return answer_question, _is_greeting_or_non_question
    except Exception as e:
        import traceback
        print(f"ERROR importing ask_question: {e}")
        traceback.print_exc()
        return None, None

def get_redacteur():
    """Lazy import of AgentRedacteur."""
    try:
        from complianceguard.agent_redacteur import AgentRedacteur, ProjectInfo
        return AgentRedacteur, ProjectInfo
    except Exception as e:
        print(f"Warning: Could not import agent_redacteur: {e}")
        return None, None

# ============================================================================
# Conformité Scoring Logic
# ============================================================================

CONFORMITE_CRITERES = [
    {
        "id": "capital",
        "label": "Capital social constitué",
        "article": "Art. 92-100",
        "article_source": "Code des Sociétés Commerciales",
        "thresholds": {"SUARL": 1000, "SARL": 1000, "SA": 5000}
    },
    {
        "id": "label_startup",
        "label": "Éligibilité label Startup",
        "article": "Art. 3",
        "article_source": "Loi n° 2018-20 (Startup Act)",
    },
    {
        "id": "protection_donnees",
        "label": "Protection des données",
        "article": "Art. 7-12",
        "article_source": "Loi organique n° 2004-63",
    },
    {
        "id": "autorisation_bct",
        "label": "Autorisation BCT",
        "article": "Art. 34",
        "article_source": "Loi n° 2016-48 + Circulaire BCT",
    },
    {
        "id": "cgv_cgu",
        "label": "Mentions légales CGU/CGV",
        "article": "Art. 15",
        "article_source": "Loi n° 2000-83 (commerce électronique)",
    }
]

def analyze_conformite(data):
    """Analyse la conformité et retourne un score par critère."""
    criteres_results = []
    total_score = 0
    
    project_description = data.get("project_description", "")
    sector = data.get("sector", "")
    capital = data.get("capital")
    type_societe = data.get("type_societe", "SUARL")
    
    for critere in CONFORMITE_CRITERES:
        score = 0
        status_val = "x"
        details = ""
        
        if critere["id"] == "capital":
            threshold = critere["thresholds"].get(type_societe, 1000)
            if capital and capital >= threshold:
                score = 100
                status_val = "check"
                details = f"Capital de {capital} TND ≥ {threshold} TND requis"
            elif capital:
                score = int((capital / threshold) * 100)
                status_val = "warning" if score > 50 else "x"
                details = f"Capital de {capital} TND < {threshold} TND requis"
            else:
                score = 50
                status_val = "warning"
                details = "Capital non spécifié"
        
        elif critere["id"] == "label_startup":
            desc_lower = project_description.lower()
            innovation_keywords = ["innovant", "technologie", "ia", "intelligence artificielle", 
                                   "blockchain", "saas", "plateforme", "app", "mobile", "digital"]
            matches = sum(1 for kw in innovation_keywords if kw in desc_lower)
            score = min(100, matches * 20 + 40)
            status_val = "check" if score >= 70 else "warning" if score >= 40 else "x"
            details = f"Potentiel d'innovation: {matches} indicateurs détectés"
        
        elif critere["id"] == "protection_donnees":
            high_risk_sectors = ["Fintech", "HealthTech", "EdTech"]
            if sector in high_risk_sectors:
                score = 45
                status_val = "warning"
                details = f"Secteur {sector}: déclaration INPDP obligatoire"
            else:
                score = 70
                status_val = "check"
                details = "Obligations standard de protection des données"
        
        elif critere["id"] == "autorisation_bct":
            if sector == "Fintech" or "paiement" in project_description.lower():
                score = 30
                status_val = "x"
                details = "Agrément BCT obligatoire pour activité de paiement"
            else:
                score = 100
                status_val = "check"
                details = "Pas d'autorisation BCT requise"
        
        elif critere["id"] == "cgv_cgu":
            score = 75
            status_val = "warning"
            details = "CGU/CGV à rédiger selon les mentions obligatoires"
        
        criteres_results.append({
            "label": critere["label"],
            "score": score,
            "status": status_val,
            "article": critere["article"],
            "article_source": critere["article_source"],
            "details": details
        })
        total_score += score
    
    score_global = total_score // len(CONFORMITE_CRITERES)
    
    if score_global >= 80:
        status_global = "conforme"
    elif score_global >= 50:
        status_global = "conforme_reserves"
    else:
        status_global = "non_conforme"
    
    return {
        "score_global": score_global,
        "status": status_global,
        "criteres": criteres_results
    }

# ============================================================================
# Suggestions Logic
# ============================================================================

SUGGESTION_TEMPLATES = {
    "Fintech": [
        "Ai-je besoin d'une autorisation BCT pour mon activité ?",
        "Quel capital minimum pour un établissement de paiement ?",
        "Quelles sont les obligations de lutte anti-blanchiment ?",
        "Comment obtenir l'agrément d'établissement de paiement ?",
    ],
    "EdTech": [
        "Quelles autorisations pour une plateforme éducative en ligne ?",
        "Protection des données des mineurs : quelles obligations ?",
        "Agrément du Ministère de l'Éducation nécessaire ?",
        "Certification des contenus pédagogiques requise ?",
    ],
    "HealthTech": [
        "Réglementation des dispositifs médicaux connectés ?",
        "Hébergement des données de santé : quelles contraintes ?",
        "Autorisation du Ministère de la Santé nécessaire ?",
        "Responsabilité médicale et applications de santé ?",
    ],
    "E-commerce": [
        "Mentions légales obligatoires pour un site e-commerce ?",
        "Droit de rétractation : quelles obligations ?",
        "TVA et facturation électronique en Tunisie ?",
        "Protection du consommateur : clauses interdites ?",
    ],
    "SaaS": [
        "Clauses essentielles d'un contrat SaaS ?",
        "Responsabilité en cas d'interruption de service ?",
        "Propriété intellectuelle du code développé ?",
        "Transfert de données hors Tunisie : conditions ?",
    ],
    "default": [
        "Quels avantages du Startup Act puis-je obtenir ?",
        "Comment obtenir le label Startup ?",
        "Quel type de société pour ma startup ?",
        "Quelles obligations fiscales pour une startup ?",
    ]
}

def generate_suggestions(project_description, sector):
    """Génère des questions suggérées basées sur le contexte."""
    sector_suggestions = SUGGESTION_TEMPLATES.get(sector, SUGGESTION_TEMPLATES["default"])
    
    desc_lower = project_description.lower()
    contextual = []
    
    if "paiement" in desc_lower or "payment" in desc_lower:
        contextual.append("Réglementation des services de paiement en Tunisie ?")
    if "données" in desc_lower or "data" in desc_lower:
        contextual.append("Obligations INPDP pour le traitement de données ?")
    if "international" in desc_lower or "export" in desc_lower:
        contextual.append("Compte en devises pour startup : conditions ?")
    if "investissement" in desc_lower or "levée" in desc_lower:
        contextual.append("Avantages fiscaux pour les investisseurs (Startup Act) ?")
    
    all_suggestions = contextual + sector_suggestions
    return all_suggestions[:6]

# ============================================================================
# API Views
# ============================================================================

@api_view(["GET"])
def api_root(request):
    """API root endpoint."""
    return Response({
        "message": "ComplianceGuard API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/chat/",
            "conformite": "/api/conformite/",
            "documents": "/api/documents/",
            "graph": "/api/graph/",
            "veille": "/api/veille/",
            "suggestions": "/api/suggestions/",
        }
    })

@api_view(["POST"])
def chat(request):
    """Chat avec l'agent GraphRAG."""
    serializer = ChatRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    message = data["message"]
    project_context = data.get("project_context", "")
    
    answer_question, is_greeting = get_answer_function()
    
    if answer_question is None:
        # Fallback response if agents not available
        return Response({
            "response": "L'agent GraphRAG n'est pas disponible. Vérifiez que les dépendances sont installées.",
            "sources": [],
            "source_type": "error"
        })
    
    # Check for greetings
    if is_greeting and is_greeting(message):
        return Response({
            "response": (
                "Bonjour ! Je suis l'assistant juridique ComplianceGuard, "
                "spécialisé dans le Startup Act tunisien.\n\n"
                "Posez-moi une question juridique, par exemple :\n"
                "- Quels documents pour obtenir le label startup ?\n"
                "- Quels sont les avantages fiscaux du Startup Act ?\n"
                "- Comment obtenir le congé startup ?"
            ),
            "sources": [],
            "source_type": "system"
        })
    
    # Enrich question with context
    enriched_question = message
    if project_context:
        enriched_question = f"Contexte projet: {project_context}\n\nQuestion: {message}"
    
    try:
        answer, sources = answer_question(enriched_question, max_docs=8, enable_web_fallback=True)
        
        source_type = "Web" if "[Source: Recherche Web]" in answer else "GraphRAG"
        answer = answer.replace("\n\n[Source: Recherche Web]", "")
        
        return Response({
            "response": answer,
            "sources": sources,
            "source_type": source_type
        })
    except Exception as e:
        # Fallback: return a helpful message when Qdrant/Neo4j not available
        error_msg = str(e)
        if "compliance_vectors" in error_msg or "Qdrant" in error_msg:
            return Response({
                "response": (
                    "⚠️ **Base de données non initialisée**\n\n"
                    "La collection Qdrant n'existe pas encore. "
                    "Exécutez d'abord l'ingestion des documents :\n\n"
                    "```bash\ncd complianceguard && python ingest.py\n```\n\n"
                    "Cela va indexer les PDFs du dossier `Data/` dans Neo4j et Qdrant."
                ),
                "sources": [],
                "source_type": "error"
            })
        return Response({
            "response": f"Erreur: {error_msg}",
            "sources": [],
            "source_type": "error"
        })

@api_view(["POST"])
def conformite(request):
    """Analyse de conformité avec scoring."""
    serializer = ConformiteRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    result = analyze_conformite(serializer.validated_data)
    return Response(result)

@api_view(["POST"])
def generate_documents(request):
    """Génère des documents juridiques."""
    serializer = DocumentRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    AgentRedacteur, ProjectInfo = get_redacteur()
    
    if AgentRedacteur is None:
        return Response({
            "error": "Agent Rédacteur non disponible"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    try:
        agent = AgentRedacteur()
        project = ProjectInfo(
            nom_startup=data["nom_startup"],
            activite=data["activite"],
            fondateurs=data.get("fondateurs", []),
            capital_social=data.get("capital_social", 1000),
            siege_social=data.get("siege_social", "Tunis"),
            type_societe=data.get("type_societe", "SUARL"),
        )
        
        results = []
        
        if data["doc_type"] == "all":
            docs = agent.generer_pack_complet(project)
            for doc_type, content in docs.items():
                results.append({
                    "doc_type": doc_type,
                    "content": content,
                    "filename": f"{data['nom_startup']}_{doc_type}.md"
                })
        else:
            content = agent.generer_document(data["doc_type"], project)
            results.append({
                "doc_type": data["doc_type"],
                "content": content,
                "filename": f"{data['nom_startup']}_{data['doc_type']}.md"
            })
        
        return Response(results)
    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def get_graph(request):
    """Récupère les données du graphe Neo4j."""
    # Default graph data (real implementation would query Neo4j)
    default_graph = {
        "nodes": [
            {"id": "loi_2018_20", "label": "Loi 2018-20 (Startup Act)", "type": "loi", "properties": {"titre": "Startup Act"}},
            {"id": "art_3", "label": "Article 3 - Conditions", "type": "article", "properties": {"sujet": "Conditions label"}},
            {"id": "art_13", "label": "Article 13 - Avantages fiscaux", "type": "article", "properties": {"sujet": "Avantages fiscaux"}},
            {"id": "art_20", "label": "Article 20 - Congé startup", "type": "article", "properties": {"sujet": "Congé création"}},
            {"id": "decret_840", "label": "Décret 2018-840", "type": "loi", "properties": {"titre": "Application"}},
            {"id": "bct_2019_01", "label": "Circulaire BCT 2019-01", "type": "loi", "properties": {"titre": "Devises"}},
            {"id": "startup", "label": "Startup", "type": "entite", "properties": {}},
            {"id": "investisseur", "label": "Investisseur", "type": "entite", "properties": {}},
            {"id": "label", "label": "Label Startup", "type": "concept", "properties": {}},
        ],
        "edges": [
            {"source": "loi_2018_20", "target": "art_3", "relation": "CONTIENT"},
            {"source": "loi_2018_20", "target": "art_13", "relation": "CONTIENT"},
            {"source": "loi_2018_20", "target": "art_20", "relation": "CONTIENT"},
            {"source": "decret_840", "target": "loi_2018_20", "relation": "APPLIQUE"},
            {"source": "bct_2019_01", "target": "loi_2018_20", "relation": "REFERENCE"},
            {"source": "art_3", "target": "startup", "relation": "DEFINIT"},
            {"source": "art_3", "target": "label", "relation": "ETABLIT"},
            {"source": "art_13", "target": "investisseur", "relation": "CONCERNE"},
            {"source": "art_20", "target": "startup", "relation": "BENEFICIE"},
        ]
    }
    
    try:
        from complianceguard.tools.retriever import get_graph as get_neo4j_graph
        graph = get_neo4j_graph()
        
        query = """
        MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT 50
        """
        result = graph.query(query)
        
        nodes = []
        edges = []
        seen_nodes = set()
        
        for record in result:
            n = record.get("n", {})
            m = record.get("m", {})
            r = record.get("r", {})
            
            for node in [n, m]:
                if node and hasattr(node, "element_id"):
                    node_id = str(node.element_id)
                    if node_id not in seen_nodes:
                        seen_nodes.add(node_id)
                        labels = list(node.labels) if hasattr(node, "labels") else ["Unknown"]
                        nodes.append({
                            "id": node_id,
                            "label": dict(node).get("name", dict(node).get("titre", node_id[:20])),
                            "type": labels[0].lower() if labels else "unknown",
                            "properties": dict(node)
                        })
            
            if r and hasattr(r, "type"):
                edges.append({
                    "source": str(r.start_node.element_id),
                    "target": str(r.end_node.element_id),
                    "relation": r.type
                })
        
        if nodes:
            return Response({"nodes": nodes, "edges": edges})
    except Exception as e:
        print(f"Error fetching graph: {e}")
    
    return Response(default_graph)

@api_view(["GET"])
def get_veille(request):
    """Récupère l'état de la veille web."""
    now = datetime.now().isoformat()
    
    # Try to get real veille status
    try:
        from complianceguard.agent_veille import load_cache, SITES_TO_MONITOR
        cache = load_cache()
        
        items = []
        for site in SITES_TO_MONITOR:
            page_info = cache.pages.get(site["url"])
            if page_info:
                items.append({
                    "url": site["url"],
                    "nom": site["name"],
                    "last_check": page_info.timestamp,
                    "has_changed": False,
                    "status": "ok"
                })
            else:
                items.append({
                    "url": site["url"],
                    "nom": site["name"],
                    "last_check": now,
                    "has_changed": False,
                    "status": "pending"
                })
        
        return Response({
            "items": items,
            "last_update": cache.last_update or now
        })
    except Exception:
        pass
    
    # Default response
    return Response({
        "items": [
            {"url": "https://startup.gov.tn", "nom": "Portail Startup", "last_check": now, "has_changed": False, "status": "ok"},
            {"url": "https://www.bct.gov.tn", "nom": "BCT - Circulaires", "last_check": now, "has_changed": False, "status": "ok"},
            {"url": "https://www.apii.tn", "nom": "APII", "last_check": now, "has_changed": False, "status": "ok"},
        ],
        "last_update": now
    })

@api_view(["POST"])
def get_suggestions(request):
    """Génère des questions suggérées."""
    serializer = SuggestionsRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    questions = generate_suggestions(
        data["project_description"],
        data["sector"]
    )
    
    return Response({"questions": questions})

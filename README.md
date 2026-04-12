# ComplianceGuard 🛡️

**Assistant juridique intelligent pour les startups en Tunisie** — Système multi-agents basé sur GraphRAG, CRAG, et LangChain avec interface web complète.

---

## 📋 Description

ComplianceGuard est une plateforme d'IA qui aide les entrepreneurs tunisiens à naviguer dans le cadre réglementaire du **Startup Act** et des lois connexes. Le système combine cinq agents spécialisés autour d'une architecture hybride :

- **Vector DB** (Qdrant) — Recherche sémantique par similarité sur les chunks de texte juridique
- **Knowledge Graph** (Neo4j) — Graphe de relations entre lois, articles, organismes et obligations
- **CRAG** (Corrective RAG) — Pipeline avancé d'évaluation et de raffinement des documents récupérés
- **Agent Web** — Fallback automatique vers la recherche Google + scraping quand la base locale est insuffisante
- **Agent Rédacteur** — Génération de documents juridiques (statuts, CGU, contrats, demande de label)
- **Agent Veille** — Surveillance des changements réglementaires sur les sites officiels tunisiens
- **Frontend Next.js** + **Backend Django REST** — Interface complète avec 6 sections intégrées

---

## 🏗️ Architecture Globale

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            ComplianceGuard                                      │
├──────────────────────────────┬──────────────────────────────────────────────────┤
│      FRONTEND (Next.js)      │              BACKEND (Django REST)               │
│                              │                                                  │
│  ┌────────────────────────┐  │  ┌──────────────────────────────────────────┐    │
│  │ 💬 Chat Juridique      │  │  │  POST /api/chat/     → GraphRAG / CRAG  │    │
│  │ (GraphRAG + CRAG +     │──┼──│  POST /api/upload/   → fast_ingest_file │    │
│  │  Upload PDF)           │  │  │  POST /api/conformite/ → Scoring Engine │    │
│  ├────────────────────────┤  │  │  POST /api/documents/  → AgentRédacteur │    │
│  │ 📝 Documents           │──┼──│  GET  /api/graph/     → Neo4j Visualize │    │
│  │ (Statuts, CGU, Contrat)│  │  │  GET  /api/veille/    → AgentVeille     │    │
│  ├────────────────────────┤  │  │  POST /api/suggestions/ → Smart Suggest │    │
│  │ ✅ Conformité          │──┼──└──────────────┬───────────────────────────┘    │
│  │ (Scoring par critère)  │  │                 │                                │
│  ├────────────────────────┤  │                 │                                │
│  │ 🧠 Quiz Conformité     │  │                 │                                │
│  │ (Auto-évaluation)      │  │                 │                                │
│  ├────────────────────────┤  │                 │                                │
│  │ 📡 Veille              │──┼─────────────────┘                                │
│  │ (Surveillance sites)   │  │                                                  │
│  ├────────────────────────┤  │                                                  │
│  │ 🔗 Graphe de Lois      │──┼──────────────────                                │
│  │ (Visualisation Neo4j)  │  │                                                  │
│  └────────────────────────┘  │                                                  │
│         SIDEBAR NAV          │                                                  │
├──────────────────────────────┴──────────────────────────────────────────────────┤
│                          CORE ENGINE                                            │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         ask_question.py (Mode KB)                       │   │
│  │                                                                         │   │
│  │   Question ──► HybridRetriever ──► Contexte suffisant ?                 │   │
│  │                   │        │              │          │                   │   │
│  │              Qdrant    Neo4j           OUI         NON                  │   │
│  │             (Vector)  (Graph)           │           │                   │   │
│  │                                         │    Web Fallback               │   │
│  │                                         │    (Serper + Scraping)        │   │
│  │                                         │           │                   │   │
│  │                                         └─────┬─────┘                   │   │
│  │                                               │                         │   │
│  │                                          LLM (Groq / Azure)             │   │
│  │                                               │                         │   │
│  │                                           Réponse                       │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         crag.py (Mode Notebook / CRAG)                  │   │
│  │                                                                         │   │
│  │   Question ──► Retrieve ──► Grade Documents ──► Decide Action           │   │
│  │                                │                     │                  │   │
│  │                         Score [-1, 1]          ┌─────┼─────┐            │   │
│  │                         par document          use  combine web_search   │   │
│  │                                                │     │      │           │   │
│  │                                         Refine Docs  │  Rewrite Query   │   │
│  │                                         (Strips)     │  + Web Search    │   │
│  │                                                │     │      │           │   │
│  │                                                └─────┼──────┘           │   │
│  │                                                      │                  │   │
│  │                                                 LLM Answer              │   │
│  │                                                 + Metadata              │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                     Retriever Hybride (retriever.py)                    │   │
│  │                                                                         │   │
│  │   ┌─────────────────┐    ┌──────────────────────┐    ┌──────────────┐   │   │
│  │   │   Qdrant        │    │   Neo4j               │    │   Ollama     │   │   │
│  │   │  (Vectors)      │    │  (Knowledge Graph)    │    │  Embeddings  │   │   │
│  │   │                 │    │                        │    │  qwen3-emb   │   │   │
│  │   │ • corpus chunks │    │ • Fulltext index       │    │  :0.6b       │   │   │
│  │   │ • user uploads  │    │ • Relation traversal   │    │              │   │   │
│  │   └────────┬────────┘    │ • Path extraction      │    └──────┬───────┘   │   │
│  │            │             │ • Rel summary          │           │           │   │
│  │            │             └───────────┬────────────┘           │           │   │
│  │            └─────────────────────────┼───────────────────────┘           │   │
│  │                                      │                                   │   │
│  │                           Deduplicate + Merge                            │   │
│  │                                      │                                   │   │
│  │                              List[Document]                              │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────┐  ┌────────────────────┐  ┌────────────────────────────┐   │
│  │  Agent Rédacteur │  │  Agent Veille Web  │  │ Agent Web (chain.py)      │   │
│  │  (Docs juridiques│  │  (Surveillance     │  │ (Recherche + Scraping     │   │
│  │   statuts, CGU,  │  │   réglementaire,   │  │  LangChain bind_tools)   │   │
│  │   contrats...)   │  │   hash comparison) │  │                           │   │
│  └──────────────────┘  └────────────────────┘  └────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🖥️ Interface Web — 6 Sections Intégrées

L'interface est construite avec une **sidebar de navigation** colorée et 6 sections complètes :

| Section | Description | Backend |
|---------|-------------|---------|
| 💬 **Chat Juridique** | Chat avec GraphRAG (base juridique) ou CRAG (documents uploadés). Toggle kb/notebook, upload PDF intégré, questions suggérées | `POST /api/chat/` + `POST /api/upload/` |
| 📝 **Documents** | Génération de statuts, CGU, contrats d'investissement, demande de label. Formulaire complet + preview + téléchargement | `POST /api/documents/` |
| ✅ **Conformité** | Analyse de conformité avec scoring pondéré. Choix du secteur, jauge animée, critères détaillés avec articles de loi | `POST /api/conformite/` |
| 🧠 **Quiz Conformité** | Auto-évaluation : 10 questions aléatoires sur la conformité de VOTRE société. Score pondéré par domaine + recommandations | Client-side (22 questions, 9 catégories) |
| 📡 **Veille** | Surveillance des sites officiels (startup.gov.tn, BCT, APII). Statut OK/changé, date du dernier check | `GET /api/veille/` |
| 🔗 **Graphe de Lois** | Visualisation des nœuds Neo4j (lois, articles, entités) avec relations colorées, sélection interactive, zoom | `GET /api/graph/` |

---

## 📁 Structure Complète du Projet

```
AI project/
│
├── complianceguard/                 # ⚙️ Core Engine (Python)
│   ├── __init__.py
│   ├── config.py                    # Configuration centralisée (Pydantic Settings)
│   ├── ask_question.py              # Agent GraphRAG — Q&A sur base juridique + web fallback
│   ├── crag.py                      # Pipeline CRAG — Grade, Refine, Rewrite, Answer
│   ├── chain.py                     # Agent Web LangChain avec bind_tools (Serper + Scraping)
│   ├── main.py                      # Point d'entrée CLI de l'Agent Web
│   ├── ingest.py                    # Ingestion PDFs → Neo4j (GraphRAG) + Qdrant (Vectors)
│   ├── document_utils.py            # Conversion documents (Unstructured/pypdf) + chunking sémantique
│   ├── agent_redacteur.py           # Agent de rédaction de documents juridiques
│   ├── agent_veille.py              # Agent de surveillance réglementaire (scraping + hash)
│   ├── config/
│   │   ├── agents.yaml              # Définition du rôle de l'agent de conformité
│   │   └── tasks.yaml               # Définition des tâches de recherche
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── retriever.py             # HybridRetriever (Qdrant + Neo4j + Ollama)
│   │   ├── graph_agent.py           # LangChain Tools : RAG chain, Graph QA, Compliance Check
│   │   └── custom_tool.py           # Template d'outil personnalisé
│   └── tests/
│       ├── __init__.py
│       └── graphrag_suite.py        # Suite de tests GraphRAG
│
├── backend/                          # 🖥️ API REST (Django)
│   ├── manage.py
│   ├── config/
│   │   ├── settings.py               # Django settings (CORS, REST Framework)
│   │   ├── urls.py                    # URL routing principal
│   └── api/
│       ├── urls.py                    # Routes : /chat, /upload, /conformite, /documents, /graph, /veille
│       ├── serializers.py             # Serializers DRF
│       └── views.py                   # Vues API + Moteur de scoring conformité
│
├── frontend/                         # 🎨 Interface Web (Next.js 16 + TailwindCSS 4)
│   ├── package.json                  # React 19, Radix UI, Recharts, Lucide
│   ├── app/
│   │   ├── layout.tsx                # Layout principal avec ThemeProvider
│   │   ├── page.tsx                  # Page racine : Sidebar + Section routing
│   │   └── globals.css               # Design system (gradients, glassmorphism, animations)
│   ├── components/
│   │   ├── app-sidebar.tsx           # ★ Sidebar navigation avec 6 sections colorées
│   │   ├── chat-section.tsx          # ★ Chat GraphRAG + CRAG + Upload PDF
│   │   ├── documents-section.tsx     # ★ Générateur de documents juridiques
│   │   ├── conformite-section.tsx    # ★ Analyse de conformité avec scoring
│   │   ├── quiz-section.tsx          # ★ Quiz auto-évaluation conformité (22 questions)
│   │   ├── veille-section.tsx        # ★ Veille réglementaire
│   │   ├── graph-section.tsx         # ★ Visualisation Knowledge Graph
│   │   └── ui/                       # Composants ShadCN/UI (57 composants)
│   └── lib/
│       ├── api.ts                    # Client HTTP complet (7 fonctions API)
│       └── utils.ts                  # Utilitaires (cn helper)
│
├── Data/                             # 📚 Documents juridiques sources (12 PDFs)
│   ├── Loi_2018_20_FR.pdf            # Startup Act
│   ├── Decret_2018_840_Startup.pdf   # Décret d'application
│   ├── Circulaire_2019_01_FR.pdf     # Circulaire BCT (comptes devises)
│   ├── Circulaire_2019_02_FR.pdf     # Circulaire BCT (carte technologique)
│   ├── Code_Societes_Commerciales_FR.pdf
│   ├── Code_Droits_Procedures_Fiscaux_2023.pdf
│   ├── Code_Travail_FR.pdf
│   ├── Loi_63-2004_FR.pdf            # Protection données personnelles
│   ├── Loi_2000-83_FR.pdf            # Commerce électronique
│   ├── Loi_2016_71_FR.pdf            # Investissement
│   └── Rapport_IC_Startup_Acts_FR.pdf
│
├── chunks/                           # 📄 Chunks pré-générés (12 fichiers .md)
│
├── scripts/                          # 🔧 Scripts d'infrastructure
│   ├── start-local-stack.ps1         # Lance Neo4j + Qdrant en Docker
│   ├── check-local-stack.ps1         # Vérifie l'état des conteneurs
│   └── use-local-env.ps1             # Configure les variables pour le stack local
│
├── .env                              # Variables d'environnement (non versionné)
├── .gitignore
├── requirements.txt
└── README.md                         # ← Ce fichier
```

---

## 🤖 Les 5 Agents du Système

### 1. Agent GraphRAG (`ask_question.py`)

**Rôle :** Répond aux questions juridiques en combinant recherche vectorielle et traversée du knowledge graph.

**Pipeline :**
1. Détection des salutations / non-questions
2. Recherche hybride via `HybridRetriever` (Qdrant + Neo4j)
3. Construction du contexte avec troncature intelligente (head+tail)
4. Si contexte insuffisant → **Web Fallback** automatique (Serper + WebBaseLoader)
5. Génération de la réponse via LLM (Groq ou Azure)
6. Post-traitement : nettoyage des noms de fichiers, expansion des références juridiques

---

### 2. Pipeline CRAG (`crag.py`)

**Rôle :** Pipeline Corrective RAG avancé pour l'analyse de documents uploadés par l'utilisateur.

| Étape | Description |
|-------|-------------|
| **1. Retrieve** | Récupère les documents via le HybridRetriever (mode `notebook` = uploads uniquement) |
| **2. Grade** | Score chaque document sur [-1, 1] via LLM avec `with_structured_output` |
| **3. Decide** | `use_docs` si score ≥ 0.6 / `web_search` si tous < -0.2 / `combine` sinon |
| **4. Refine** | Décompose les docs en "knowledge strips" → score chaque strip → garde les pertinents |
| **5. Rewrite** | Reformule la question en mots-clés web si recherche web nécessaire |
| **6. Answer** | Génère la réponse finale avec le contexte raffiné + métadonnées CRAG |

---

### 3. Agent Web (`chain.py`)

**Rôle :** Agent LangChain avec outils bindés pour la recherche web autonome.

| Outil | Description |
|-------|-------------|
| `serper_search` | Recherche Google via Serper API (10 résultats, filtre Tunisie) |
| `scrape_website` | Extraction du contenu d'une URL via WebBaseLoader (max 15k chars) |

---

### 4. Agent Rédacteur (`agent_redacteur.py`)

**Rôle :** Génère des documents juridiques adaptés au projet startup.

| Document | Base légale |
|----------|-------------|
| `statuts` | Statuts de société (SUARL, SARL, SA) — Code des Sociétés Commerciales |
| `cgu` | Conditions Générales d'Utilisation — Loi n° 2004-63 |
| `contrat_investissement` | Convention d'investissement — Startup Act Art. 13+ |
| `demande_label` | Formulaire de demande du label Startup — Décret n° 2018-840 |

---

### 5. Agent Veille Web (`agent_veille.py`)

**Rôle :** Surveillance périodique des sites officiels tunisiens pour détecter les changements réglementaires.

| Site | URL | Contenu |
|------|-----|---------|
| Portail Startup Act | startup.gov.tn | Label, avantages, procédures |
| BCT | bct.gov.tn | Circulaires, devises, fintech |
| APII | apii.tn | Création d'entreprise, investissement |

---

## 🧠 Quiz de Conformité — Auto-évaluation

Le quiz évalue si **votre société** respecte le cadre juridique tunisien. Il tire **10 questions aléatoires** parmi un pool de 22 questions couvrant **9 domaines** :

| Domaine | Exemples de questions |
|---------|----------------------|
| **Startup Act** | Ancienneté < 8 ans ? Innovation technologique ? Indépendance ? |
| **Forme juridique** | Capital minimum respecté ? Statuts formels ? |
| **Protection données** | Déclaration INPDP ? Consentement explicite ? Politique de confidentialité ? |
| **Fiscalité** | Déclarations IS/TVA à jour ? Expert comptable ? |
| **Droit social** | Salariés déclarés CNSS ? Contrats écrits ? |
| **E-commerce** | Mentions légales ? CGV/CGU ? |
| **BCT / Fintech** | Agrément BCT ? KYC/AML ? Compte devises ? |
| **Propriété intellectuelle** | Marque déposée INNORPI ? |
| **Investissement** | Déclaration APII ? |

**Scoring pondéré** : Chaque question a un poids (1-3) selon sa criticité. Le score final affiche :
- Résultat par domaine avec barres de progression
- Verdict : Très bonne conformité / Partielle / Insuffisant / Non conforme
- Actions recommandées avec articles de loi correspondants

---

## 🔌 API REST (Django Backend)

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/` | GET | Racine API — liste des endpoints |
| `/api/chat/` | POST | Chat avec GraphRAG (mode `kb`) ou CRAG (mode `notebook`) |
| `/api/upload/` | POST | Upload PDF → ingestion rapide dans Qdrant (collection `user_uploads`) |
| `/api/conformite/` | POST | Analyse de conformité avec scoring pondéré par critère légal |
| `/api/documents/` | POST | Génération de documents juridiques via AgentRédacteur |
| `/api/graph/` | GET | Visualisation du graphe Neo4j (nœuds + arêtes) |
| `/api/veille/` | GET | État de la veille réglementaire |
| `/api/suggestions/` | POST | Questions suggérées contextuelles par secteur |

### Moteur de Conformité (`/api/conformite/`)

Le moteur de scoring analyse un projet startup sur **5 axes réglementaires** :

| Axe | Loi de référence | Critères vérifiés |
|-----|------------------|-------------------|
| **Startup Act** | Loi n° 2018-20 | Innovation, âge, indépendance, siège, capital |
| **Forme juridique** | Code des Sociétés | Capital minimum selon type (SUARL/SARL/SA) |
| **Protection données** | Loi n° 2004-63 | Déclaration INPDP, consentement, sécurité |
| **Réglementation BCT** | Loi 2016-48 + Circ. 2020-01 | Agrément paiement, capital, KYC/AML |
| **Commerce électronique** | Loi n° 2000-83 | Mentions légales, CGU/CGV, droit de rétractation |

---

## 🔧 Ingestion des Données (`ingest.py`)

### Pipeline d'ingestion principale (corpus juridique)

```
chunks/*.md ──► Parse sections ──► Clean + Metadata ──►  Neo4j (GraphRAG)
                                                    └──► Qdrant (Vectors)
                                                    └──► LLMGraphTransformer
```

1. **Chargement** des chunks pré-générés depuis `chunks/` (12 fichiers markdown)
2. **Nettoyage** des headers markdown, métadonnées, overlaps
3. **Enrichissement** : détection des articles, références "Vu ...", domaines juridiques
4. **Indexation Neo4j** : contraintes d'unicité, index, nœuds Document/Chunk/Article
5. **Transformation Graph** : extraction automatique d'entités et relations via `LLMGraphTransformer`
6. **Indexation Qdrant** : embeddings Ollama → upsert par batches avec vérification de dimension

### Ingestion rapide (upload utilisateur)

```
PDF Upload ──► Unstructured/pypdf ──► Chunks sémantiques ──► Qdrant (user_uploads)
```

- Collection séparée `user_uploads` pour ne pas polluer le corpus principal
- Fallback pypdf si Unstructured échoue
- Découpage sémantique intelligent : articles juridiques → chapitres → paragraphes → fallback taille fixe

---

## 🛠️ Stack Technologique

| Catégorie | Technologie | Usage |
|-----------|-------------|-------|
| **Orchestration** | LangChain | Agents, tools, retrievers, prompts |
| **LLM** | Groq (Llama 4 Scout) / Azure OpenAI | Génération de réponses |
| **Knowledge Graph** | Neo4j (local Docker / Aura) | Relations juridiques entre entités |
| **Vector Store** | Qdrant (local Docker / Cloud) | Recherche sémantique sur chunks |
| **Embeddings** | Ollama + qwen3-embedding:0.6b | Vectorisation multilingue locale |
| **Recherche Web** | Serper API + WebBaseLoader | Google Search + web scraping |
| **Backend** | Django 5 + Django REST Framework | API REST avec serializers |
| **Frontend** | Next.js 16 + React 19 + TailwindCSS 4 | Interface utilisateur |
| **UI Components** | Radix UI + ShadCN + Lucide Icons | Composants accessibles |
| **Config** | Pydantic Settings + dotenv | Validation des variables d'env |
| **Parsing PDF** | Unstructured + pypdf + pdfplumber | Extraction de texte multi-stratégie |
| **Scraping** | httpx + BeautifulSoup | Agent Veille Web |
| **Infra locale** | Docker (Neo4j 5 + Qdrant) | Stack de développement |

---

## 🚀 Installation

### Prérequis

- **Python 3.12+**
- **Node.js 18+** (pour le frontend)
- **Docker Desktop** (pour Neo4j + Qdrant en local)
- **[Ollama](https://ollama.com/download)** (pour les embeddings locaux)
- Clé API **Groq** ou **Azure OpenAI**
- Clé API **Serper** (recherche web)

### 1. Cloner et configurer l'environnement Python

```powershell
git clone <repo-url>
cd "AI project"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Lancer le stack local (Neo4j + Qdrant)

```powershell
.\scripts\start-local-stack.ps1
```

Cela démarre deux conteneurs Docker :
- **Neo4j** : http://localhost:7474 (user: `neo4j`, password: `neo4j123`)
- **Qdrant** : http://localhost:6333

### 3. Configurer les variables d'environnement

Créer un fichier `.env` à la racine :

```env
# LLM Provider
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
GROQ_BASE_URL=https://api.groq.com/openai/v1

# Azure OpenAI (alternative)
AZURE_API_KEY=your_azure_api_key
AZURE_API_BASE=https://your-resource.services.ai.azure.com
AZURE_API_VERSION=2024-05-01-preview
model=azure/YourModel

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=neo4j123
NEO4J_DATABASE=neo4j

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=complianceguard_chunks
QDRANT_USER_COLLECTION_NAME=user_uploads

# Serper (recherche web)
SERPER_API_KEY=your_serper_key
```

### 4. Télécharger le modèle d'embedding

```powershell
ollama pull qwen3-embedding:0.6b
```

### 5. Ingérer les documents juridiques

```powershell
python -m complianceguard.ingest
```

### 6. Lancer le backend Django

```powershell
cd backend
python manage.py runserver
```

### 7. Lancer le frontend Next.js

```powershell
cd frontend
npm install
npm run dev
```

L'application est accessible sur **http://localhost:3000**.

---

## 🧪 Guide de Test — Exemples par Fonctionnalité

### 💬 Chat Juridique

**Mode Base juridique (GraphRAG) :**

| Question à tester | Résultat attendu |
|--------------------|------------------|
| `Quels sont les avantages fiscaux du Startup Act ?` | Réponse citant Art. 13, exonération IS 4 ans |
| `Comment obtenir le label startup ?` | Procédure via Startup Tunisia, conditions Art. 3 |
| `Quelle est la procédure pour obtenir le label startup ?` | Multi-hop graph traversal |
| `Capital minimum pour une SARL ?` | 1 000 TND, Code des Sociétés Art. 92 |
| `Quelles sont les sanctions INPDP ?` | Protection données, Loi 2004-63 |
| `Comment ouvrir un compte en devises startup ?` | Circulaire BCT 2019-01 |

**Mode Mes documents (CRAG) — après upload PDF :**

| Question à tester | Résultat attendu |
|--------------------|------------------|
| `Résume ce document en 5 points clés` | Résumé basé uniquement sur le PDF uploadé |
| `Quels articles sont mentionnés ?` | Extraction d'entités juridiques |
| `Quelles obligations sont définies ?` | Analyse juridique ciblée |
| `Ce document mentionne-t-il des sanctions ?` | Recherche ciblée dans le contenu |

---

### 📝 Documents

| Test | Paramètres |
|------|-----------|
| **Statuts SUARL** | Nom: `TechInnovate` • Activité: `Plateforme SaaS B2B` • Capital: `5000` • Type: `SUARL` |
| **CGU** | Nom: `DataSafe` • Activité: `Application mobile santé` |
| **Pack complet** | Type: `Pack Complet` → génère les 4 documents |

---

### ✅ Conformité

| Test | Paramètres | Score attendu |
|------|-----------|---------------|
| **Fintech** | Secteur: Fintech • Desc: `Plateforme de paiement mobile avec wallet digital` • Capital: 50 000 | ~40% — alerte BCT |
| **SaaS simple** | Secteur: SaaS • Desc: `Application de gestion de projets pour PME avec IA` • Capital: 5 000 | ~70%+ |
| **HealthTech** | Secteur: HealthTech • Desc: `Application mobile de suivi médical avec données patients` | Score moyen — alerte INPDP |

---

### 🧠 Quiz Conformité

| Test | Comment | Résultat |
|------|---------|----------|
| **Startup conforme** | Répondre la 1ère option (conforme) à chaque question | ~100%, "Très bonne conformité" |
| **Non-conforme** | Répondre "Non" aux questions | Score bas + liste de recommandations |
| **Cas réaliste** | Répondre honnêtement pour votre propre société | Score réel + actions par domaine |

---

## 📚 Sources Juridiques Intégrées

| Document | Description | Domaines |
|----------|-------------|----------|
| Loi n° 2018-20 | Startup Act tunisien | Label, IS, congé, bourse, devises |
| Décret n° 2018-840 | Décret d'application | Procédure labélisation, conditions |
| Circulaire BCT 2019-01 | Comptes startup en devises | Changes, levée de fonds |
| Circulaire BCT 2019-02 | Carte Technologique | Transferts courants |
| Code des Sociétés | Droit des sociétés commerciales | SARL, SA, SAS, capital, statuts |
| Code Fiscal 2023 | Droits et Procédures Fiscaux | IS, TVA, déclarations |
| Code du Travail | Droit du travail tunisien | Contrats, licenciement, congés |
| Loi n° 2004-63 | Protection données personnelles | INPDP, vie privée |
| Loi n° 2000-83 | Échanges électroniques | Signature, e-commerce |
| Loi n° 2016-71 | Investissement | APII, incitations, FOPRODI |

---

## 📄 Licence

Projet privé — Usage interne uniquement.

---

*Développé pour faciliter la conformité juridique des startups tunisiennes* 🇹🇳

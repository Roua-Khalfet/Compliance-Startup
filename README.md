# 🚀 Startup Analyzer

## 📌 Description du projet

**Startup Analyzer** est une application intelligente dédiée à l'**analyse concurrentielle des projets startup** d'un point de vue marketing.

Le système permet d'explorer un projet, d'analyser ses concurrents et de générer automatiquement des insights stratégiques grâce à des agents intelligents basés sur des modèles LLM.

---

## 🎯 Objectifs

- 🔍 Analyser un projet et son marché
- 🏢 Identifier et afficher les concurrents
- 📊 Générer une analyse SWOT individuelle
- 🔀 Créer un SWOT combiné (multi-concurrents)
- ⚡ Définir des actions prioritaires
- 🧠 Générer des personas clients
- 📑 Produire une présentation automatique (PPT/PDF)
- 🎤 Générer un pitch audio du projet

---

## 🧠 Architecture Multi-Agents

Le projet repose sur une architecture **multi-agents intelligents** orchestrée via LangChain :

| Agent | Rôle |
|---|---|
| `agent1_search.js` | Recherche d'informations sur le projet |
| `agent2_scraper.js` | Extraction de données web |
| `agent2b_reviews.js` | Analyse des avis clients |
| `agent3_swot.js` | Génération de l'analyse SWOT |
| `agent4_persona.js` | Génération des personas clients |
| `chatbot_agent.js` | Interaction utilisateur |
| `llmRouter.js` | Routage intelligent entre les modèles LLM |
| `sharedContext.js` | Contexte partagé entre les agents |

### 🤖 Modèles LLM utilisés

- **LLaMA 3.1 Instruct** — Génération précise et structurée
- **LLaMA 3.3 Versatile** — Analyse créative et synthèse

---

## 🛠️ Stack Technologique

| Couche | Technologie |
|---|---|
| Frontend | React.js (Vite) |
| Backend | Django + Django REST Framework |
| Orchestration IA | LangChain |
| LLM | LLaMA 3.1 / 3.3 via Groq API |
| Génération PPT | pptxgenjs |
| Export PDF | jsPDF + html2canvas |

---

## 📁 Structure du projet

```
startup-analyzer/
│
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── api/
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── models.py
│   └── shared_contexts/
│
├── src/
│   ├── agents/
│   │   ├── agent1_search.js
│   │   ├── agent2_scraper.js
│   │   ├── agent2b_reviews.js
│   │   ├── agent3_swot.js
│   │   ├── agent4_persona.js
│   │   ├── chatbot_agent.js
│   │   ├── llmRouter.js
│   │   └── sharedContext.js
│   ├── components/
│   ├── hooks/
│   └── utils/
│
├── .env
├── .gitignore
├── package.json
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

### Prérequis

- Python 3.10+
- Node.js 18+
- Clé API Groq
- Clé API Google (Serper ou Custom Search)

---

### 1. Cloner le projet

```bash
git clone https://github.com/your-username/startup-analyzer.git
cd startup-analyzer
```

---

### 2. Backend (Django)

```bash
cd backend

# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement
# Windows :
venv\Scripts\activate
# Mac/Linux :
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Générer une clé Django secrète
python -c "import secrets; print(secrets.token_urlsafe(50))"

# Appliquer les migrations
python manage.py migrate

# Lancer le serveur
python manage.py runserver 8000
```

---

### 3. Frontend (React)

```bash
# Depuis la racine du projet
npm install
npm install pptxgenjs jspdf html2canvas
npm run dev
```

---

## 🔐 Variables d'environnement

Créer un fichier `.env` à la racine :

```env
GOOGLE_API_KEY=your_google_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

---

## 🚀 Fonctionnalités détaillées

### 🔍 Analyse concurrentielle automatique
Identification et affichage des concurrents directs et indirects du projet sur le marché cible.

### 📊 Génération SWOT
Analyse des Forces, Faiblesses, Opportunités et Menaces du projet ainsi qu'un **SWOT combiné** croisant le projet avec ses concurrents.

### ⚡ Actions prioritaires
Recommandations stratégiques générées automatiquement à partir de l'analyse SWOT.

### 🧠 Personas clients
Création de profils utilisateurs cibles détaillés (démographie, motivations, comportements).

### 📑 Génération de présentation
Export automatique de l'analyse complète en **PowerPoint** ou **PDF** prêt à partager.

### 🎤 Pitch audio
Synthèse vocale du pitch projet pour une présentation orale du résultat.

---

## 💡 Exemple de prompt

Je souhaite ouvrir une salle de sport moderne dans le Grand Tunis, dans le secteur du fitness et du bien-être physique. Ma cible principale sont les jeunes de 18-35 ans et les actifs qui cherchent un accompagnement sérieux. Je propose des abonnements mensuels entre 80 et 150 TND incluant du coaching personnalisé et des cours collectifs variés. Le problème que je résous est le manque de motivation et d'accompagnement personnalisé dans les salles de sport classiques de Tunis. Mon différenciateur principal est la combinaison d'un suivi digital via application mobile avec un coaching sur mesure, des cours variés et une expérience client premium — ce que très peu de salles proposent actuellement dans le Grand Tunis. Nous sommes en phase d'idée avec un budget de démarrage de 200 000 TND. Le modèle économique repose sur des abonnements mensuels et des packages coaching. Notre zone de chalandise cible les quartiers de Tunis comme La Marsa, Les Berges du Lac, Ariana et El Menzah où le pouvoir d'achat est plus élevé et la demande en fitness est forte.


---

## 👨‍💻 Auteurs

Projet réalisé dans le cadre d'un projet académique en Intelligence Artificielle — 4ème année IA.

---

## 💡 Améliorations futures

- Intégration de plus de sources de données
- Amélioration des modèles LLM
- Dashboard interactif avancé
- Déploiement cloud

---

## 📜 Licence

Ce projet est à usage éducatif.

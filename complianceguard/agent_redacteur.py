#!/usr/bin/env python
"""
AgentRedacteur - Génération de documents juridiques pour startups tunisiennes.

Génère des documents adaptés au projet basés sur:
- Les résultats de conformité (GraphRAG)
- Les templates juridiques tunisiens
- Les informations spécifiques du projet
"""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class ProjectInfo:
    """Informations sur le projet startup."""
    nom_startup: str
    activite: str
    fondateurs: list[str] = field(default_factory=list)
    capital_social: int = 1000  # En TND
    siege_social: str = "Tunis"
    type_societe: str = "SUARL"  # SUARL, SARL, SA
    email_contact: str = ""
    date_creation: str = field(default_factory=lambda: datetime.now().strftime("%d/%m/%Y"))


# Templates de documents
TEMPLATES = {
    "statuts": """
# STATUTS DE {nom_startup}
## {type_societe}

**Date de constitution:** {date_creation}

### TITRE I - FORME - OBJET - DÉNOMINATION - SIÈGE - DURÉE

**Article 1 - Forme**
Il est formé entre les soussignés une société à responsabilité limitée ({type_societe}) régie par les lois en vigueur en Tunisie, notamment le Code des Sociétés Commerciales et la Loi n° 2018-20 du 17 avril 2018 relative aux startups.

**Article 2 - Objet**
La société a pour objet:
{activite}

Et plus généralement, toutes opérations commerciales, industrielles, mobilières, immobilières et financières se rattachant directement ou indirectement à l'objet social.

**Article 3 - Dénomination**
La société prend la dénomination de: **{nom_startup}**

**Article 4 - Siège social**
Le siège social est fixé à: {siege_social}

**Article 5 - Durée**
La durée de la société est fixée à quatre-vingt-dix-neuf (99) années à compter de la date de son immatriculation au Registre du Commerce.

### TITRE II - APPORTS - CAPITAL SOCIAL

**Article 6 - Capital social**
Le capital social est fixé à la somme de **{capital_social} TND** (Dinars Tunisiens).

**Article 7 - Parts sociales**
Les parts sociales sont réparties entre les associés comme suit:
{repartition_parts}

### TITRE III - GÉRANCE

**Article 8 - Gérance**
La société est gérée par un ou plusieurs gérants, personnes physiques, associés ou non.

### TITRE IV - DISPOSITIONS STARTUP ACT

**Article 9 - Label Startup**
Conformément à la Loi n° 2018-20 du 17 avril 2018 (Startup Act), la société peut solliciter le label "Startup" auprès du Comité de Labélisation si elle remplit les conditions prévues à l'article 3 de ladite loi.

**Article 10 - Avantages**
En cas d'obtention du label Startup, la société pourra bénéficier des avantages prévus par le Startup Act, notamment:
- Exonérations fiscales
- Congé pour création d'entreprise
- Compte spécial en devises
- Facilités de financement

---
*Document généré automatiquement par ComplianceGuard - À faire valider par un conseiller juridique*
""",

    "cgu": """
# CONDITIONS GÉNÉRALES D'UTILISATION
## {nom_startup}

**Dernière mise à jour:** {date_creation}

### Article 1 - Mentions légales

Le présent site/application est édité par:
- **Raison sociale:** {nom_startup}
- **Forme juridique:** {type_societe}
- **Siège social:** {siege_social}
- **Contact:** {email_contact}

### Article 2 - Objet

Les présentes Conditions Générales d'Utilisation (CGU) ont pour objet de définir les modalités d'accès et d'utilisation des services proposés par {nom_startup}.

### Article 3 - Acceptation des CGU

L'utilisation des services implique l'acceptation pleine et entière des présentes CGU.

### Article 4 - Services proposés

{nom_startup} propose les services suivants:
{activite}

### Article 5 - Protection des données personnelles

Conformément à la loi organique n° 2004-63 du 27 juillet 2004 relative à la protection des données à caractère personnel, les utilisateurs disposent d'un droit d'accès, de rectification et de suppression de leurs données.

### Article 6 - Propriété intellectuelle

L'ensemble des éléments constituant le site/application (textes, graphismes, logiciels, etc.) est la propriété exclusive de {nom_startup}.

### Article 7 - Responsabilité

{nom_startup} s'engage à mettre en œuvre tous les moyens nécessaires pour assurer la continuité du service, sans obligation de résultat.

### Article 8 - Droit applicable

Les présentes CGU sont régies par le droit tunisien. Tout litige sera soumis aux tribunaux compétents de Tunis.

---
*Document généré automatiquement par ComplianceGuard - À faire valider par un conseiller juridique*
""",

    "contrat_investissement": """
# CONTRAT D'INVESTISSEMENT
## Convention d'investissement dans {nom_startup}

**Date:** {date_creation}

### ENTRE LES SOUSSIGNÉS

**La Startup:**
- Dénomination: {nom_startup}
- Forme: {type_societe}
- Siège: {siege_social}
- Représentée par: {fondateurs_str}

Ci-après dénommée "la Startup"

**ET**

**L'Investisseur:**
- Nom/Raison sociale: [À COMPLÉTER]
- Adresse: [À COMPLÉTER]

Ci-après dénommé "l'Investisseur"

### PRÉAMBULE

La Startup exerce l'activité suivante: {activite}

La Startup a obtenu / sollicite le label "Startup" conformément à la Loi n° 2018-20 du 17 avril 2018.

L'Investisseur souhaite participer au financement de la Startup.

### ARTICLE 1 - OBJET

Le présent contrat a pour objet de définir les conditions dans lesquelles l'Investisseur investit dans le capital de la Startup.

### ARTICLE 2 - MONTANT DE L'INVESTISSEMENT

L'Investisseur s'engage à apporter la somme de [MONTANT] TND.

### ARTICLE 3 - CONTREPARTIE

En contrepartie de cet apport, l'Investisseur recevra [NOMBRE] parts sociales de la Startup, représentant [POURCENTAGE]% du capital social.

### ARTICLE 4 - AVANTAGES FISCAUX (Startup Act)

Conformément aux articles 13 et suivants de la Loi n° 2018-20:
- Les personnes physiques qui investissent dans le capital de la Startup bénéficient d'une déduction de leurs revenus imposables dans la limite de [MONTANT] TND par an.
- Conditions: présentation du label Startup et attestation de libération du capital.

### ARTICLE 5 - GARANTIES

La Startup garantit:
- L'exactitude des informations communiquées
- Sa conformité aux dispositions légales en vigueur
- L'absence de litiges en cours affectant sa situation

### ARTICLE 6 - DROIT DE SORTIE

Les modalités de sortie de l'Investisseur seront définies dans un pacte d'associés séparé.

### ARTICLE 7 - CONFIDENTIALITÉ

Les parties s'engagent à garder confidentielles les informations échangées dans le cadre du présent contrat.

### ARTICLE 8 - DROIT APPLICABLE

Le présent contrat est régi par le droit tunisien. Tout litige sera soumis aux tribunaux de Tunis.

---
**Fait à {siege_social}, le {date_creation}**

Pour la Startup: _________________ | Pour l'Investisseur: _________________

---
*Document généré automatiquement par ComplianceGuard - À faire valider par un conseiller juridique*
""",

    "demande_label": """
# DEMANDE D'ATTRIBUTION DU LABEL STARTUP
## Formulaire de candidature

**Date de dépôt:** {date_creation}

### I. INFORMATIONS SUR LA SOCIÉTÉ

| Champ | Valeur |
|-------|--------|
| Dénomination sociale | {nom_startup} |
| Forme juridique | {type_societe} |
| Capital social | {capital_social} TND |
| Siège social | {siege_social} |
| Date de création | {date_creation} |

### II. FONDATEURS

{liste_fondateurs}

### III. ACTIVITÉ

**Description de l'activité:**
{activite}

### IV. CRITÈRES D'ÉLIGIBILITÉ (Art. 3, Loi 2018-20)

Cochez les critères remplis:

- [ ] Existence de moins de 8 ans
- [ ] Effectif inférieur à 100 employés
- [ ] Capital détenu majoritairement par des personnes physiques ou fonds d'investissement
- [ ] Total du bilan annuel < 15 millions TND
- [ ] Modèle économique innovant et à fort potentiel de croissance

### V. PIÈCES JUSTIFICATIVES À JOINDRE

Conformément au Décret n° 2018-840:

- [ ] Extrait du registre de commerce (< 3 mois)
- [ ] Copie des statuts de la société
- [ ] Attestation d'adhésion à la CNSS
- [ ] États financiers de l'année précédente (si applicable)
- [ ] Business plan / Présentation du projet

### VI. DÉCLARATION

Je soussigné(e), représentant légal de {nom_startup}, certifie l'exactitude des informations fournies et m'engage à respecter les obligations liées au label Startup.

**Signature:** _________________

**Date:** {date_creation}

---
*Formulaire à soumettre via: https://startup.gov.tn*
*Document généré automatiquement par ComplianceGuard*
"""
}


def _build_llm() -> AzureChatOpenAI:
    """Construit le client LLM Azure."""
    azure_endpoint = os.getenv("AZURE_API_BASE", "").strip()
    model = os.getenv("AZURE_MODEL", "").strip()
    api_version = os.getenv("AZURE_API_VERSION", "2024-02-01").strip()
    api_key = os.getenv("AZURE_API_KEY", "").strip()
    
    if "/" in model:
        model = model.split("/", 1)[1].strip()
    
    return AzureChatOpenAI(
        azure_endpoint=azure_endpoint,
        azure_deployment=model,
        api_version=api_version,
        api_key=api_key,
        temperature=0.3,
    )


class AgentRedacteur:
    """Agent de rédaction de documents juridiques pour startups."""
    
    def __init__(self):
        self.llm = _build_llm()
        self.templates = TEMPLATES
    
    def _format_template(self, template_name: str, project: ProjectInfo) -> str:
        """Remplit un template avec les infos du projet."""
        template = self.templates.get(template_name, "")
        
        # Préparation des données
        fondateurs_str = ", ".join(project.fondateurs) if project.fondateurs else "[À COMPLÉTER]"
        
        # Répartition des parts (égale par défaut)
        if project.fondateurs:
            parts_par_fondateur = project.capital_social // len(project.fondateurs)
            repartition = "\n".join([
                f"- {f}: {parts_par_fondateur} TND ({100 // len(project.fondateurs)}%)"
                for f in project.fondateurs
            ])
        else:
            repartition = "- [À COMPLÉTER]"
        
        # Liste fondateurs formatée
        liste_fondateurs = "\n".join([
            f"- **Fondateur {i+1}:** {f}" 
            for i, f in enumerate(project.fondateurs)
        ]) if project.fondateurs else "- [À COMPLÉTER]"
        
        # Remplacement des variables
        return template.format(
            nom_startup=project.nom_startup,
            activite=project.activite,
            type_societe=project.type_societe,
            capital_social=project.capital_social,
            siege_social=project.siege_social,
            date_creation=project.date_creation,
            email_contact=project.email_contact or "[À COMPLÉTER]",
            fondateurs_str=fondateurs_str,
            repartition_parts=repartition,
            liste_fondateurs=liste_fondateurs,
        )
    
    def generer_document(
        self, 
        doc_type: str, 
        project: ProjectInfo,
        instructions_supplementaires: str = ""
    ) -> str:
        """
        Génère un document juridique.
        
        Args:
            doc_type: Type de document (statuts, cgu, contrat_investissement, demande_label)
            project: Informations sur le projet
            instructions_supplementaires: Instructions spécifiques pour le LLM
        
        Returns:
            Document généré au format Markdown
        """
        if doc_type not in self.templates:
            return f"❌ Type de document inconnu: {doc_type}. Types disponibles: {list(self.templates.keys())}"
        
        # Générer le document de base
        doc_base = self._format_template(doc_type, project)
        
        # Si pas d'instructions supplémentaires, retourner le template rempli
        if not instructions_supplementaires:
            return doc_base
        
        # Sinon, utiliser le LLM pour adapter/enrichir
        system_prompt = (
            "Tu es un assistant juridique spécialisé dans le droit tunisien des startups. "
            "Tu dois adapter et enrichir le document fourni selon les instructions. "
            "Garde la structure et le format Markdown. "
            "Assure-toi que le document reste conforme au droit tunisien (Startup Act, Code des Sociétés)."
        )
        
        human_prompt = (
            f"Voici un document juridique de base:\n\n{doc_base}\n\n"
            f"Instructions d'adaptation:\n{instructions_supplementaires}\n\n"
            "Adapte et enrichis ce document selon les instructions tout en gardant sa structure."
        )
        
        result = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])
        
        return result.content if hasattr(result, "content") else str(result)
    
    def generer_pack_complet(self, project: ProjectInfo) -> dict[str, str]:
        """
        Génère tous les documents pour un projet.
        
        Returns:
            Dict avec les documents générés
        """
        print(f"📝 Génération du pack documentaire pour {project.nom_startup}...")
        
        documents = {}
        for doc_type in self.templates.keys():
            print(f"  → Génération: {doc_type}")
            documents[doc_type] = self._format_template(doc_type, project)
        
        return documents
    
    def sauvegarder_documents(
        self, 
        documents: dict[str, str], 
        output_dir: Path,
        project_name: str
    ) -> list[Path]:
        """Sauvegarde les documents générés dans des fichiers."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        for doc_type, content in documents.items():
            filename = f"{project_name}_{doc_type}.md"
            filepath = output_dir / filename
            filepath.write_text(content, encoding="utf-8")
            saved_files.append(filepath)
            print(f"  ✅ Sauvegardé: {filepath}")
        
        return saved_files


def main():
    """CLI pour l'AgentRedacteur."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AgentRedacteur - Génération de documents juridiques")
    parser.add_argument("--nom", required=True, help="Nom de la startup")
    parser.add_argument("--activite", required=True, help="Description de l'activité")
    parser.add_argument("--fondateurs", nargs="+", help="Liste des fondateurs")
    parser.add_argument("--capital", type=int, default=1000, help="Capital social (TND)")
    parser.add_argument("--siege", default="Tunis", help="Siège social")
    parser.add_argument("--type", choices=["SUARL", "SARL", "SA"], default="SUARL", help="Type de société")
    parser.add_argument("--doc", choices=list(TEMPLATES.keys()) + ["all"], default="all", help="Document à générer")
    parser.add_argument("--output", default="documents_generes", help="Dossier de sortie")
    
    args = parser.parse_args()
    
    # Créer le projet
    project = ProjectInfo(
        nom_startup=args.nom,
        activite=args.activite,
        fondateurs=args.fondateurs or [],
        capital_social=args.capital,
        siege_social=args.siege,
        type_societe=args.type,
    )
    
    agent = AgentRedacteur()
    
    if args.doc == "all":
        # Générer tous les documents
        documents = agent.generer_pack_complet(project)
        output_dir = PROJECT_ROOT / args.output
        agent.sauvegarder_documents(documents, output_dir, project.nom_startup)
    else:
        # Générer un seul document
        doc = agent.generer_document(args.doc, project)
        print(doc)


if __name__ == "__main__":
    main()

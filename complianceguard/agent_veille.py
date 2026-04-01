#!/usr/bin/env python
"""
AgentVeilleWeb - Agent de surveillance des changements réglementaires.

Cet agent scrape périodiquement les sites officiels tunisiens pour détecter
les modifications de textes légaux depuis la dernière ingestion.

Sites surveillés:
- startup.gov.tn : Portail officiel du Startup Act
- bct.gov.tn : Banque Centrale de Tunisie (circulaires)
- apii.tn : Agence de Promotion de l'Industrie et de l'Innovation
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# ============================================================================
# Configuration
# ============================================================================

# Cache file for storing page hashes
CACHE_FILE = PROJECT_ROOT / "complianceguard" / ".veille_cache.json"

# Sites à surveiller
SITES_TO_MONITOR = [
    {
        "id": "startup_gov",
        "url": "https://startup.gov.tn",
        "name": "Portail Startup Act",
        "pages": [
            "/",
            "/fr/label-startup",
            "/fr/avantages",
        ],
        "keywords": ["startup", "label", "avantages", "loi", "décret"],
    },
    {
        "id": "bct",
        "url": "https://www.bct.gov.tn",
        "name": "BCT - Banque Centrale",
        "pages": [
            "/fr/Circulaires/circulaires.jsp",
        ],
        "keywords": ["circulaire", "devises", "paiement", "fintech"],
    },
    {
        "id": "apii",
        "url": "https://www.apii.tn",
        "name": "APII",
        "pages": [
            "/",
            "/fr/creation-entreprises",
        ],
        "keywords": ["création", "entreprise", "investissement", "avantages"],
    },
]

# ============================================================================
# Models
# ============================================================================

@dataclass
class PageHash:
    """Hash d'une page web à un instant T."""
    url: str
    hash: str
    timestamp: str
    content_length: int

@dataclass
class VeilleResult:
    """Résultat de la surveillance d'un site."""
    site_id: str
    site_name: str
    url: str
    status: str  # "ok" | "changed" | "error" | "new"
    last_check: str
    has_changed: bool
    changes: list[str] = field(default_factory=list)
    error_message: Optional[str] = None

@dataclass
class VeilleCache:
    """Cache des hashs précédents."""
    pages: dict[str, PageHash] = field(default_factory=dict)
    last_update: str = ""

# Pydantic models for API
class VeilleItem(BaseModel):
    url: str
    nom: str
    last_check: str
    has_changed: bool
    status: str

class VeilleResponse(BaseModel):
    items: list[VeilleItem]
    last_update: str

# ============================================================================
# Cache Management
# ============================================================================

def load_cache() -> VeilleCache:
    """Charge le cache depuis le fichier JSON."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                pages = {
                    url: PageHash(**page_data)
                    for url, page_data in data.get("pages", {}).items()
                }
                return VeilleCache(
                    pages=pages,
                    last_update=data.get("last_update", "")
                )
        except (json.JSONDecodeError, KeyError):
            pass
    return VeilleCache()

def save_cache(cache: VeilleCache) -> None:
    """Sauvegarde le cache dans le fichier JSON."""
    data = {
        "pages": {url: asdict(page) for url, page in cache.pages.items()},
        "last_update": cache.last_update
    }
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ============================================================================
# Scraping Functions
# ============================================================================

def compute_content_hash(content: str) -> str:
    """Calcule le hash SHA256 du contenu normalisé."""
    # Normaliser le contenu (retirer espaces multiples, timestamps, etc.)
    normalized = re.sub(r'\s+', ' ', content.strip())
    # Retirer les dates/heures qui changent souvent
    normalized = re.sub(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', '', normalized)
    normalized = re.sub(r'\d{1,2}:\d{2}(:\d{2})?', '', normalized)
    return hashlib.sha256(normalized.encode()).hexdigest()

def extract_text_content(html: str) -> str:
    """Extrait le texte principal d'une page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    
    # Retirer les éléments non pertinents
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    
    # Extraire le texte
    text = soup.get_text(separator=" ", strip=True)
    return text

async def fetch_page(url: str, timeout: float = 30.0) -> tuple[str, int]:
    """Récupère le contenu d'une page web."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.text, len(response.content)

def extract_relevant_sections(html: str, keywords: list[str]) -> str:
    """Extrait les sections contenant les mots-clés pertinents."""
    soup = BeautifulSoup(html, "html.parser")
    relevant_text = []
    
    # Chercher dans les sections principales
    for tag in soup.find_all(["article", "section", "div", "p", "h1", "h2", "h3"]):
        text = tag.get_text(strip=True).lower()
        if any(kw.lower() in text for kw in keywords):
            relevant_text.append(tag.get_text(separator=" ", strip=True))
    
    return "\n".join(relevant_text) if relevant_text else extract_text_content(html)

# ============================================================================
# Veille Agent
# ============================================================================

class AgentVeilleWeb:
    """Agent de surveillance des changements réglementaires."""
    
    def __init__(self):
        self.cache = load_cache()
        self.results: list[VeilleResult] = []
    
    async def check_page(self, site: dict, page_path: str) -> VeilleResult:
        """Vérifie une page pour des changements."""
        url = urljoin(site["url"], page_path)
        timestamp = datetime.now().isoformat()
        
        try:
            html, content_length = await fetch_page(url)
            
            # Extraire le contenu pertinent
            content = extract_relevant_sections(html, site.get("keywords", []))
            new_hash = compute_content_hash(content)
            
            # Comparer avec le cache
            old_page = self.cache.pages.get(url)
            
            if old_page is None:
                # Nouvelle page
                status = "new"
                has_changed = False
                changes = ["Première surveillance de cette page"]
            elif old_page.hash != new_hash:
                # Page modifiée
                status = "changed"
                has_changed = True
                changes = [
                    f"Contenu modifié depuis {old_page.timestamp}",
                    f"Taille: {old_page.content_length} → {content_length} bytes",
                ]
            else:
                # Pas de changement
                status = "ok"
                has_changed = False
                changes = []
            
            # Mettre à jour le cache
            self.cache.pages[url] = PageHash(
                url=url,
                hash=new_hash,
                timestamp=timestamp,
                content_length=content_length
            )
            
            return VeilleResult(
                site_id=site["id"],
                site_name=site["name"],
                url=url,
                status=status,
                last_check=timestamp,
                has_changed=has_changed,
                changes=changes,
            )
            
        except httpx.HTTPStatusError as e:
            return VeilleResult(
                site_id=site["id"],
                site_name=site["name"],
                url=url,
                status="error",
                last_check=timestamp,
                has_changed=False,
                error_message=f"HTTP {e.response.status_code}",
            )
        except Exception as e:
            return VeilleResult(
                site_id=site["id"],
                site_name=site["name"],
                url=url,
                status="error",
                last_check=timestamp,
                has_changed=False,
                error_message=str(e),
            )
    
    async def run_full_check(self) -> list[VeilleResult]:
        """Lance une vérification complète de tous les sites."""
        import asyncio
        
        self.results = []
        tasks = []
        
        for site in SITES_TO_MONITOR:
            for page in site["pages"]:
                tasks.append(self.check_page(site, page))
        
        self.results = await asyncio.gather(*tasks)
        
        # Sauvegarder le cache
        self.cache.last_update = datetime.now().isoformat()
        save_cache(self.cache)
        
        return self.results
    
    def get_summary(self) -> dict:
        """Retourne un résumé de la dernière vérification."""
        if not self.results:
            return {
                "status": "no_data",
                "message": "Aucune vérification n'a été effectuée",
            }
        
        changed = [r for r in self.results if r.has_changed]
        errors = [r for r in self.results if r.status == "error"]
        
        return {
            "total_pages": len(self.results),
            "changed": len(changed),
            "errors": len(errors),
            "ok": len(self.results) - len(changed) - len(errors),
            "changed_sites": [r.site_name for r in changed],
            "error_sites": [r.site_name for r in errors],
            "last_update": self.cache.last_update,
        }
    
    def generate_report(self) -> str:
        """Génère un rapport markdown des changements détectés."""
        summary = self.get_summary()
        
        report = f"""# Rapport de Veille Réglementaire

**Date:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

## Résumé

- **Pages surveillées:** {summary.get('total_pages', 0)}
- **Changements détectés:** {summary.get('changed', 0)}
- **Erreurs:** {summary.get('errors', 0)}

"""
        
        if summary.get("changed", 0) > 0:
            report += "## ⚠️ Changements Détectés\n\n"
            for result in self.results:
                if result.has_changed:
                    report += f"### {result.site_name}\n"
                    report += f"- **URL:** {result.url}\n"
                    for change in result.changes:
                        report += f"- {change}\n"
                    report += "\n"
        
        if summary.get("errors", 0) > 0:
            report += "## ❌ Erreurs\n\n"
            for result in self.results:
                if result.status == "error":
                    report += f"- **{result.site_name}** ({result.url}): {result.error_message}\n"
        
        report += "\n## Sites Surveillés\n\n"
        report += "| Site | URL | Statut |\n"
        report += "|------|-----|--------|\n"
        
        for site in SITES_TO_MONITOR:
            site_results = [r for r in self.results if r.site_id == site["id"]]
            if site_results:
                status_emoji = "🔴" if any(r.has_changed for r in site_results) else "🟢"
                report += f"| {site['name']} | {site['url']} | {status_emoji} |\n"
        
        return report

# ============================================================================
# API Function (imported by api.py)
# ============================================================================

async def get_veille_status() -> VeilleResponse:
    """Récupère l'état actuel de la veille (utilisé par l'API)."""
    cache = load_cache()
    
    items = []
    for site in SITES_TO_MONITOR:
        # Récupérer le dernier état de la page principale
        main_url = site["url"]
        page_info = cache.pages.get(main_url)
        
        if page_info:
            # Vérifier si changé depuis la dernière ingestion (simplification)
            has_changed = False  # À implémenter avec la date d'ingestion
            items.append(VeilleItem(
                url=main_url,
                nom=site["name"],
                last_check=page_info.timestamp,
                has_changed=has_changed,
                status="ok" if not has_changed else "changed"
            ))
        else:
            items.append(VeilleItem(
                url=main_url,
                nom=site["name"],
                last_check=datetime.now().isoformat(),
                has_changed=False,
                status="pending"  # Jamais vérifié
            ))
    
    return VeilleResponse(
        items=items,
        last_update=cache.last_update or datetime.now().isoformat()
    )

# ============================================================================
# CLI Interface
# ============================================================================

async def main():
    """Point d'entrée CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AgentVeilleWeb - Surveillance réglementaire")
    parser.add_argument("--check", action="store_true", help="Lancer une vérification complète")
    parser.add_argument("--report", action="store_true", help="Générer un rapport")
    parser.add_argument("--status", action="store_true", help="Afficher le statut actuel")
    parser.add_argument("--output", "-o", type=str, help="Fichier de sortie pour le rapport")
    
    args = parser.parse_args()
    
    agent = AgentVeilleWeb()
    
    if args.check:
        print("🔍 Vérification des sites officiels en cours...")
        results = await agent.run_full_check()
        
        print(f"\n✅ Vérification terminée: {len(results)} pages analysées")
        
        summary = agent.get_summary()
        if summary["changed"] > 0:
            print(f"⚠️  {summary['changed']} changement(s) détecté(s):")
            for site in summary["changed_sites"]:
                print(f"   - {site}")
        else:
            print("✅ Aucun changement détecté")
        
        if summary["errors"] > 0:
            print(f"❌ {summary['errors']} erreur(s)")
    
    if args.report or args.output:
        # Si pas de vérification faite, charger depuis le cache
        if not agent.results:
            print("⚠️  Aucune vérification récente. Utilisez --check d'abord.")
            return
        
        report = agent.generate_report()
        
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(report, encoding="utf-8")
            print(f"📄 Rapport sauvegardé: {output_path}")
        else:
            print(report)
    
    if args.status:
        cache = load_cache()
        print(f"📊 Dernière mise à jour: {cache.last_update or 'Jamais'}")
        print(f"📄 Pages en cache: {len(cache.pages)}")
        
        for url, page in cache.pages.items():
            print(f"   - {url}")
            print(f"     Vérifié: {page.timestamp}")
    
    if not any([args.check, args.report, args.status, args.output]):
        parser.print_help()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

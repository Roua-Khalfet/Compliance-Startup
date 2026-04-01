import { useEffect, useState, useCallback } from "react";
import { Check, AlertTriangle, X, FileText, ClipboardList, PenLine, Download, ArrowRight, RefreshCw, ExternalLink, Shield, Clock, Lightbulb, Scale, ChevronDown, ChevronUp } from "lucide-react";

const API_BASE = "http://localhost:8000/api";

interface Criterion {
  label: string;
  score: number;
  status: "check" | "warning" | "x";
  article: string;
  article_source: string;
  details: string;
  category?: string;
  recommendation?: string | null;
}

interface RiskProfile {
  niveau: string;
  autorisations_requises: string[];
  capital_recommande: number;
  delai_conformite: string;
}

interface ConformiteData {
  score_global: number;
  status: "conforme" | "conforme_reserves" | "non_conforme";
  criteres: Criterion[];
  risk_profile?: RiskProfile;
  recommendations?: string[];
  lois_applicables?: string[];
}

interface GraphNode {
  id: string;
  label: string;
  type: string;
}

interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const documents = [
  { icon: FileText, name: "Statuts adaptés.md", type: "statuts" },
  { icon: ClipboardList, name: "CGU conformes.md", type: "cgu" },
  { icon: PenLine, name: "Contrat type.md", type: "contrat_investissement" },
];

const CriterionIcon = ({ type }: { type: string }) => {
  if (type === "check") return <Check size={14} className="text-success" />;
  if (type === "warning") return <AlertTriangle size={14} className="text-warning" />;
  return <X size={14} className="text-destructive" />;
};

const statusLabels: Record<string, { text: string; class: string; bg: string }> = {
  conforme: { text: "Conforme", class: "text-success", bg: "bg-success/10" },
  conforme_reserves: { text: "Conforme avec réserves", class: "text-warning", bg: "bg-warning/10" },
  non_conforme: { text: "Non conforme", class: "text-destructive", bg: "bg-destructive/10" },
};

const riskLevelColors: Record<string, { text: string; bg: string }> = {
  "Très élevé": { text: "text-destructive", bg: "bg-destructive/10" },
  "Élevé": { text: "text-orange-500", bg: "bg-orange-500/10" },
  "Moyen": { text: "text-warning", bg: "bg-warning/10" },
  "Faible": { text: "text-success", bg: "bg-success/10" },
};

interface RightPanelProps {
  projectDescription?: string;
  sector?: string;
  capital?: number;
  typeSociete?: string;
}

export const RightPanel = ({ projectDescription, sector, capital, typeSociete }: RightPanelProps) => {
  const [conformite, setConformite] = useState<ConformiteData | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedCriterion, setSelectedCriterion] = useState<Criterion | null>(null);
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [showRiskDetails, setShowRiskDetails] = useState(false);

  const fetchConformite = useCallback(async () => {
    if (!projectDescription || !sector) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/conformite/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_description: projectDescription,
          sector: sector,
          capital: capital || null,
          type_societe: typeSociete || "SUARL",
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setConformite(data);
      }
    } catch (error) {
      console.error("Error fetching conformite:", error);
      // Use default data
      setConformite({
        score_global: 65,
        status: "conforme_reserves",
        criteres: [
          { label: "Capital social constitué", score: 50, status: "warning", article: "Art. 92-100", article_source: "Code des Sociétés Commerciales", details: "Capital non spécifié", category: "Structure juridique", recommendation: "Définir capital social minimum" },
          { label: "Éligibilité label Startup", score: 60, status: "warning", article: "Art. 3", article_source: "Loi n° 2018-20 (Startup Act)", details: "Potentiel d'innovation: 1 indicateurs détectés", category: "Startup Act", recommendation: "Renforcer aspect innovation" },
          { label: "Protection des données", score: 70, status: "check", article: "Art. 7-12", article_source: "Loi organique n° 2004-63", details: "Obligations standard de protection des données", category: "Protection des données" },
          { label: "Autorisation BCT", score: 100, status: "check", article: "Art. 34", article_source: "Loi n° 2016-48 + Circulaire BCT", details: "Pas d'autorisation BCT requise", category: "Réglementation BCT" },
          { label: "Mentions légales CGU/CGV", score: 75, status: "warning", article: "Art. 15", article_source: "Loi n° 2000-83 (commerce électronique)", details: "CGU/CGV à rédiger selon les mentions obligatoires", category: "Commerce électronique", recommendation: "Rédiger CGU/CGV conformes" },
        ],
        risk_profile: {
          niveau: "Moyen",
          autorisations_requises: ["Label Startup Act"],
          capital_recommande: 1000,
          delai_conformite: "1-3 mois"
        },
        recommendations: ["Définir capital social minimum", "Renforcer aspect innovation", "Rédiger CGU/CGV conformes"],
        lois_applicables: ["Loi n° 2018-20 (Startup Act)", "Loi organique n° 2004-63"]
      });
    } finally {
      setLoading(false);
    }
  }, [projectDescription, sector, capital, typeSociete]);

  const fetchGraph = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/graph/`);
      if (response.ok) {
        const data = await response.json();
        setGraphData(data);
      }
    } catch (error) {
      // Use default graph
      setGraphData({
        nodes: [
          { id: "loi_2018_20", label: "Startup Act", type: "loi" },
          { id: "art_3", label: "Conditions", type: "article" },
          { id: "art_13", label: "Avantages", type: "article" },
          { id: "decret", label: "Décret 2018-840", type: "loi" },
          { id: "bct", label: "Circulaire BCT", type: "loi" },
        ],
        edges: [
          { source: "loi_2018_20", target: "art_3", relation: "CONTIENT" },
          { source: "loi_2018_20", target: "art_13", relation: "CONTIENT" },
          { source: "decret", target: "loi_2018_20", relation: "APPLIQUE" },
          { source: "bct", target: "loi_2018_20", relation: "REFERENCE" },
        ],
      });
    }
  }, []);

  useEffect(() => {
    fetchConformite();
    fetchGraph();
  }, [fetchConformite, fetchGraph]);

  const score = conformite?.score_global ?? 0;
  const statusInfo = statusLabels[conformite?.status ?? "conforme_reserves"];
  const riskInfo = riskLevelColors[conformite?.risk_profile?.niveau ?? "Moyen"];

  // Group criteria by category
  const groupedCriteria = (conformite?.criteres ?? []).reduce((acc, c) => {
    const cat = c.category || "Général";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(c);
    return acc;
  }, {} as Record<string, Criterion[]>);

  // Calculate node positions for graph
  const getNodePosition = (index: number, total: number) => {
    const centerX = 120;
    const centerY = 50;
    const radius = 40;
    const angle = (index / total) * 2 * Math.PI - Math.PI / 2;
    return {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  };

  // Progress ring for score
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="w-[320px] shrink-0 flex flex-col h-full overflow-y-auto">
      <div className="p-4">
        {/* Enhanced Score Display */}
        <div className="flex items-start gap-4 mb-4">
          <div className="relative">
            <svg width="100" height="100" className="transform -rotate-90">
              <circle
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke="hsl(220 13% 91%)"
                strokeWidth="8"
              />
              <circle
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke={score >= 75 ? "hsl(142 76% 36%)" : score >= 50 ? "hsl(45 93% 47%)" : "hsl(0 84% 60%)"}
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                className="transition-all duration-700"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-bold text-foreground">{score}</span>
              <span className="text-xs text-muted-foreground">/100</span>
            </div>
          </div>
          <div className="flex-1 pt-2">
            <p className={`text-base font-semibold ${statusInfo.class}`}>{statusInfo.text}</p>
            <div className="flex items-center gap-1.5 mt-2">
              <button
                onClick={fetchConformite}
                disabled={loading}
                className="p-1.5 hover:bg-surface rounded-md transition-colors"
                title="Actualiser l'analyse"
              >
                <RefreshCw size={14} className={`text-muted-foreground ${loading ? "animate-spin" : ""}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Risk Profile Card */}
        {conformite?.risk_profile && (
          <div 
            className={`rounded-lg p-3 mb-4 cursor-pointer transition-all ${riskInfo?.bg || "bg-surface"}`}
            onClick={() => setShowRiskDetails(!showRiskDetails)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Shield size={16} className={riskInfo?.text || "text-muted-foreground"} />
                <span className="text-sm font-medium">Profil de risque</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-sm font-semibold ${riskInfo?.text}`}>
                  {conformite.risk_profile.niveau}
                </span>
                {showRiskDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </div>
            </div>
            
            {showRiskDetails && (
              <div className="mt-3 pt-3 border-t border-border/50 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <Scale size={12} /> Capital recommandé
                  </span>
                  <span className="font-medium">{conformite.risk_profile.capital_recommande.toLocaleString()} TND</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <Clock size={12} /> Délai conformité
                  </span>
                  <span className="font-medium">{conformite.risk_profile.delai_conformite}</span>
                </div>
                {conformite.risk_profile.autorisations_requises.length > 0 && (
                  <div className="text-xs">
                    <span className="text-muted-foreground">Autorisations requises:</span>
                    <ul className="mt-1 space-y-1">
                      {conformite.risk_profile.autorisations_requises.map((auth, i) => (
                        <li key={i} className="flex items-center gap-1">
                          <span className="w-1 h-1 rounded-full bg-primary" />
                          <span className="text-foreground">{auth}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Recommendations Section */}
        {conformite?.recommendations && conformite.recommendations.length > 0 && (
          <div 
            className="rounded-lg p-3 mb-4 bg-primary/5 cursor-pointer transition-all"
            onClick={() => setShowRecommendations(!showRecommendations)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Lightbulb size={16} className="text-primary" />
                <span className="text-sm font-medium">Recommandations</span>
                <span className="text-xs bg-primary/20 text-primary px-1.5 py-0.5 rounded-full">
                  {conformite.recommendations.length}
                </span>
              </div>
              {showRecommendations ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </div>
            
            {showRecommendations && (
              <ul className="mt-3 space-y-2">
                {conformite.recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs">
                    <span className="text-primary mt-0.5">→</span>
                    <span className="text-foreground">{rec}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Divider */}
        <div className="border-t border-border my-4" />

        {/* Criteria by Category */}
        <p className="text-label uppercase tracking-wider text-muted-foreground mb-3">
          Critères d'évaluation
        </p>
        
        {Object.entries(groupedCriteria).map(([category, criteria]) => (
          <div key={category} className="mb-4">
            <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-primary/50" />
              {category}
            </p>
            <div className="flex flex-col pl-2 border-l-2 border-border">
              {criteria.map((c) => (
                <div key={c.label}>
                  <div
                    className="flex items-center gap-2 py-2 hover:bg-surface-hover rounded-md px-2 transition-colors group cursor-pointer"
                    onClick={() => setSelectedCriterion(selectedCriterion?.label === c.label ? null : c)}
                  >
                    <CriterionIcon type={c.status} />
                    <span className="text-sm text-foreground flex-1 truncate">{c.label}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-12 h-1.5 bg-surface rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            c.score >= 80 ? "bg-success" : c.score >= 50 ? "bg-warning" : "bg-destructive"
                          }`}
                          style={{ width: `${c.score}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-score-mono w-6 text-right">{c.score}</span>
                    </div>
                  </div>
                  
                  {/* Expanded criterion details */}
                  {selectedCriterion?.label === c.label && (
                    <div className="ml-2 mb-2 p-2.5 bg-surface rounded-lg text-xs animate-in slide-in-from-top-2">
                      <p className="text-foreground font-medium mb-2">{c.details}</p>
                      <div className="flex items-center gap-1 text-primary mb-2">
                        <ExternalLink size={10} />
                        <span>{c.article} - {c.article_source}</span>
                      </div>
                      {c.recommendation && (
                        <div className="flex items-start gap-1.5 mt-2 pt-2 border-t border-border">
                          <Lightbulb size={12} className="text-warning mt-0.5" />
                          <span className="text-muted-foreground">{c.recommendation}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Applicable Laws */}
        {conformite?.lois_applicables && conformite.lois_applicables.length > 0 && (
          <>
            <div className="border-t border-border my-4" />
            <p className="text-label uppercase tracking-wider text-muted-foreground mb-2">
              Lois applicables
            </p>
            <div className="flex flex-wrap gap-1.5 mb-4">
              {conformite.lois_applicables.map((loi, i) => (
                <span key={i} className="text-xs bg-surface px-2 py-1 rounded-md text-muted-foreground">
                  {loi}
                </span>
              ))}
            </div>
          </>
        )}

        {/* Divider */}
        <div className="border-t border-border my-4" />

        {/* Documents */}
        <p className="text-label uppercase tracking-wider text-muted-foreground mb-3">
          Documents
        </p>
        <div className="flex flex-col">
          {documents.map((d) => (
            <div
              key={d.name}
              className="flex items-center gap-2.5 py-2 hover:bg-surface-hover rounded-md px-1 transition-colors cursor-pointer"
            >
              <d.icon size={14} className="text-muted-foreground" />
              <span className="text-base text-foreground flex-1">{d.name}</span>
              <Download size={13} className="text-muted-foreground" />
            </div>
          ))}
        </div>

        {/* Divider */}
        <div className="border-t border-border my-4" />

        {/* Graph */}
        <p className="text-label uppercase tracking-wider text-muted-foreground mb-3">
          Graphe de relations
        </p>
        <div className="border border-border rounded-lg p-4 mb-3">
          <svg viewBox="0 0 240 100" className="w-full h-auto">
            {/* Render edges */}
            {graphData?.edges.map((edge, i) => {
              const sourceNode = graphData.nodes.findIndex((n) => n.id === edge.source);
              const targetNode = graphData.nodes.findIndex((n) => n.id === edge.target);
              if (sourceNode === -1 || targetNode === -1) return null;
              const source = getNodePosition(sourceNode, graphData.nodes.length);
              const target = getNodePosition(targetNode, graphData.nodes.length);
              return (
                <line
                  key={i}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke="hsl(220 13% 91%)"
                  strokeWidth="1"
                />
              );
            })}
            {/* Render nodes */}
            {graphData?.nodes.map((node, i) => {
              const pos = getNodePosition(i, graphData.nodes.length);
              const isLoi = node.type === "loi";
              return (
                <g key={node.id}>
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={isLoi ? 5 : 3.5}
                    fill={isLoi ? "hsl(224 76% 53%)" : "hsl(220 9% 46%)"}
                  />
                  <title>{node.label}</title>
                </g>
              );
            })}
          </svg>
        </div>
        <button className="flex items-center gap-1 text-base text-primary hover:underline">
          Explorer <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
};

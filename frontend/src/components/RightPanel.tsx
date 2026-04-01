import { useEffect, useState, useCallback } from "react";
import { Check, AlertTriangle, X, FileText, ClipboardList, PenLine, Download, ArrowRight, RefreshCw, ExternalLink } from "lucide-react";

const API_BASE = "http://localhost:8000/api";

interface Criterion {
  label: string;
  score: number;
  status: "check" | "warning" | "x";
  article: string;
  article_source: string;
  details: string;
}

interface ConformiteData {
  score_global: number;
  status: "conforme" | "conforme_reserves" | "non_conforme";
  criteres: Criterion[];
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

const statusLabels: Record<string, { text: string; class: string }> = {
  conforme: { text: "Conforme", class: "text-success" },
  conforme_reserves: { text: "Conforme avec réserves", class: "text-warning" },
  non_conforme: { text: "Non conforme", class: "text-destructive" },
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
          { label: "Capital social constitué", score: 50, status: "warning", article: "Art. 92-100", article_source: "Code des Sociétés Commerciales", details: "Capital non spécifié" },
          { label: "Éligibilité label Startup", score: 60, status: "warning", article: "Art. 3", article_source: "Loi n° 2018-20 (Startup Act)", details: "Potentiel d'innovation: 1 indicateurs détectés" },
          { label: "Protection des données", score: 70, status: "check", article: "Art. 7-12", article_source: "Loi organique n° 2004-63", details: "Obligations standard de protection des données" },
          { label: "Autorisation BCT", score: 100, status: "check", article: "Art. 34", article_source: "Loi n° 2016-48 + Circulaire BCT", details: "Pas d'autorisation BCT requise" },
          { label: "Mentions légales CGU/CGV", score: 75, status: "warning", article: "Art. 15", article_source: "Loi n° 2000-83 (commerce électronique)", details: "CGU/CGV à rédiger selon les mentions obligatoires" },
        ],
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
  return (
    <div className="w-[320px] shrink-0 flex flex-col h-full overflow-y-auto">
      <div className="p-4">
        {/* Score */}
        <div className="flex items-center justify-between mb-1">
          <div>
            <span className="text-score font-medium text-foreground">{score}</span>
            <span className="text-title text-score-mono ml-1">/100</span>
          </div>
          <button
            onClick={fetchConformite}
            disabled={loading}
            className="p-1.5 hover:bg-surface rounded-md transition-colors"
            title="Actualiser"
          >
            <RefreshCw size={14} className={`text-muted-foreground ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
        <p className={`text-base font-medium ${statusInfo.class}`}>{statusInfo.text}</p>

        {/* Divider */}
        <div className="border-t border-border my-4" />

        {/* Criteria */}
        <p className="text-label uppercase tracking-wider text-muted-foreground mb-3">
          Critères
        </p>
        <div className="flex flex-col">
          {(conformite?.criteres ?? []).map((c) => (
            <div
              key={c.label}
              className="flex items-center gap-2 py-2 hover:bg-surface-hover rounded-md px-1 transition-colors group cursor-pointer"
              onClick={() => setSelectedCriterion(selectedCriterion?.label === c.label ? null : c)}
            >
              <CriterionIcon type={c.status} />
              <span className="text-base text-foreground flex-1 truncate">{c.label}</span>
              <span className="text-label font-mono text-score-mono">{c.score}</span>
              <span className="text-label text-primary opacity-0 group-hover:opacity-100 transition-opacity ml-1 flex items-center gap-0.5">
                {c.article} <ExternalLink size={10} />
              </span>
            </div>
          ))}
        </div>

        {/* Selected criterion details */}
        {selectedCriterion && (
          <div className="mt-2 p-2.5 bg-surface rounded-lg text-sm">
            <p className="text-foreground font-medium mb-1">{selectedCriterion.label}</p>
            <p className="text-muted-foreground text-xs mb-1">{selectedCriterion.details}</p>
            <p className="text-primary text-xs">
              📖 {selectedCriterion.article} - {selectedCriterion.article_source}
            </p>
          </div>
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

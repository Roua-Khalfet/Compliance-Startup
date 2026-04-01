import { useState, useEffect, useCallback } from "react";
import { Upload, ArrowRight, Sparkles, RefreshCw } from "lucide-react";

const sectors = ["Fintech", "EdTech", "HealthTech", "E-commerce", "SaaS"];
const API_BASE = "http://localhost:8000/api";

const defaultSuggestions = [
  "Besoin d'autorisation BCT ?",
  "Clauses RGPD obligatoires ?",
  "Capital minimum requis ?",
  "Type de société adapté ?",
];

interface LeftPanelProps {
  onSuggestionClick: (text: string) => void;
  onProjectChange?: (description: string, sector: string) => void;
}

export const LeftPanel = ({ onSuggestionClick, onProjectChange }: LeftPanelProps) => {
  const [selected, setSelected] = useState("Fintech");
  const [projectDescription, setProjectDescription] = useState(
    "Application de paiement mobile permettant aux utilisateurs d'envoyer et recevoir de l'argent, avec intégration bancaire locale."
  );
  const [suggestions, setSuggestions] = useState<string[]>(defaultSuggestions);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);

  const fetchSuggestions = useCallback(async () => {
    if (!projectDescription.trim()) return;
    
    setLoadingSuggestions(true);
    try {
      const response = await fetch(`${API_BASE}/suggestions/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_description: projectDescription,
          sector: selected,
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setSuggestions(data.questions);
      }
    } catch (error) {
      console.error("Error fetching suggestions:", error);
      // Keep default suggestions on error
    } finally {
      setLoadingSuggestions(false);
    }
  }, [projectDescription, selected]);

  // Notify parent of project changes
  useEffect(() => {
    onProjectChange?.(projectDescription, selected);
  }, [projectDescription, selected, onProjectChange]);

  // Auto-fetch suggestions when sector changes
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchSuggestions();
    }, 500);
    return () => clearTimeout(timer);
  }, [selected]);

  return (
    <div className="w-[280px] shrink-0 border-r border-border flex flex-col h-full overflow-y-auto">
      <div className="p-4">
        {/* Logo */}
        <div className="flex items-center gap-2 mb-8">
          <div className="w-2.5 h-2.5 rounded-full bg-primary" />
          <span className="text-title font-medium text-foreground">ComplianceGuard</span>
        </div>

        {/* Section title */}
        <p className="text-label uppercase tracking-wider text-muted-foreground mb-3">
          Votre projet
        </p>

        {/* Textarea */}
        <textarea
          className="w-full bg-surface rounded-lg p-3 text-base text-foreground placeholder:text-muted-foreground resize-none border-0 outline-none focus:ring-1 focus:ring-primary/30 min-h-[80px]"
          placeholder="Décrivez votre projet en quelques lignes..."
          value={projectDescription}
          onChange={(e) => setProjectDescription(e.target.value)}
          onBlur={fetchSuggestions}
        />

        {/* Sector tags */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {sectors.map((s) => (
            <button
              key={s}
              onClick={() => setSelected(s)}
              className={`px-2.5 py-1 rounded-full text-label transition-colors ${
                selected === s
                  ? "bg-primary text-primary-foreground"
                  : "border border-border text-muted-foreground hover:bg-surface-hover"
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Upload zone */}
        <div className="mt-4 border border-dashed border-border rounded-lg p-6 flex flex-col items-center gap-2 cursor-pointer hover:bg-surface-hover transition-colors">
          <Upload size={18} className="text-muted-foreground" />
          <span className="text-label text-muted-foreground text-center">
            Glissez vos documents ici
            <br />
            <span className="text-label text-muted-foreground/60">(optionnel)</span>
          </span>
        </div>

        {/* Divider */}
        <div className="border-t border-border my-5" />

        {/* Suggestions */}
        <div className="flex items-center justify-between mb-3">
          <p className="text-label uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <Sparkles size={12} /> Suggestions
          </p>
          <button
            onClick={fetchSuggestions}
            disabled={loadingSuggestions}
            className="p-1 hover:bg-surface rounded transition-colors"
            title="Générer des suggestions"
          >
            <RefreshCw size={12} className={`text-muted-foreground ${loadingSuggestions ? "animate-spin" : ""}`} />
          </button>
        </div>
        <div className="flex flex-col gap-2">
          {suggestions.map((q, i) => (
            <button
              key={i}
              onClick={() => onSuggestionClick(q)}
              className="text-left px-3 py-2 rounded-lg border border-border text-base text-foreground hover:bg-surface-hover transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

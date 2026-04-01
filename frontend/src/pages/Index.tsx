import { useState, useCallback } from "react";
import { LeftPanel } from "@/components/LeftPanel";
import { CenterPanel } from "@/components/CenterPanel";
import { RightPanel } from "@/components/RightPanel";

const Index = () => {
  const [pendingSuggestion, setPendingSuggestion] = useState<string | null>(null);
  const [projectDescription, setProjectDescription] = useState("");
  const [sector, setSector] = useState("Fintech");

  const handleProjectChange = useCallback((description: string, newSector: string) => {
    setProjectDescription(description);
    setSector(newSector);
  }, []);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      <LeftPanel 
        onSuggestionClick={(text) => setPendingSuggestion(text)}
        onProjectChange={handleProjectChange}
      />
      <CenterPanel
        onSendFromSuggestion={pendingSuggestion}
        onSuggestionHandled={() => setPendingSuggestion(null)}
        projectContext={projectDescription}
        sector={sector}
      />
      <RightPanel 
        projectDescription={projectDescription}
        sector={sector}
      />
    </div>
  );
};

export default Index;

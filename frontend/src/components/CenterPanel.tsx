import { useState, useRef, useEffect } from "react";
import { Send, Database, Globe } from "lucide-react";
import ReactMarkdown from "react-markdown";

type Message = { 
  role: "user" | "assistant"; 
  content: string;
  sourceType?: "GraphRAG" | "Web" | "system" | "error";
  sources?: string[];
};

const API_BASE = "http://localhost:8000/api";

const DEFAULT_RESPONSE = `Je suis votre assistant juridique spécialisé dans la **législation tunisienne**. Je peux vous aider avec :

- Conformité réglementaire
- Choix de forme juridique
- Protection des données (Loi 2004-63)
- Réglementation BCT pour les Fintech
- Startup Act et avantages fiscaux
- Code des Sociétés Commerciales

Posez-moi votre question !`;

interface CenterPanelProps {
  onSendFromSuggestion?: string | null;
  onSuggestionHandled?: () => void;
  projectContext?: string;
  sector?: string;
}

export const CenterPanel = ({ onSendFromSuggestion, onSuggestionHandled, projectContext, sector }: CenterPanelProps) => {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: DEFAULT_RESPONSE, sourceType: "system" },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  useEffect(() => {
    if (onSendFromSuggestion) {
      handleSend(onSendFromSuggestion);
      onSuggestionHandled?.();
    }
  }, [onSendFromSuggestion]);

  const handleSend = async (text?: string) => {
    const msg = text || input.trim();
    if (!msg) return;
    setInput("");

    const userMsg: Message = { role: "user", content: msg };
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    try {
      const response = await fetch(`${API_BASE}/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msg,
          project_context: projectContext || "",
          sector: sector || "",
        }),
      });

      if (!response.ok) throw new Error("API error");

      const data = await response.json();
      
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response,
          sourceType: data.source_type as Message["sourceType"],
          sources: data.sources,
        },
      ]);
    } catch (error) {
      // Fallback to mock response if API fails
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Concernant votre question sur "${msg}", voici ce que prévoit la législation tunisienne :\n\n⚠️ **Mode hors ligne** - Le serveur Django n'est pas disponible.\n\nLancez le backend avec:\n\`\`\`bash\ncd backend && python manage.py runserver\n\`\`\``,
          sourceType: "error",
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex-1 border-r border-border flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-success" />
          <h1 className="text-title font-medium text-foreground">Assistant Juridique</h1>
          <span className="text-label text-muted-foreground ml-1">Lois tunisiennes</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-lg px-3.5 py-2.5 text-base ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-surface text-foreground"
              }`}
            >
              {msg.role === "assistant" ? (
                <div>
                  <div className="prose prose-sm prose-slate max-w-none [&_h2]:text-title [&_h2]:font-medium [&_h2]:mb-2 [&_h2]:mt-0 [&_h3]:text-base [&_h3]:font-medium [&_h3]:mb-1 [&_p]:text-base [&_p]:mb-2 [&_p]:last:mb-0 [&_li]:text-base [&_blockquote]:text-label [&_blockquote]:border-l-warning [&_blockquote]:bg-background [&_blockquote]:px-3 [&_blockquote]:py-1.5 [&_blockquote]:rounded-r [&_table]:text-label [&_th]:px-2 [&_td]:px-2 [&_code]:text-label [&_code]:bg-background [&_code]:px-1 [&_code]:rounded [&_strong]:text-foreground">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                  {msg.sourceType && msg.sourceType !== "system" && (
                    <div className="mt-2 pt-2 border-t border-border/50 flex items-center gap-1.5 text-xs text-muted-foreground">
                      {msg.sourceType === "GraphRAG" ? (
                        <><Database size={12} /> Source: Base juridique locale</>
                      ) : msg.sourceType === "Web" ? (
                        <><Globe size={12} /> Source: Recherche Web</>
                      ) : msg.sourceType === "error" ? (
                        <span className="text-destructive">⚠️ Mode hors ligne</span>
                      ) : null}
                    </div>
                  )}
                </div>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-surface rounded-lg px-3.5 py-2.5">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-border shrink-0">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Posez votre question juridique..."
            className="flex-1 bg-surface rounded-lg px-3 py-2.5 text-base text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-primary/30 border-0"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isTyping}
            className="bg-primary text-primary-foreground rounded-lg px-3 py-2.5 hover:opacity-90 transition-opacity disabled:opacity-40"
          >
            <Send size={15} />
          </button>
        </div>
      </div>
    </div>
  );
};

'use client'

import { useState } from 'react'
import { FileText, Download, Loader2, Sparkles, Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { generateDocuments, type DocumentResult } from '@/lib/api'

const DOC_TYPES = [
  { id: 'statuts', label: 'Statuts de Société', icon: '📜', desc: 'SARL, SA, SUARL — Code des Sociétés', color: 'from-violet-500 to-purple-600' },
  { id: 'cgu', label: 'CGU / CGV', icon: '📋', desc: 'Conditions Générales — Loi 2004-63', color: 'from-fuchsia-500 to-pink-600' },
  { id: 'contrat_investissement', label: 'Contrat Investissement', icon: '💰', desc: 'Convention — Startup Act Art. 13+', color: 'from-amber-500 to-orange-600' },
  { id: 'demande_label', label: 'Demande Label Startup', icon: '🏷️', desc: 'Formulaire — Décret 2018-840', color: 'from-emerald-500 to-teal-600' },
  { id: 'all', label: 'Pack Complet', icon: '📦', desc: 'Tous les documents ci-dessus', color: 'from-indigo-500 to-violet-600' },
]

const SOCIETE_TYPES = ['SUARL', 'SARL', 'SA', 'SAS']

export default function DocumentsSection() {
  const [nom, setNom] = useState('')
  const [activite, setActivite] = useState('')
  const [fondateurs, setFondateurs] = useState<string[]>([''])
  const [capital, setCapital] = useState('1000')
  const [siege, setSiege] = useState('Tunis')
  const [typeSociete, setTypeSociete] = useState('SUARL')
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null)
  const [results, setResults] = useState<DocumentResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [activePreview, setActivePreview] = useState<string | null>(null)

  const handleGenerate = async () => {
    if (!nom.trim() || !activite.trim() || !selectedDoc) return
    setIsLoading(true)
    setError('')
    setResults([])
    try {
      const docs = await generateDocuments({
        doc_type: selectedDoc, nom_startup: nom, activite,
        fondateurs: fondateurs.filter(f => f.trim()),
        capital_social: parseInt(capital) || 1000,
        siege_social: siege, type_societe: typeSociete,
      })
      setResults(docs)
      if (docs.length > 0) setActivePreview(docs[0].doc_type)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur génération')
    } finally {
      setIsLoading(false)
    }
  }

  const downloadDoc = (doc: DocumentResult) => {
    const blob = new Blob([doc.content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = doc.filename; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border bg-gradient-to-r from-violet-500/5 via-fuchsia-500/5 to-transparent">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground">Générateur de Documents</h2>
            <p className="text-xs text-muted-foreground">Statuts, CGU, contrats — conformes au droit tunisien</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Document type selection */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {DOC_TYPES.map((dt) => (
            <button key={dt.id} onClick={() => setSelectedDoc(dt.id)}
              className={`text-left p-4 rounded-xl border-2 transition-all duration-200 group ${
                selectedDoc === dt.id ? 'border-violet-400 bg-violet-50/50 shadow-md shadow-violet-500/10' : 'border-border hover:border-violet-300 hover:bg-violet-50/30'
              }`}>
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{dt.icon}</span>
                <span className="text-sm font-semibold text-foreground">{dt.label}</span>
              </div>
              <p className="text-[11px] text-muted-foreground">{dt.desc}</p>
            </button>
          ))}
        </div>

        {/* Form */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-5 rounded-2xl border border-border bg-card">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Nom de la Startup *</label>
            <Input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Ex : TechInnovate" className="rounded-lg" />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Activité *</label>
            <Input value={activite} onChange={(e) => setActivite(e.target.value)} placeholder="Ex : Plateforme SaaS pour PME" className="rounded-lg" />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Capital Social (TND)</label>
            <Input type="number" value={capital} onChange={(e) => setCapital(e.target.value)} className="rounded-lg" />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Type de Société</label>
            <div className="flex gap-2">
              {SOCIETE_TYPES.map((t) => (
                <button key={t} onClick={() => setTypeSociete(t)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    typeSociete === t ? 'bg-violet-500 text-white' : 'bg-secondary text-secondary-foreground hover:bg-violet-100'
                  }`}>{t}</button>
              ))}
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Siège Social</label>
            <Input value={siege} onChange={(e) => setSiege(e.target.value)} className="rounded-lg" />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Fondateurs</label>
            <div className="space-y-1.5">
              {fondateurs.map((f, i) => (
                <div key={i} className="flex gap-1.5">
                  <Input value={f} onChange={(e) => { const u = [...fondateurs]; u[i] = e.target.value; setFondateurs(u) }}
                    placeholder={`Fondateur ${i + 1}`} className="rounded-lg text-xs" />
                  {fondateurs.length > 1 && (
                    <Button variant="ghost" size="icon" className="h-9 w-9" onClick={() => setFondateurs(fondateurs.filter((_, j) => j !== i))}>
                      <X className="w-3 h-3" />
                    </Button>
                  )}
                </div>
              ))}
              <Button variant="ghost" size="sm" className="text-xs gap-1 text-violet-500" onClick={() => setFondateurs([...fondateurs, ''])}>
                <Plus className="w-3 h-3" /> Ajouter
              </Button>
            </div>
          </div>
        </div>

        {/* Generate button */}
        <Button onClick={handleGenerate} disabled={!nom.trim() || !activite.trim() || !selectedDoc || isLoading}
          className="w-full py-6 rounded-xl text-sm font-semibold bg-gradient-to-r from-violet-500 to-fuchsia-600 hover:from-violet-600 hover:to-fuchsia-700 shadow-lg shadow-violet-500/20 gap-2">
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {isLoading ? 'Génération en cours...' : 'Générer les documents'}
        </Button>

        {error && <div className="p-3 rounded-xl bg-red-50 text-red-600 text-xs border border-red-200">{error}</div>}

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-3">
            <div className="flex gap-2 flex-wrap">
              {results.map((doc) => (
                <button key={doc.doc_type} onClick={() => setActivePreview(doc.doc_type)}
                  className={`px-4 py-2 rounded-lg text-xs font-medium transition-colors ${
                    activePreview === doc.doc_type ? 'bg-violet-500 text-white' : 'bg-secondary hover:bg-violet-100'
                  }`}>{doc.doc_type}</button>
              ))}
            </div>
            {results.filter(d => d.doc_type === activePreview).map((doc) => (
              <div key={doc.doc_type} className="rounded-2xl border border-border bg-card overflow-hidden">
                <div className="flex justify-between items-center px-4 py-2 bg-secondary/50 border-b border-border">
                  <span className="text-xs font-semibold text-foreground">{doc.filename}</span>
                  <Button variant="ghost" size="sm" className="text-xs gap-1" onClick={() => downloadDoc(doc)}>
                    <Download className="w-3 h-3" /> Télécharger
                  </Button>
                </div>
                <pre className="p-4 text-xs leading-relaxed overflow-x-auto max-h-[400px] overflow-y-auto whitespace-pre-wrap font-mono text-foreground/80">{doc.content}</pre>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

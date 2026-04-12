'use client'

import { useState } from 'react'
import { ShieldCheck, Loader2, AlertTriangle, CheckCircle2, XCircle, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { analyzeConformite, type ConformiteResult } from '@/lib/api'

const SECTORS = [
  { id: 'Fintech', label: 'Fintech', emoji: '💳', risk: 'élevé' },
  { id: 'HealthTech', label: 'HealthTech', emoji: '🏥', risk: 'élevé' },
  { id: 'EdTech', label: 'EdTech', emoji: '📚', risk: 'moyen' },
  { id: 'E-commerce', label: 'E-commerce', emoji: '🛒', risk: 'moyen' },
  { id: 'SaaS', label: 'SaaS', emoji: '☁️', risk: 'faible' },
]

function ScoreGauge({ score }: { score: number }) {
  const circumference = 283
  const offset = circumference - (score / 100) * circumference
  const color = score >= 75 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444'
  return (
    <div className="relative w-40 h-40 mx-auto">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="6" className="text-border" />
        <circle cx="50" cy="50" r="45" fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1.5s ease-out', animation: 'score-fill 1.5s ease-out' }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-black" style={{ color }}>{score}</span>
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">/ 100</span>
      </div>
    </div>
  )
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'check') return <CheckCircle2 className="w-5 h-5 text-emerald-500" />
  if (status === 'warning') return <AlertTriangle className="w-5 h-5 text-amber-500" />
  return <XCircle className="w-5 h-5 text-red-500" />
}

export default function ConformiteSection() {
  const [description, setDescription] = useState('')
  const [sector, setSector] = useState('SaaS')
  const [capital, setCapital] = useState('')
  const [typeSociete, setTypeSociete] = useState('SUARL')
  const [result, setResult] = useState<ConformiteResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleAnalyze = async () => {
    if (!description.trim()) return
    setIsLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await analyzeConformite({
        project_description: description, sector,
        capital: capital ? parseInt(capital) : null,
        type_societe: typeSociete,
      })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur analyse')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border bg-gradient-to-r from-emerald-500/5 via-teal-500/5 to-transparent">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground">Analyse de Conformité</h2>
            <p className="text-xs text-muted-foreground">Scoring pondéré par critère légal</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {!result ? (
          <>
            {/* Sector selection */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-foreground uppercase tracking-wider">Secteur d&apos;activité</label>
              <div className="grid grid-cols-5 gap-2">
                {SECTORS.map((s) => (
                  <button key={s.id} onClick={() => setSector(s.id)}
                    className={`p-3 rounded-xl border-2 text-center transition-all ${
                      sector === s.id ? 'border-emerald-400 bg-emerald-50/50 shadow-sm' : 'border-border hover:border-emerald-300'
                    }`}>
                    <span className="text-2xl block mb-1">{s.emoji}</span>
                    <span className="text-[11px] font-semibold block text-foreground">{s.label}</span>
                    <span className={`text-[9px] font-medium ${s.risk === 'élevé' ? 'text-red-500' : s.risk === 'moyen' ? 'text-amber-500' : 'text-emerald-500'}`}>
                      Risque {s.risk}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Project description */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">Description du projet *</label>
              <Textarea value={description} onChange={(e) => setDescription(e.target.value)}
                placeholder="Décrivez votre startup : activité, modèle économique, technologie utilisée, cible..."
                className="rounded-xl min-h-[100px]" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Capital prévu (TND)</label>
                <Input type="number" value={capital} onChange={(e) => setCapital(e.target.value)} placeholder="Ex : 10000" className="rounded-lg" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Type de société</label>
                <div className="flex gap-2">
                  {['SUARL', 'SARL', 'SA'].map((t) => (
                    <button key={t} onClick={() => setTypeSociete(t)}
                      className={`flex-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        typeSociete === t ? 'bg-emerald-500 text-white' : 'bg-secondary hover:bg-emerald-100'
                      }`}>{t}</button>
                  ))}
                </div>
              </div>
            </div>

            <Button onClick={handleAnalyze} disabled={!description.trim() || isLoading}
              className="w-full py-6 rounded-xl text-sm font-semibold bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-500/20 gap-2">
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
              {isLoading ? 'Analyse en cours...' : 'Analyser la conformité'}
            </Button>
            {error && <div className="p-3 rounded-xl bg-red-50 text-red-600 text-xs border border-red-200">{error}</div>}
          </>
        ) : (
          /* Results */
          <div className="space-y-6">
            <button onClick={() => setResult(null)} className="text-xs text-muted-foreground hover:text-foreground transition-colors">&larr; Nouvelle analyse</button>

            {/* Score */}
            <div className="text-center space-y-3">
              <ScoreGauge score={result.score_global} />
              <div className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold ${
                result.status === 'conforme' ? 'bg-emerald-100 text-emerald-700' :
                result.status === 'conforme_reserves' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'
              }`}>
                {result.status === 'conforme' ? '✓ Conforme' : result.status === 'conforme_reserves' ? '⚠ Conforme avec réserves' : '✗ Non conforme'}
              </div>
            </div>

            {/* Risk profile */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: 'Niveau de risque', value: result.risk_profile.niveau, color: result.risk_profile.niveau === 'élevé' ? 'text-red-500' : result.risk_profile.niveau === 'moyen' ? 'text-amber-500' : 'text-emerald-500' },
                { label: 'Capital recommandé', value: `${result.risk_profile.capital_recommande.toLocaleString()} TND`, color: 'text-foreground' },
                { label: 'Délai conformité', value: result.risk_profile.delai_conformite, color: 'text-foreground' },
                { label: 'Autorisations', value: result.risk_profile.autorisations_requises.length > 0 ? result.risk_profile.autorisations_requises.join(', ') : 'Aucune', color: 'text-foreground' },
              ].map((item, i) => (
                <div key={i} className="p-3 rounded-xl bg-secondary/50 border border-border">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">{item.label}</p>
                  <p className={`text-xs font-bold ${item.color}`}>{item.value}</p>
                </div>
              ))}
            </div>

            {/* Criteria */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">Critères détaillés</h3>
              {result.criteres.map((c, i) => (
                <div key={i} className="flex items-start gap-3 p-4 rounded-xl border border-border bg-card hover:shadow-sm transition-shadow">
                  <StatusIcon status={c.status} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-foreground">{c.label}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-secondary text-muted-foreground font-medium">{c.score}/100</span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-1">{c.details}</p>
                    <p className="text-[10px] text-muted-foreground/70">{c.article} — {c.article_source}</p>
                    {c.recommendation && (
                      <div className="flex items-center gap-1.5 mt-2 text-[11px] text-indigo-600 font-medium">
                        <ArrowRight className="w-3 h-3" /> {c.recommendation}
                      </div>
                    )}
                  </div>
                  {/* Score bar */}
                  <div className="w-16 flex-shrink-0">
                    <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                      <div className={`h-full rounded-full transition-all duration-1000 ${
                        c.score >= 75 ? 'bg-emerald-500' : c.score >= 50 ? 'bg-amber-500' : 'bg-red-500'
                      }`} style={{ width: `${c.score}%` }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Recommendations */}
            {result.recommendations.length > 0 && (
              <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 space-y-2">
                <h3 className="text-xs font-semibold text-emerald-800 uppercase tracking-wider">Recommandations prioritaires</h3>
                {result.recommendations.map((rec, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-emerald-700">
                    <span className="font-bold text-emerald-500">{i + 1}.</span> {rec}
                  </div>
                ))}
              </div>
            )}

            {/* Applicable laws */}
            <div className="flex flex-wrap gap-2">
              {result.lois_applicables.map((loi, i) => (
                <span key={i} className="px-3 py-1 rounded-full text-[10px] font-medium bg-indigo-50 text-indigo-600 border border-indigo-200">{loi}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

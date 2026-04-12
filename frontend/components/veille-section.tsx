'use client'

import { useState, useEffect } from 'react'
import { Radio, RefreshCcw, ExternalLink, CheckCircle2, Clock, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { fetchVeille, type VeilleResponse } from '@/lib/api'

function StatusBadge({ status }: { status: string }) {
  if (status === 'ok') return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-700"><CheckCircle2 className="w-3 h-3" /> OK</span>
  if (status === 'pending') return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-700"><Clock className="w-3 h-3" /> En attente</span>
  return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-100 text-red-700"><AlertCircle className="w-3 h-3" /> Changé</span>
}

export default function VeilleSection() {
  const [data, setData] = useState<VeilleResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const loadVeille = async () => {
    setIsLoading(true)
    setError('')
    try {
      const res = await fetchVeille()
      setData(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur chargement')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { loadVeille() }, [])

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border bg-gradient-to-r from-rose-500/5 via-pink-500/5 to-transparent">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-500 to-pink-600 flex items-center justify-center shadow-lg shadow-rose-500/20">
              <Radio className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-foreground">Veille Réglementaire</h2>
              <p className="text-xs text-muted-foreground">Surveillance des sites officiels tunisiens</p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={loadVeille} disabled={isLoading} className="gap-1.5 text-xs rounded-lg">
            <RefreshCcw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Actualiser
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {error && <div className="p-3 rounded-xl bg-red-50 text-red-600 text-xs border border-red-200">{error}</div>}

        {data && (
          <>
            {/* Last update */}
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock className="w-3.5 h-3.5" />
              Dernière mise à jour : {new Date(data.last_update).toLocaleString('fr-FR')}
            </div>

            {/* Sites list */}
            <div className="space-y-3">
              {data.items.map((item, i) => (
                <div key={i} className="p-5 rounded-2xl border border-border bg-card hover:shadow-md transition-shadow group">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2 flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <div className={`w-2.5 h-2.5 rounded-full ${
                          item.status === 'ok' ? 'bg-emerald-500' : item.status === 'pending' ? 'bg-amber-500 animate-pulse' : 'bg-red-500 animate-pulse'
                        }`} />
                        <h3 className="text-sm font-bold text-foreground">{item.nom}</h3>
                        <StatusBadge status={item.status} />
                      </div>
                      <a href={item.url} target="_blank" rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-xs text-indigo-500 hover:text-indigo-700 transition-colors truncate">
                        <ExternalLink className="w-3 h-3 flex-shrink-0" /> {item.url}
                      </a>
                      <p className="text-[11px] text-muted-foreground">
                        Dernier check : {new Date(item.last_check).toLocaleString('fr-FR')}
                      </p>
                    </div>
                    {item.has_changed && (
                      <div className="px-3 py-1.5 rounded-lg bg-rose-50 border border-rose-200 text-[11px] text-rose-600 font-semibold flex-shrink-0">
                        🔔 Changement détecté
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Info card */}
            <div className="p-4 rounded-2xl bg-gradient-to-r from-rose-50 to-pink-50 border border-rose-200 text-xs text-rose-700 space-y-1">
              <p className="font-semibold">Comment fonctionne la veille ?</p>
              <p className="text-rose-600/80">L&apos;agent scrape périodiquement les sites officiels, normalise le contenu et compare le hash SHA256 avec le cache local pour détecter tout changement réglementaire.</p>
            </div>
          </>
        )}

        {!data && !error && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
            <Radio className="w-12 h-12 text-rose-300 animate-pulse" />
            <p className="text-sm text-muted-foreground">Chargement de la veille...</p>
          </div>
        )}
      </div>
    </div>
  )
}

'use client'

import { useState, useEffect } from 'react'
import { Network, RefreshCcw, ZoomIn, ZoomOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { fetchGraph, type GraphData } from '@/lib/api'

const NODE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  loi: { bg: 'bg-indigo-100', border: 'border-indigo-400', text: 'text-indigo-700' },
  article: { bg: 'bg-violet-100', border: 'border-violet-400', text: 'text-violet-700' },
  decret: { bg: 'bg-fuchsia-100', border: 'border-fuchsia-400', text: 'text-fuchsia-700' },
  circulaire: { bg: 'bg-sky-100', border: 'border-sky-400', text: 'text-sky-700' },
  entite: { bg: 'bg-emerald-100', border: 'border-emerald-400', text: 'text-emerald-700' },
  concept: { bg: 'bg-amber-100', border: 'border-amber-400', text: 'text-amber-700' },
  organisme: { bg: 'bg-rose-100', border: 'border-rose-400', text: 'text-rose-700' },
  avantage: { bg: 'bg-teal-100', border: 'border-teal-400', text: 'text-teal-700' },
  obligation: { bg: 'bg-orange-100', border: 'border-orange-400', text: 'text-orange-700' },
  condition: { bg: 'bg-purple-100', border: 'border-purple-400', text: 'text-purple-700' },
  default: { bg: 'bg-gray-100', border: 'border-gray-400', text: 'text-gray-700' },
}

function getNodeColor(type: string) {
  return NODE_COLORS[type.toLowerCase()] || NODE_COLORS.default
}

const RELATION_COLORS: Record<string, string> = {
  CONTIENT: 'text-indigo-500',
  APPLIQUE: 'text-violet-500',
  REFERENCE: 'text-sky-500',
  DEFINIT: 'text-emerald-500',
  ETABLIT: 'text-amber-500',
  CONCERNE: 'text-rose-500',
  BENEFICIE: 'text-teal-500',
  MODIFIE: 'text-fuchsia-500',
  PREVOIT: 'text-orange-500',
}

export default function GraphSection() {
  const [data, setData] = useState<GraphData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)

  const loadGraph = async () => {
    setIsLoading(true)
    setError('')
    try {
      const res = await fetchGraph()
      setData(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur chargement')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { loadGraph() }, [])

  const connectedEdges = data?.edges.filter(e => e.source === selectedNode || e.target === selectedNode) || []
  const connectedNodeIds = new Set(connectedEdges.flatMap(e => [e.source, e.target]))

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border bg-gradient-to-r from-sky-500/5 via-cyan-500/5 to-transparent">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500 to-cyan-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <Network className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-foreground">Knowledge Graph</h2>
              <p className="text-xs text-muted-foreground">Relations entre lois, articles et entités</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" className="h-8 w-8 rounded-lg" onClick={() => setZoom(z => Math.max(0.5, z - 0.1))}>
              <ZoomOut className="w-3.5 h-3.5" />
            </Button>
            <span className="text-xs text-muted-foreground w-10 text-center">{Math.round(zoom * 100)}%</span>
            <Button variant="outline" size="icon" className="h-8 w-8 rounded-lg" onClick={() => setZoom(z => Math.min(2, z + 0.1))}>
              <ZoomIn className="w-3.5 h-3.5" />
            </Button>
            <Button variant="outline" size="sm" onClick={loadGraph} disabled={isLoading} className="gap-1.5 text-xs rounded-lg ml-2">
              <RefreshCcw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Recharger
            </Button>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Graph visualization */}
        <div className="flex-1 overflow-auto p-6">
          {error && <div className="p-3 rounded-xl bg-red-50 text-red-600 text-xs border border-red-200">{error}</div>}

          {data && (
            <div style={{ transform: `scale(${zoom})`, transformOrigin: 'top left', transition: 'transform 0.2s' }}>
              {/* Legend */}
              <div className="flex flex-wrap gap-2 mb-6">
                {Object.entries(NODE_COLORS).filter(([k]) => k !== 'default').map(([type, colors]) => (
                  <span key={type} className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold ${colors.bg} ${colors.text} border ${colors.border}`}>
                    <span className={`w-2 h-2 rounded-full ${colors.border} border-2`} />
                    {type}
                  </span>
                ))}
              </div>

              {/* Nodes grid */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {data.nodes.map((node) => {
                  const colors = getNodeColor(node.type)
                  const isSelected = selectedNode === node.id
                  const isConnected = selectedNode ? connectedNodeIds.has(node.id) : true
                  return (
                    <button key={node.id} onClick={() => setSelectedNode(isSelected ? null : node.id)}
                      className={`p-4 rounded-xl border-2 text-left transition-all duration-200 ${colors.bg} ${
                        isSelected ? `${colors.border} shadow-lg ring-2 ring-offset-1 ring-${colors.border}` :
                        !isConnected && selectedNode ? 'opacity-30' :
                        `${colors.border} border-opacity-30 hover:border-opacity-100 hover:shadow-md`
                      }`}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`w-2.5 h-2.5 rounded-full ${colors.border} border-2 flex-shrink-0`} />
                        <span className={`text-[10px] font-semibold uppercase tracking-wider ${colors.text} opacity-70`}>{node.type}</span>
                      </div>
                      <p className={`text-xs font-bold ${colors.text} truncate`}>{node.label}</p>
                    </button>
                  )
                })}
              </div>

              {/* Edges */}
              {connectedEdges.length > 0 && selectedNode && (
                <div className="mt-6 space-y-2">
                  <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">Relations connectées</h3>
                  {connectedEdges.map((edge, i) => {
                    const sourceNode = data.nodes.find(n => n.id === edge.source)
                    const targetNode = data.nodes.find(n => n.id === edge.target)
                    const relColor = RELATION_COLORS[edge.relation] || 'text-gray-500'
                    return (
                      <div key={i} className="flex items-center gap-2 p-3 rounded-xl bg-card border border-border text-xs">
                        <span className="font-semibold text-foreground truncate">{sourceNode?.label || edge.source}</span>
                        <span className={`px-2 py-0.5 rounded-full bg-secondary font-bold ${relColor}`}>— {edge.relation} →</span>
                        <span className="font-semibold text-foreground truncate">{targetNode?.label || edge.target}</span>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* All edges when no selection */}
              {!selectedNode && data.edges.length > 0 && (
                <div className="mt-6 space-y-2">
                  <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">Toutes les relations ({data.edges.length})</h3>
                  {data.edges.slice(0, 20).map((edge, i) => {
                    const sourceNode = data.nodes.find(n => n.id === edge.source)
                    const targetNode = data.nodes.find(n => n.id === edge.target)
                    const relColor = RELATION_COLORS[edge.relation] || 'text-gray-500'
                    return (
                      <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-secondary/30 text-xs">
                        <span className="font-medium text-foreground truncate">{sourceNode?.label || edge.source}</span>
                        <span className={`font-bold ${relColor} flex-shrink-0`}>{edge.relation}</span>
                        <span className="font-medium text-foreground truncate">{targetNode?.label || edge.target}</span>
                      </div>
                    )
                  })}
                  {data.edges.length > 20 && <p className="text-[10px] text-muted-foreground text-center">... et {data.edges.length - 20} autres relations</p>}
                </div>
              )}
            </div>
          )}

          {!data && !error && (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
              <Network className="w-12 h-12 text-sky-300 animate-pulse" />
              <p className="text-sm text-muted-foreground">Chargement du graphe...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

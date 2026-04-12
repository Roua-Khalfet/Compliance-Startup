'use client'

import { MessageSquare, FileText, ShieldCheck, Brain, Radio, Network, ChevronLeft, ChevronRight, Shield } from 'lucide-react'
import { cn } from '@/lib/utils'

export type SectionId = 'chat' | 'documents' | 'conformite' | 'quiz' | 'veille' | 'graph'

const NAV_ITEMS: { id: SectionId; label: string; icon: React.ElementType; color: string; gradient: string }[] = [
  { id: 'chat', label: 'Chat Juridique', icon: MessageSquare, color: 'text-indigo-500', gradient: 'from-indigo-500/20 to-violet-500/20' },
  { id: 'documents', label: 'Documents', icon: FileText, color: 'text-violet-500', gradient: 'from-violet-500/20 to-fuchsia-500/20' },
  { id: 'conformite', label: 'Conformité', icon: ShieldCheck, color: 'text-emerald-500', gradient: 'from-emerald-500/20 to-teal-500/20' },
  { id: 'quiz', label: 'Quiz Juridique', icon: Brain, color: 'text-amber-500', gradient: 'from-amber-500/20 to-orange-500/20' },
  { id: 'veille', label: 'Veille Réglementaire', icon: Radio, color: 'text-rose-500', gradient: 'from-rose-500/20 to-pink-500/20' },
  { id: 'graph', label: 'Graphe de Lois', icon: Network, color: 'text-sky-500', gradient: 'from-sky-500/20 to-cyan-500/20' },
]

interface AppSidebarProps {
  activeSection: SectionId
  onSectionChange: (id: SectionId) => void
  collapsed: boolean
  onToggleCollapse: () => void
}

export default function AppSidebar({ activeSection, onSectionChange, collapsed, onToggleCollapse }: AppSidebarProps) {
  return (
    <aside className={cn(
      'flex flex-col h-full border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-all duration-300 ease-in-out',
      collapsed ? 'w-[68px]' : 'w-[240px]'
    )}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-sidebar-border">
        <div className="flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/25">
          <Shield className="w-5 h-5 text-white" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <h1 className="text-sm font-bold tracking-tight text-sidebar-foreground truncate">ComplianceGuard</h1>
            <p className="text-[10px] text-sidebar-foreground/50 truncate">Assistant Juridique IA</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const isActive = activeSection === item.id
          return (
            <button
              key={item.id}
              onClick={() => onSectionChange(item.id)}
              title={collapsed ? item.label : undefined}
              className={cn(
                'w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 group',
                isActive
                  ? `bg-gradient-to-r ${item.gradient} ${item.color} shadow-sm`
                  : 'text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent'
              )}
            >
              <div className={cn(
                'flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-lg transition-all',
                isActive
                  ? `bg-gradient-to-br ${item.gradient} ${item.color}`
                  : 'text-sidebar-foreground/50 group-hover:text-sidebar-foreground'
              )}>
                <Icon className="w-[18px] h-[18px]" />
              </div>
              {!collapsed && (
                <span className="truncate">{item.label}</span>
              )}
              {isActive && !collapsed && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
              )}
            </button>
          )
        })}
      </nav>

      {/* Collapse Toggle */}
      <div className="p-3 border-t border-sidebar-border">
        <button
          onClick={onToggleCollapse}
          className="w-full flex items-center justify-center gap-2 rounded-lg py-2 text-xs text-sidebar-foreground/40 hover:text-sidebar-foreground/70 hover:bg-sidebar-accent transition-colors"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          {!collapsed && <span>Réduire</span>}
        </button>
      </div>
    </aside>
  )
}

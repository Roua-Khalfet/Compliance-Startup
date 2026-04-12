'use client'

import { useState } from 'react'
import AppSidebar, { type SectionId } from '@/components/app-sidebar'
import ChatSection from '@/components/chat-section'
import DocumentsSection from '@/components/documents-section'
import ConformiteSection from '@/components/conformite-section'
import QuizSection from '@/components/quiz-section'
import VeilleSection from '@/components/veille-section'
import GraphSection from '@/components/graph-section'

export default function Page() {
  const [activeSection, setActiveSection] = useState<SectionId>('chat')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <AppSidebar
        activeSection={activeSection}
        onSectionChange={setActiveSection}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <main className="flex-1 overflow-hidden">
        {activeSection === 'chat' && <ChatSection />}
        {activeSection === 'documents' && <DocumentsSection />}
        {activeSection === 'conformite' && <ConformiteSection />}
        {activeSection === 'quiz' && <QuizSection />}
        {activeSection === 'veille' && <VeilleSection />}
        {activeSection === 'graph' && <GraphSection />}
      </main>
    </div>
  )
}

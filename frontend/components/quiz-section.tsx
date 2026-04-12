'use client'

import { useState, useCallback } from 'react'
import { Brain, ChevronRight, Trophy, RotateCcw, CheckCircle2, XCircle, Sparkles, AlertTriangle, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'

interface QuizQuestion {
  id: number
  question: string
  options: string[]
  /** Index of the "compliant" answer. null means scoring depends on weights. */
  compliantAnswer: number
  explanation: string
  article: string
  category: string
  /** Weight of this question in the final score (1-3) */
  weight: number
}

const QUESTION_POOL: QuizQuestion[] = [
  // ── Startup Act eligibility ──
  { id: 1, question: "Votre entreprise a-t-elle été créée il y a moins de 8 ans ?", options: ["Oui", "Non", "Pas encore créée", "Je ne sais pas"], compliantAnswer: 0, explanation: "Pour obtenir le label Startup, l'entreprise doit avoir été constituée depuis moins de 8 ans.", article: "Loi n° 2018-20, Art. 3 al. 1", category: "Startup Act", weight: 3 },
  { id: 2, question: "Votre modèle économique repose-t-il sur l'innovation technologique ?", options: ["Oui, fortement", "Partiellement", "Non, activité traditionnelle", "Je ne sais pas"], compliantAnswer: 0, explanation: "Le caractère innovant et le fort potentiel de croissance sont des critères obligatoires du label.", article: "Loi n° 2018-20, Art. 3 al. 2", category: "Startup Act", weight: 3 },
  { id: 3, question: "Votre entreprise est-elle indépendante (pas une filiale ou issue d'une restructuration) ?", options: ["Oui, totalement indépendante", "Non, c'est une filiale", "Issue d'une restructuration", "Je ne sais pas"], compliantAnswer: 0, explanation: "L'entreprise ne doit pas être une filiale ou résulter d'une opération de restructuration.", article: "Loi n° 2018-20, Art. 3 al. 3", category: "Startup Act", weight: 2 },
  { id: 4, question: "Le siège social de votre entreprise est-il situé en Tunisie ?", options: ["Oui", "Non", "En cours de domiciliation", "Je ne sais pas"], compliantAnswer: 0, explanation: "Le siège social doit être en Tunisie pour bénéficier du label Startup Act.", article: "Loi n° 2018-20, Art. 3 al. 4", category: "Startup Act", weight: 2 },
  { id: 5, question: "Le capital de votre société est-il détenu à au moins 2/3 par des personnes physiques ?", options: ["Oui (≥ 66%)", "Non", "Je ne connais pas la répartition", "Non applicable (auto-entrepreneur)"], compliantAnswer: 0, explanation: "Le capital doit être détenu à 2/3 par des personnes physiques ou des fonds d'investissement.", article: "Loi n° 2018-20, Art. 3 al. 5", category: "Startup Act", weight: 2 },

  // ── Forme juridique & Capital ──
  { id: 6, question: "Quel est le statut juridique de votre société ?", options: ["SUARL", "SARL", "SA / SAS", "Pas encore de statut"], compliantAnswer: 0, explanation: "Le choix de la forme juridique détermine les obligations légales. La SUARL et la SARL sont les plus courantes pour les startups.", article: "Code des Sociétés, Art. 92-160", category: "Forme juridique", weight: 1 },
  { id: 7, question: "Votre capital social respecte-t-il le minimum légal pour votre type de société ?", options: ["Oui, il est au-dessus du minimum", "Non, en-dessous du seuil", "Je ne connais pas le minimum", "Pas encore de capital"], compliantAnswer: 0, explanation: "SARL/SUARL : 1 000 TND minimum. SA sans APE : 5 000 TND. SA avec APE : 50 000 TND.", article: "Code des Sociétés, Art. 92 & 160", category: "Forme juridique", weight: 2 },
  { id: 8, question: "Vos statuts ont-ils été rédigés par acte authentique ou sous seing privé ?", options: ["Oui, par un notaire/avocat", "Oui, sous seing privé", "Non, pas de statuts formels", "Je ne sais pas"], compliantAnswer: 0, explanation: "Les statuts doivent être rédigés par acte authentique ou sous seing privé pour être valables.", article: "Code des Sociétés, Art. 96", category: "Forme juridique", weight: 2 },

  // ── Protection des données ──
  { id: 9, question: "Avez-vous effectué une déclaration auprès de l'INPDP pour le traitement de données personnelles ?", options: ["Oui", "Non", "Pas de traitement de données", "Je ne connais pas l'INPDP"], compliantAnswer: 0, explanation: "Toute personne traitant des données personnelles doit effectuer une déclaration préalable auprès de l'INPDP.", article: "Loi n° 2004-63, Art. 7", category: "Protection données", weight: 3 },
  { id: 10, question: "Recueillez-vous le consentement explicite de vos utilisateurs avant de collecter leurs données ?", options: ["Oui, avec case à cocher + politique", "Partiellement", "Non", "Pas applicable"], compliantAnswer: 0, explanation: "Le consentement explicite est obligatoire pour toute collecte de données personnelles.", article: "Loi n° 2004-63, Art. 27", category: "Protection données", weight: 2 },
  { id: 11, question: "Avez-vous une politique de confidentialité accessible sur votre site/application ?", options: ["Oui, complète et visible", "Oui, mais pas à jour", "Non", "Pas de site/app"], compliantAnswer: 0, explanation: "La politique de confidentialité doit informer les utilisateurs sur la finalité, la durée et les droits.", article: "Loi n° 2004-63, Art. 9", category: "Protection données", weight: 2 },

  // ── Obligations fiscales ──
  { id: 12, question: "Votre entreprise est-elle à jour dans ses déclarations fiscales (IS, TVA) ?", options: ["Oui, tout est à jour", "En retard sur certaines", "Non", "Pas encore assujettie"], compliantAnswer: 0, explanation: "Les déclarations fiscales doivent être effectuées dans les délais sous peine de pénalités.", article: "Code Fiscal, Art. 60", category: "Fiscalité", weight: 3 },
  { id: 13, question: "Avez-vous un expert comptable ou un commissaire aux comptes ?", options: ["Oui, expert comptable", "Oui, commissaire aux comptes", "Les deux", "Non, aucun"], compliantAnswer: 0, explanation: "La tenue d'une comptabilité régulière est obligatoire. Les SA doivent avoir un commissaire aux comptes.", article: "Code des Sociétés & Code Fiscal", category: "Fiscalité", weight: 2 },

  // ── Droit du travail / CNSS ──
  { id: 14, question: "Vos salariés sont-ils tous déclarés à la CNSS ?", options: ["Oui, tous déclarés", "Certains seulement", "Non", "Pas de salariés"], compliantAnswer: 0, explanation: "L'affiliation au CNSS est obligatoire pour tous les salariés dès le premier jour.", article: "Code du Travail", category: "Droit social", weight: 3 },
  { id: 15, question: "Vos contrats de travail sont-ils écrits et conformes au Code du Travail ?", options: ["Oui, tous écrits et signés", "Certains sont verbaux", "Pas de contrats écrits", "Pas de salariés"], compliantAnswer: 0, explanation: "Tout contrat de travail doit être formalisé par écrit et respecter les dispositions du Code du Travail.", article: "Code du Travail, Art. 6-13", category: "Droit social", weight: 2 },

  // ── E-commerce ──
  { id: 16, question: "Votre site web affiche-t-il les mentions légales obligatoires ?", options: ["Oui (raison sociale, siège, RCS, contact)", "Partiellement", "Non", "Pas de site web"], compliantAnswer: 0, explanation: "Les mentions obligatoires incluent : raison sociale, siège social, RCS, contact, numéro TVA.", article: "Loi n° 2000-83, Art. 9", category: "E-commerce", weight: 2 },
  { id: 17, question: "Avez-vous des Conditions Générales de Vente/Utilisation accessibles ?", options: ["Oui, acceptées avant achat", "Rédigées mais pas visibles", "Non", "Pas de vente en ligne"], compliantAnswer: 0, explanation: "Les CGV/CGU doivent être accessibles et acceptées par le client avant toute transaction.", article: "Loi n° 2000-83, Art. 25", category: "E-commerce", weight: 2 },

  // ── Fintech / BCT ──
  { id: 18, question: "Si vous exercez une activité de paiement, avez-vous l'agrément BCT ?", options: ["Oui", "En cours de demande", "Non", "Pas d'activité de paiement"], compliantAnswer: 0, explanation: "Toute activité de services de paiement nécessite un agrément de la Banque Centrale de Tunisie.", article: "Loi 2016-48, Art. 34", category: "BCT / Fintech", weight: 3 },
  { id: 19, question: "Avez-vous mis en place un dispositif KYC/AML (vérification d'identité, lutte anti-blanchiment) ?", options: ["Oui, conforme", "En cours d'implémentation", "Non", "Pas applicable"], compliantAnswer: 0, explanation: "Les établissements financiers doivent implémenter un dispositif KYC et de lutte anti-blanchiment.", article: "Loi 2003-75, Art. 74", category: "BCT / Fintech", weight: 3 },

  // ── Propriété intellectuelle ──
  { id: 20, question: "Avez-vous protégé votre marque (dépôt INNORPI) ?", options: ["Oui, marque déposée", "En cours", "Non", "Je ne connais pas la procédure"], compliantAnswer: 0, explanation: "Le dépôt de marque auprès de l'INNORPI protège votre identité commerciale.", article: "Loi n° 2001-36", category: "Propriété intellectuelle", weight: 1 },

  // ── Investissement ──
  { id: 21, question: "Avez-vous déclaré votre investissement auprès de l'APII ?", options: ["Oui", "Non", "En cours", "Pas nécessaire pour mon activité"], compliantAnswer: 0, explanation: "La déclaration d'investissement auprès de l'APII est requise pour bénéficier des incitations.", article: "Loi n° 2016-71", category: "Investissement", weight: 1 },

  // ── Compte en devises ──
  { id: 22, question: "Si vous faites des opérations à l'international, disposez-vous d'un compte en devises autorisé ?", options: ["Oui, compte startup en devises", "En cours de demande", "Non", "Pas d'opérations internationales"], compliantAnswer: 0, explanation: "Les startups labellisées peuvent ouvrir un compte en devises selon les conditions de la circulaire BCT.", article: "Circulaire BCT n° 2019-01", category: "BCT / Fintech", weight: 1 },
]

const QUIZ_SIZE = 10
const CATEGORIES = ['Startup Act', 'Forme juridique', 'Protection données', 'Fiscalité', 'Droit social', 'E-commerce', 'BCT / Fintech', 'Propriété intellectuelle', 'Investissement']

function shuffleArray<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

type QuizState = 'intro' | 'playing' | 'result'

function ScoreRing({ score, max }: { score: number; max: number }) {
  const pct = Math.round((score / max) * 100)
  const circumference = 283
  const offset = circumference - (pct / 100) * circumference
  const color = pct >= 75 ? '#10b981' : pct >= 50 ? '#f59e0b' : '#ef4444'
  return (
    <div className="relative w-44 h-44 mx-auto">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="5" className="text-border" />
        <circle cx="50" cy="50" r="45" fill="none" stroke={color} strokeWidth="5" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1.5s ease-out' }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-black" style={{ color }}>{pct}%</span>
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Conformité</span>
      </div>
    </div>
  )
}

export default function QuizSection() {
  const [state, setState] = useState<QuizState>('intro')
  const [questions, setQuestions] = useState<QuizQuestion[]>([])
  const [current, setCurrent] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [answered, setAnswered] = useState(false)
  const [answers, setAnswers] = useState<number[]>([])

  const startQuiz = useCallback(() => {
    // Pick 10 questions spread across categories
    const shuffled = shuffleArray(QUESTION_POOL)
    const picked: QuizQuestion[] = []
    const catCounts: Record<string, number> = {}
    for (const q of shuffled) {
      if (picked.length >= QUIZ_SIZE) break
      const cc = catCounts[q.category] || 0
      if (cc >= 2) continue // max 2 per category for variety
      picked.push(q)
      catCounts[q.category] = cc + 1
    }
    // Fill remaining if needed
    if (picked.length < QUIZ_SIZE) {
      for (const q of shuffled) {
        if (picked.length >= QUIZ_SIZE) break
        if (!picked.includes(q)) picked.push(q)
      }
    }
    setQuestions(picked)
    setCurrent(0)
    setSelected(null)
    setAnswered(false)
    setAnswers([])
    setState('playing')
  }, [])

  const handleAnswer = (idx: number) => {
    if (answered) return
    setSelected(idx)
    setAnswered(true)
    setAnswers(a => [...a, idx])
  }

  const nextQuestion = () => {
    if (current + 1 >= questions.length) {
      setState('result')
    } else {
      setCurrent(c => c + 1)
      setSelected(null)
      setAnswered(false)
    }
  }

  // Score calculation
  const totalWeight = questions.reduce((s, q) => s + q.weight, 0)
  const earnedWeight = answers.reduce((s, ans, i) => {
    if (!questions[i]) return s
    const q = questions[i]
    if (ans === q.compliantAnswer) return s + q.weight
    if (ans === 1) return s + q.weight * 0.3 // partial
    return s
  }, 0)
  const scorePct = totalWeight > 0 ? Math.round((earnedWeight / totalWeight) * 100) : 0

  const getVerdict = (pct: number) => {
    if (pct >= 80) return { label: '✅ Très bonne conformité', color: 'text-emerald-600', bg: 'bg-emerald-50 border-emerald-200', desc: 'Votre société respecte bien le cadre juridique tunisien. Continuez à surveiller les évolutions réglementaires.' }
    if (pct >= 60) return { label: '⚠️ Conformité partielle', color: 'text-amber-600', bg: 'bg-amber-50 border-amber-200', desc: 'Certains aspects nécessitent votre attention. Consultez les recommandations ci-dessous.' }
    if (pct >= 40) return { label: '🔶 Insuffisant', color: 'text-orange-600', bg: 'bg-orange-50 border-orange-200', desc: 'Plusieurs obligations ne sont pas respectées. Il est recommandé de consulter un conseil juridique.' }
    return { label: '🚨 Non conforme', color: 'text-red-600', bg: 'bg-red-50 border-red-200', desc: 'Votre société présente des risques juridiques significatifs. Consultez un avocat spécialisé.' }
  }

  // Category scores for result
  const catScores = questions.reduce<Record<string, { earned: number; total: number }>>((acc, q, i) => {
    if (!acc[q.category]) acc[q.category] = { earned: 0, total: 0 }
    acc[q.category].total += q.weight
    if (answers[i] === q.compliantAnswer) acc[q.category].earned += q.weight
    else if (answers[i] === 1) acc[q.category].earned += q.weight * 0.3
    return acc
  }, {})

  // Non-compliant items for recommendations
  const issues = questions.filter((q, i) => answers[i] !== undefined && answers[i] !== q.compliantAnswer)

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border bg-gradient-to-r from-amber-500/5 via-orange-500/5 to-transparent">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground">Quiz de Conformité</h2>
            <p className="text-xs text-muted-foreground">Évaluez si votre société respecte le cadre juridique tunisien</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto flex items-center justify-center p-6">
        {/* ── INTRO ── */}
        {state === 'intro' && (
          <div className="text-center space-y-8 max-w-lg w-full">
            <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-amber-500/10 to-orange-500/10 flex items-center justify-center mx-auto animate-float">
              <Brain className="w-12 h-12 text-amber-500" />
            </div>
            <div className="space-y-3">
              <h3 className="text-2xl font-black gradient-text">Auto-évaluation Juridique</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Répondez à <strong>10 questions</strong> sur votre société pour évaluer sa conformité avec la législation tunisienne : Startup Act, protection des données, fiscalité, droit du travail...
              </p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[{ n: '22+', l: 'Questions' }, { n: '10', l: 'Par évaluation' }, { n: '9', l: 'Domaines' }].map((s, i) => (
                <div key={i} className="p-3 rounded-xl bg-secondary/50 border border-border">
                  <p className="text-lg font-black text-foreground">{s.n}</p>
                  <p className="text-[10px] text-muted-foreground">{s.l}</p>
                </div>
              ))}
            </div>
            <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-left space-y-2">
              <p className="text-xs font-semibold text-amber-800">💡 Comment ça marche ?</p>
              <ul className="text-xs text-amber-700 space-y-1">
                <li>• Chaque question porte sur une obligation légale réelle</li>
                <li>• La première option est toujours la réponse conforme</li>
                <li>• Vous obtenez un score pondéré + recommandations concrètes</li>
                <li>• Les articles de loi sont cités pour chaque point</li>
              </ul>
            </div>
            <Button onClick={startQuiz} className="w-full py-6 rounded-xl text-sm font-semibold bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 shadow-lg shadow-amber-500/20 gap-2">
              <Sparkles className="w-4 h-4" /> Commencer l&apos;évaluation
            </Button>
          </div>
        )}

        {/* ── PLAYING ── */}
        {state === 'playing' && questions[current] && (
          <div className="w-full max-w-2xl space-y-6">
            {/* Progress */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Question {current + 1} / {questions.length}</span>
                <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium text-[10px]">{questions[current].category}</span>
              </div>
              <Progress value={((current + 1) / questions.length) * 100} className="h-2" />
            </div>

            {/* Question */}
            <div className="p-6 rounded-2xl bg-card border border-border shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                {questions[current].weight >= 3 && <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-600 font-bold">⚠️ Critique</span>}
                {questions[current].weight === 2 && <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-600 font-bold">Important</span>}
                {questions[current].weight === 1 && <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-bold">Recommandé</span>}
              </div>
              <h3 className="text-lg font-bold text-foreground leading-relaxed mb-6">{questions[current].question}</h3>

              <div className="space-y-3">
                {questions[current].options.map((opt, idx) => {
                  const isCompliant = idx === questions[current].compliantAnswer
                  const isSelected = idx === selected
                  let optStyle = 'border-border hover:border-amber-300 hover:bg-amber-50/30'
                  if (answered) {
                    if (isCompliant) optStyle = 'border-emerald-400 bg-emerald-50 shadow-sm shadow-emerald-500/10'
                    else if (isSelected && !isCompliant) optStyle = 'border-red-400 bg-red-50'
                    else optStyle = 'border-border opacity-50'
                  }
                  return (
                    <button key={idx} onClick={() => handleAnswer(idx)} disabled={answered}
                      className={`w-full text-left p-4 rounded-xl border-2 transition-all flex items-center gap-3 ${optStyle}`}>
                      <span className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${
                        answered && isCompliant ? 'bg-emerald-500 text-white' :
                        answered && isSelected && !isCompliant ? 'bg-red-500 text-white' :
                        'bg-secondary text-secondary-foreground'
                      }`}>{String.fromCharCode(65 + idx)}</span>
                      <span className="text-sm font-medium text-foreground">{opt}</span>
                      {answered && isCompliant && <CheckCircle2 className="w-5 h-5 text-emerald-500 ml-auto" />}
                      {answered && isSelected && !isCompliant && <XCircle className="w-5 h-5 text-red-500 ml-auto" />}
                    </button>
                  )
                })}
              </div>

              {answered && (
                <div className={`mt-4 p-4 rounded-xl border space-y-1 animate-in fade-in duration-300 ${
                  selected === questions[current].compliantAnswer ? 'bg-emerald-50/70 border-emerald-200' : 'bg-amber-50/70 border-amber-200'
                }`}>
                  <p className={`text-xs font-semibold ${selected === questions[current].compliantAnswer ? 'text-emerald-700' : 'text-amber-700'}`}>
                    {selected === questions[current].compliantAnswer ? '✅ Conforme !' : '⚠️ Point d\'attention :'}
                  </p>
                  <p className={`text-xs leading-relaxed ${selected === questions[current].compliantAnswer ? 'text-emerald-600' : 'text-amber-600'}`}>
                    {questions[current].explanation}
                  </p>
                  <p className="text-[10px] text-muted-foreground font-medium mt-1">📖 {questions[current].article}</p>
                </div>
              )}
            </div>

            {answered && (
              <Button onClick={nextQuestion} className="w-full py-5 rounded-xl text-sm font-semibold bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 gap-2 animate-in fade-in duration-300">
                {current + 1 >= questions.length ? 'Voir le résultat' : 'Question suivante'} <ChevronRight className="w-4 h-4" />
              </Button>
            )}

            {/* Answer dots */}
            <div className="flex justify-center gap-1.5">
              {Array.from({ length: questions.length }).map((_, i) => (
                <div key={i} className={`w-3 h-3 rounded-full transition-all ${
                  i >= answers.length ? 'bg-border' :
                  answers[i] === questions[i]?.compliantAnswer ? 'bg-emerald-500 scale-110' : 'bg-red-400'
                }`} />
              ))}
            </div>
          </div>
        )}

        {/* ── RESULT ── */}
        {state === 'result' && (
          <div className="w-full max-w-2xl space-y-6 pb-6">
            <div className="text-center space-y-4">
              <ScoreRing score={earnedWeight} max={totalWeight} />
              <div className={`inline-block px-5 py-2 rounded-xl border text-sm font-bold ${getVerdict(scorePct).bg} ${getVerdict(scorePct).color}`}>
                {getVerdict(scorePct).label}
              </div>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">{getVerdict(scorePct).desc}</p>
            </div>

            {/* Category breakdown */}
            <div className="p-5 rounded-2xl bg-card border border-border space-y-3">
              <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider">Score par domaine</h4>
              {Object.entries(catScores).map(([cat, { earned, total }]) => {
                const pct = total > 0 ? Math.round((earned / total) * 100) : 0
                return (
                  <div key={cat} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-medium text-foreground">{cat}</span>
                      <span className={`font-bold ${pct >= 75 ? 'text-emerald-600' : pct >= 50 ? 'text-amber-600' : 'text-red-600'}`}>{pct}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-secondary overflow-hidden">
                      <div className={`h-full rounded-full transition-all duration-1000 ${pct >= 75 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500'}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Recommendations */}
            {issues.length > 0 && (
              <div className="p-5 rounded-2xl bg-amber-50 border border-amber-200 space-y-3">
                <h4 className="text-xs font-semibold text-amber-800 uppercase tracking-wider flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" /> Actions recommandées ({issues.length})
                </h4>
                {issues.map((q, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-amber-700 p-2 rounded-lg bg-white/50">
                    <ArrowRight className="w-3.5 h-3.5 mt-0.5 text-amber-500 flex-shrink-0" />
                    <div>
                      <p className="font-semibold">{q.question}</p>
                      <p className="text-amber-600/80 mt-0.5">{q.explanation}</p>
                      <p className="text-[10px] text-amber-500 mt-0.5">📖 {q.article}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Detail per question */}
            <div className="p-5 rounded-2xl bg-card border border-border space-y-2">
              <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">Détail par question</h4>
              {questions.map((q, i) => (
                <div key={i} className="flex items-center gap-2 text-xs py-1">
                  {answers[i] === q.compliantAnswer
                    ? <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                    : <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />}
                  <span className="truncate text-muted-foreground flex-1">{q.question}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-secondary text-muted-foreground flex-shrink-0">{q.category}</span>
                </div>
              ))}
            </div>

            <Button onClick={startQuiz} className="w-full py-5 rounded-xl text-sm font-semibold bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 gap-2">
              <RotateCcw className="w-4 h-4" /> Refaire l&apos;évaluation
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

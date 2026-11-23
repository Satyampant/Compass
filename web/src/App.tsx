import { useEffect, useState, useSyncExternalStore } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, systemApi } from './api'
import { Icon, type IconName } from './icons'
import { QuickCapture, type CaptureKind } from './components/QuickCapture'
import { PlanDialog } from './components/PlanDialog'
import { CalendarBanner } from './components/CalendarBanner'
import { TodayPage } from './pages/Today'
import { QueuePage } from './pages/Queue'
import { MonthPage } from './pages/Month'
import { QuarterPage } from './pages/Quarter'
import { YearPage } from './pages/Year'
import { SetupPage } from './pages/Setup'
import { WeekPage } from './pages/Week'
import { ReviewPage } from './pages/Review'
import { StatusPage } from './pages/Status'

const PAGES = ['today', 'learn', 'week', 'month', 'quarter', 'year', 'review', 'status', 'setup'] as const
type Page = (typeof PAGES)[number]
const NAMES: Record<string, string> = { today: 'Today', learn: 'Learning queue', week: 'This week', month: 'This month', quarter: 'This quarter', year: 'This year', review: 'Weekly review', status: 'Status', setup: 'Setup' }
const ICONS: Record<string, IconName> = { today: 'sun', learn: 'queue', week: 'week', month: 'month', quarter: 'quarter', year: 'year', review: 'review', status: 'clock' }
const READY = new Set<string>(PAGES)

function PageView({ page, today, onCapture, onPlan }: { page: Page; today?: string; onCapture: (k: CaptureKind) => void; onPlan: () => void }) {
  if (page === 'learn') return <QueuePage />
  if (page === 'setup') return <SetupPage />
  if (page === 'review') return <ReviewPage />
  if (page === 'status') return <StatusPage />
  if (page === 'today' || !today) return <TodayPage onCapture={onCapture} onPlan={onPlan} />
  if (page === 'week') return <WeekPage today={today} />
  if (page === 'month') return <MonthPage today={today} />
  if (page === 'quarter') return <QuarterPage today={today} />
  return <YearPage today={today} />
}

function useHash(): Page {
  const hash = useSyncExternalStore(
    (cb) => {
      window.addEventListener('hashchange', cb)
      return () => window.removeEventListener('hashchange', cb)
    },
    () => window.location.hash.slice(1),
  )
  return (PAGES as readonly string[]).includes(hash) ? (hash as Page) : 'today'
}

function NavItem({ p, page, count }: { p: string; page: Page; count?: number }) {
  if (!READY.has(p))
    return (
      <span className="nav soon" title="Comes in a later release">
        <Icon name={ICONS[p]} />
        {NAMES[p]}
      </span>
    )
  return (
    <a className={`nav ${p === page ? 'active' : ''}`} href={`#${p}`} aria-current={p === page ? 'page' : undefined}>
      <Icon name={ICONS[p]} />
      {NAMES[p]}
      {count !== undefined && <span className="count">{count}</span>}
    </a>
  )
}

export default function App() {
  const page = useHash()
  const [capture, setCapture] = useState<CaptureKind | null>(null)
  const [menu, setMenu] = useState(false)
  const [planning, setPlanning] = useState(false)
  const today = useQuery({ queryKey: ['today'], queryFn: api.today })
  const status = useQuery({ queryKey: ['status'], queryFn: systemApi.status, refetchInterval: 60_000 })
  const warnings = status.data?.rows.filter((r) => !r.ok).length

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = /INPUT|TEXTAREA|SELECT/.test((e.target as HTMLElement).tagName)
      if (e.key.toLowerCase() === 'c' && !e.metaKey && !e.ctrlKey && !e.altKey && !typing && !document.querySelector('dialog[open]')) {
        e.preventDefault()
        setCapture('learn')
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [page])

  return (
    <div className="shell">
      <aside className={`rail ${menu ? 'open' : ''}`}>
        <a className="brand" href="#today">
          <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
            <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="1.2" />
            <path d="M16 4l3.2 12L16 28l-3.2-12z" fill="currentColor" />
            <circle cx="16" cy="16" r="1.6" fill="var(--rail)" />
          </svg>
          Compass
        </a>
        <nav aria-label="Workspace navigation" onClick={() => setMenu(false)}>
          <div className="navgroup">
            <p className="kicker">My workspace</p>
            <NavItem p="today" page={page} />
            <NavItem p="learn" page={page} count={today.data?.inbox_count} />
          </div>
          <div className="navgroup">
            <p className="kicker">Planning horizons</p>
            {['week', 'month', 'quarter', 'year'].map((p) => (
              <NavItem key={p} p={p} page={page} />
            ))}
          </div>
          <div className="navgroup">
            <p className="kicker">Reflect</p>
            <NavItem p="review" page={page} />
            <NavItem p="status" page={page} count={warnings || undefined} />
          </div>
        </nav>
      </aside>
      <button className={`veil ${menu ? 'show' : ''}`} aria-label="Close navigation" onClick={() => setMenu(false)} />
      <main className="main">
        <header className="bar">
          <div className="crumb">
            <button className="menu" aria-label="Open navigation" onClick={() => setMenu(true)}>
              <Icon name="menu" />
            </button>
            <span>Workspace</span>
            <span>/</span>
            <strong>{NAMES[page]}</strong>
          </div>
          <div className="tools">
            {today.data && (
              <button className="btn outline" onClick={() => setPlanning(true)}>
                Plan tomorrow
              </button>
            )}
            <button className="btn primary" onClick={() => setCapture('learn')}>
              <Icon name="plus" />
              Quick capture <kbd>C</kbd>
            </button>
          </div>
        </header>
        <CalendarBanner />
        <PageView page={page} today={today.data?.date} onCapture={setCapture} onPlan={() => setPlanning(true)} />
      </main>
      {planning && today.data && <PlanDialog today={today.data.date} topLimit={today.data.top_limit} onClose={() => setPlanning(false)} />}
      {capture && <QuickCapture initial={capture} onClose={() => setCapture(null)} />}
    </div>
  )
}

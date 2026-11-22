import { useEffect, useState, useSyncExternalStore } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import { Icon, type IconName } from './icons'
import { QuickCapture, type CaptureKind } from './components/QuickCapture'
import { TodayPage } from './pages/Today'
import { QueuePage } from './pages/Queue'

type Page = 'today' | 'learn'
const NAMES: Record<string, string> = { today: 'Today', learn: 'Learning queue', week: 'This week', month: 'This month', quarter: 'This quarter', year: 'This year', review: 'Weekly review' }
const ICONS: Record<string, IconName> = { today: 'sun', learn: 'queue', week: 'week', month: 'month', quarter: 'quarter', year: 'year', review: 'review' }
const READY = new Set(['today', 'learn'])

function useHash(): Page {
  const hash = useSyncExternalStore(
    (cb) => {
      window.addEventListener('hashchange', cb)
      return () => window.removeEventListener('hashchange', cb)
    },
    () => window.location.hash.slice(1),
  )
  return hash === 'learn' ? 'learn' : 'today'
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
  const today = useQuery({ queryKey: ['today'], queryFn: api.today })

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
            <button className="btn primary" onClick={() => setCapture('learn')}>
              <Icon name="plus" />
              Quick capture <kbd>C</kbd>
            </button>
          </div>
        </header>
        {page === 'today' ? <TodayPage onCapture={setCapture} /> : <QueuePage />}
      </main>
      {capture && <QuickCapture initial={capture} onClose={() => setCapture(null)} />}
    </div>
  )
}

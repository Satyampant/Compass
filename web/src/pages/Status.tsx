import { useQuery } from '@tanstack/react-query'
import { systemApi } from '../api'
import { Icon } from '../icons'

function ago(iso: string | null): string {
  if (!iso) return 'never'
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60_000)
  if (min < 1) return 'just now'
  if (min < 60) return `${min} min ago`
  if (min < 48 * 60) return `${Math.round(min / 60)} h ago`
  return `${Math.round(min / 1440)} days ago`
}

/** Did everything run? One row per job, the Telegram check and the backup. */
export function StatusPage() {
  const { data } = useQuery({ queryKey: ['status'], queryFn: systemApi.status, refetchInterval: 30_000 })
  if (!data) return null
  const warnings = data.rows.filter((r) => !r.ok).length
  return (
    <>
      <div className="pagehead">
        <div>
          <div className="over kicker" style={{ color: 'var(--rust)' }}>
            <Icon name="clock" />
            {warnings ? `${warnings} to look at` : 'Everything ran'}
          </div>
          <h1>Status</h1>
        </div>
      </div>
      <div className="cols">
        <section className="card">
          <div className="cardhead">
            <h2>Last runs</h2>
          </div>
          <div className="section">
            {data.rows.map((r) => (
              <div className="slot" key={r.name} data-testid={`status-${r.name}`}>
                <span className="t">{ago(r.last)}</span>
                <span className="name">
                  <span>{r.name}</span>
                  {r.detail && <span className="muted">· {r.detail}</span>}
                </span>
                <span className={`chip ${r.ok ? 'good' : 'warn'}`}>{r.ok ? 'OK' : 'Check'}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="card">
          <div className="cardhead">
            <h2>Jobs that gave up</h2>
            <span className="chip">{data.failures.length}</span>
          </div>
          {data.failures.map((f, i) => (
            <div className="decide" key={i}>
              <span className="title">
                {f.kind} · {ago(f.finished_at)} · {f.attempts} tries
              </span>
              <span className="support">{f.error}</span>
            </div>
          ))}
          {data.failures.length === 0 && <p className="empty">None. Every job finished.</p>}
        </section>
        <section className="card">
          <div className="cardhead">
            <h2>Your data</h2>
          </div>
          <p className="support">Everything Compass holds, as one JSON file. It loads into an empty database with <code>uv run python -m app.modules.system.export load FILE</code>.</p>
          <div className="actions">
            <a className="btn outline" href="/v1/export" download>
              Download all data
            </a>
          </div>
        </section>
      </div>
    </>
  )
}

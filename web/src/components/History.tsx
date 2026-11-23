import { useQuery } from '@tanstack/react-query'
import { historyApi, type HistoryData } from '../api'
import { day } from '../format'

function useHistory() {
  return useQuery({ queryKey: ['history'], queryFn: historyApi.get })
}

const SHADE = ['', 'color-mix(in srgb, var(--g1) 40%, var(--soft))', 'var(--g1)']

/** Twelve weeks of days: darker when the day was both planned and closed. */
export function History() {
  const { data } = useHistory()
  if (!data) return null
  const weeks = Array.from({ length: 12 }, (_, w) => data.days.slice(w * 7, w * 7 + 7))
  const full = data.days.filter((d) => d.planned && d.closed).length
  return (
    <section className="card">
      <div className="cardhead">
        <h2>Plan and shutdown</h2>
        <span className="chip">{full} full days in 12 weeks</span>
      </div>
      <p className="support">One square per day. Light: planned or closed. Dark: both.</p>
      <div className="heat" data-testid="heat">
        {weeks.map((w) => (
          <div key={w[0].date}>
            {w.map((d) => {
              const level = Number(d.planned) + Number(d.closed)
              return <i key={d.date} data-level={level} title={`${d.date}: ${d.planned ? 'planned' : 'not planned'}, ${d.closed ? 'closed' : 'not closed'}`} style={level ? { background: SHADE[level] } : undefined} />
            })}
          </div>
        ))}
      </div>
    </section>
  )
}

function FlowBars({ weeks }: { weeks: HistoryData['weeks'] }) {
  const max = Math.max(1, ...weeks.flatMap((w) => [w.added, w.closed]))
  return (
    <div className="flow" data-testid="flow">
      {weeks.map((w) => (
        <div className="flowweek" key={w.week_start} title={`Week of ${w.week_start}: ${w.added} in, ${w.closed} out`}>
          <div className="flowbars">
            <i className="in" style={{ height: `${(w.added / max) * 100}%` }} />
            <i className="out" style={{ height: `${(w.closed / max) * 100}%` }} />
          </div>
          <span>{day(w.week_start).getDate()}</span>
        </div>
      ))}
    </div>
  )
}

/** Items added against items closed, for the last eight weeks. */
export function QueueFlow() {
  const { data } = useHistory()
  if (!data) return null
  const added = data.weeks.reduce((s, w) => s + w.added, 0)
  const closed = data.weeks.reduce((s, w) => s + w.closed, 0)
  return (
    <section className="card">
      <div className="cardhead">
        <h2>Queue flow</h2>
        <span className="chip">last 8 weeks</span>
      </div>
      <p className="support">A healthy queue closes about as much as it takes in.</p>
      <FlowBars weeks={data.weeks} />
      <div className="legend">
        <span className="gtag">
          <i className="dot" style={{ background: 'var(--g2)' }} />
          In {added}
        </span>
        <span className="gtag">
          <i className="dot" style={{ background: 'var(--g1)' }} />
          Out {closed}
        </span>
      </div>
    </section>
  )
}

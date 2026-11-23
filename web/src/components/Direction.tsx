import type { Today } from '../api'

const hours = (min: number) => `${Math.round((min / 60) * 10) / 10}h`

/** Today's aligned share of hours, learning blocks kept this week and the planning streak. */
export function Direction({ data }: { data: Today }) {
  const d = data.direction
  const pct = d.alignment === null ? null : Math.round(d.alignment * 100)
  const chip = pct === null ? null : pct >= 50 ? ['good', 'On course'] : ['warn', 'Drifting']
  return (
    <section className="card">
      <div className="cardhead">
        <h2>Direction check</h2>
        {chip && <span className={`chip ${chip[0]}`}>{chip[1]}</span>}
      </div>
      <p className="figure section" data-testid="alignment">
        {pct === null ? '–' : `${pct}%`}
      </p>
      <p className="support">{pct === null ? 'Nothing planned yet today.' : `of today’s ${hours(d.planned_min)} planned move a goal forward`}</p>
      <div className="facts">
        <div className="fact">
          <span>Learning blocks kept this week</span>
          <b className="num">
            {d.blocks_kept} of {d.blocks_total}
          </b>
        </div>
        <div className="fact">
          <span>Days planned in a row</span>
          <b className="num">{d.planning_streak}</b>
        </div>
      </div>
    </section>
  )
}

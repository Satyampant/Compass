import { useState } from 'react'
import { Icon } from '../icons'
import { PlanningPrompt } from '../components/PlanningPrompt'
import { day, periodDay } from '../format'
import { AddGoalDialog, DeleteGoal, Dot } from '../components/goals'
import { pct, useGoals } from '../goals'

/** This year: up to three themes, each with this quarter's goals under it. */
export function YearPage({ today }: { today: string }) {
  const themes = useGoals('year')
  const quarter = useGoals('quarter')
  const [adding, setAdding] = useState(false)
  const year = day(today).getFullYear()
  const [n, of] = periodDay(`${year}-01-01`, `${year}-12-31`, today)
  const list = themes.data ?? []

  return (
    <>
      <div className="pagehead">
        <div>
          <div className="over kicker" style={{ color: 'var(--rust)' }}>
            <Icon name="year" />
            {year} · {list.length === 1 ? 'one theme' : `${list.length} themes`}
          </div>
          <h1>This year</h1>
        </div>
        <span>{of - n} days left</span>
      </div>
      <PlanningPrompt />
      <div className="trio">
        {list.map((t, i) => {
          const goals = (quarter.data ?? []).filter((g) => g.parent_id === t.id)
          return (
            <section className="card theme" key={t.id}>
              <p className="kicker">
                Theme {i + 1}
                {t.short ? ` · ${t.short}` : ''}
              </p>
              <h2>{t.title}</h2>
              <DeleteGoal goal={t} />
              <ul>
                {goals.map((g) => (
                  <li key={g.id}>
                    <span className="gtag">
                      <Dot color={g.color} />
                      {g.title}
                    </span>
                    <span className="chip">{pct(g.progress)}%</span>
                  </li>
                ))}
                {goals.length === 0 && <li className="muted">No goal this quarter yet</li>}
              </ul>
            </section>
          )
        })}
        {list.length < 3 && (
          <section className="card theme">
            <p className="kicker">Theme {list.length + 1}</p>
            <h2>What is this year about?</h2>
            <p className="support">Up to three themes. Work and life sit side by side.</p>
            <div className="actions">
              <button className="btn outline" onClick={() => setAdding(true)}>
                <Icon name="plus" />
                Add a theme
              </button>
            </div>
          </section>
        )}
      </div>
      <p className="support section">
        Each theme breaks down into this quarter’s goals.{' '}
        <a className="link" href="#quarter">
          Open this quarter <Icon name="arrow" />
        </a>
      </p>
      {adding && <AddGoalDialog horizon="year" parents={[]} onClose={() => setAdding(false)} />}
    </>
  )
}

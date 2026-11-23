import { useState } from 'react'
import type { Goal } from '../api'
import { Icon } from '../icons'
import { day, isoDay, monthName, periodDay } from '../format'
import { AddGoalDialog, DeleteGoal, Dot, DraftRow, GoalTag } from '../components/goals'
import { useGoals, useToggleGoal } from '../goals'

export function GoalCheck({ goal, tag, onToggle }: { goal: Goal; tag?: Goal; onToggle: () => void }) {
  return (
    <div className={`task ${goal.done ? 'done' : ''}`}>
      <button className="check" aria-pressed={goal.done} aria-label={`${goal.done ? 'Reopen' : 'Complete'} ${goal.title}`} onClick={onToggle}>
        <Icon name="check" />
      </button>
      <span className="taskbody">
        <span className="title">{goal.title}</span>
        <span className="sub">
          <GoalTag goal={tag} />
          {goal.due_date && <span>{day(goal.due_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</span>}
        </span>
      </span>
      <DeleteGoal goal={goal} />
    </div>
  )
}

/** Monday-first weeks covering the month, with spill-over days from either side. */
function monthGrid(today: string): Date[] {
  const d = day(today)
  const first = new Date(d.getFullYear(), d.getMonth(), 1, 12)
  const last = new Date(d.getFullYear(), d.getMonth() + 1, 0, 12)
  const start = new Date(first)
  start.setDate(1 - ((first.getDay() + 6) % 7))
  const days: Date[] = []
  for (const c = new Date(start); c <= last || days.length % 7; c.setDate(c.getDate() + 1)) days.push(new Date(c))
  return days
}

/** This month: a calendar of dated milestones and a checklist with progress. */
export function MonthPage({ today }: { today: string }) {
  const milestones = useGoals('month')
  const quarter = useGoals('quarter')
  const toggle = useToggleGoal('month')
  const [adding, setAdding] = useState(false)
  const list = milestones.data ?? []
  const quarterById = new Map((quarter.data ?? []).map((g) => [g.id, g]))
  const month = day(today).getMonth()
  const start = `${today.slice(0, 7)}-01`
  const end = isoDay(new Date(day(today).getFullYear(), month + 1, 0, 12))
  const [n, of] = periodDay(start, end, today)
  const done = list.filter((m) => m.done).length
  const dated = list.filter((m) => m.due_date)

  return (
    <>
      <div className="pagehead">
        <div>
          <div className="over kicker" style={{ color: 'var(--rust)' }}>
            <Icon name="month" />
            {monthName(today)} {today.slice(0, 4)}
          </div>
          <h1>This month</h1>
        </div>
        <span>{of - n} days left</span>
      </div>
      <div className="cols">
        <section className="card">
          <div className="cardhead">
            <h2>Calendar</h2>
            <span className="chip">{dated.length} dated milestones</span>
          </div>
          <div className="cal">
            {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => (
              <div className="dh" key={d}>
                {d}
              </div>
            ))}
            {monthGrid(today).map((d) => {
              const iso = isoDay(d)
              return (
                <div key={iso} className={`d ${d.getMonth() !== month ? 'off' : ''} ${iso === today ? 'today' : ''}`}>
                  <span className="n">{d.getDate()}</span>
                  {dated
                    .filter((m) => m.due_date === iso)
                    .map((m) => (
                      <span className="ev" key={m.id} title={m.title}>
                        <Dot color={quarterById.get(m.parent_id ?? -1)?.color} />
                        <span>{m.title}</span>
                      </span>
                    ))}
                </div>
              )
            })}
          </div>
        </section>
        <section className="card">
          <div className="cardhead">
            <span className="kicker">Milestones</span>
            <button className="link" onClick={() => setAdding(true)} disabled={!quarter.data?.length} title={quarter.data?.length ? undefined : 'Add a quarter goal first'}>
              <Icon name="plus" />
              Add
            </button>
          </div>
          {list.length > 0 && (
            <div className="meterwrap">
              <span>
                {done} / {list.length} milestones
              </span>
              <div className="meter">
                <i style={{ width: `${(done / list.length) * 100}%` }} />
              </div>
            </div>
          )}
          {list.map((m) =>
            m.draft ? (
              <DraftRow key={m.id} goal={m} parents={quarter.data ?? []} why="Needs a quarter goal" />
            ) : (
              <GoalCheck key={m.id} goal={m} tag={quarterById.get(m.parent_id ?? -1)} onToggle={() => toggle.mutate(m)} />
            ),
          )}
          {milestones.isSuccess && list.length === 0 && <p className="empty">No milestones this month yet.</p>}
        </section>
      </div>
      {adding && <AddGoalDialog horizon="month" parents={quarter.data ?? []} onClose={() => setAdding(false)} />}
    </>
  )
}

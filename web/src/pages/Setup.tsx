import { useState } from 'react'
import type { Goal, Horizon } from '../api'
import { Icon } from '../icons'
import { Dot, GoalFields } from '../components/goals'
import { useCreateGoal, useGoals } from '../goals'

const STEPS: { horizon: Horizon; title: string; hint: string; max: number }[] = [
  { horizon: 'year', title: 'Themes for this year', hint: 'Up to three. Work and life sit side by side.', max: 3 },
  { horizon: 'quarter', title: 'Goals for this quarter', hint: 'Up to five, each with one to three key results.', max: 5 },
  { horizon: 'month', title: 'Milestones for this month', hint: 'The steps this month that move a quarter goal.', max: 99 },
  { horizon: 'week', title: 'Outcomes for this week', hint: 'Up to three. Each one finishes part of a milestone.', max: 3 },
]

function Added({ goals }: { goals: Goal[] }) {
  return (
    <ul className="setup-list">
      {goals.map((g) => (
        <li key={g.id}>
          <Dot color={g.color} />
          {g.title}
        </li>
      ))}
    </ul>
  )
}

/** First run: themes, quarter goals, month milestones, then this week's outcomes. */
export function SetupPage() {
  const [step, setStep] = useState(0)
  const [formKey, setFormKey] = useState(0)
  const { horizon, title, hint, max } = STEPS[step]
  const goals = useGoals(horizon)
  const parents = useGoals(STEPS[Math.max(step - 1, 0)].horizon)
  const create = useCreateGoal(() => setFormKey((k) => k + 1))
  const list = goals.data ?? []
  const last = step === STEPS.length - 1
  const go = (n: number) => {
    create.reset()
    setStep(n)
  }

  return (
    <>
      <div className="pagehead">
        <div>
          <div className="over kicker" style={{ color: 'var(--rust)' }}>
            <Icon name="compass" />
            Setup · step {step + 1} of {STEPS.length}
          </div>
          <h1>{title}</h1>
        </div>
      </div>
      <p className="lead">{hint}</p>
      <section className="card setup">
        {list.length > 0 && <Added goals={list} />}
        {list.length < max && (
          <GoalFields
            key={`${horizon}-${formKey}`}
            horizon={horizon}
            parents={step === 0 ? [] : (parents.data ?? [])}
            onSave={(g) => create.mutate(g)}
            saving={create.isPending}
            error={create.error?.message}
            submitLabel="Add"
          />
        )}
        <div className="actions">
          {step > 0 && (
            <button className="btn outline" onClick={() => go(step - 1)}>
              Back
            </button>
          )}
          {last ? (
            <button className="btn primary" disabled={!list.length} onClick={() => (window.location.hash = 'today')}>
              Finish setup
            </button>
          ) : (
            <button className="btn primary" disabled={!list.length} onClick={() => go(step + 1)}>
              Next <Icon name="arrow" />
            </button>
          )}
        </div>
      </section>
    </>
  )
}

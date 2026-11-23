import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { goalsApi, type Horizon } from '../api'
import { useGoals } from '../goals'
import { AddGoalDialog } from './goals'

function PlanDialog({ horizon, starts, label, onClose }: { horizon: Horizon; starts: string; label: string; onClose: () => void }) {
  const themes = useGoals('year', starts)
  if (horizon === 'quarter' && !themes.data) return null
  return (
    <AddGoalDialog
      horizon={horizon}
      on={starts}
      parents={themes.data ?? []}
      title={horizon === 'year' ? `A theme for ${label}` : `A goal for ${label}`}
      onClose={onClose}
    />
  )
}

/** Planning that is open now: next quarter from the 24th of its last month, next year from 1 December. */
export function PlanningPrompt() {
  const { data } = useQuery({ queryKey: ['goals', 'prompts'], queryFn: goalsApi.prompts })
  const [open, setOpen] = useState<number | null>(null)
  if (!data?.length) return null
  const first = data[0]
  const label = data.map((p) => p.label).join(' and ')
  return (
    <section className="card banner prompt" data-testid="planning-prompt">
      <div>
        <p className="kicker">Coming up</p>
        <h3 style={{ marginTop: 6 }}>{label} planning is open</h3>
        <p className="support">
          {first.horizon === 'year' ? 'Choose up to three themes for the year, then the first quarter’s goals.' : 'Set up to five goals for the quarter, each with one to three key results.'}
        </p>
      </div>
      <div className="actions" style={{ marginTop: 0 }}>
        {data.map((p, i) => (
          <button key={p.label} className="btn primary" onClick={() => setOpen(i)}>
            Plan {p.label}
          </button>
        ))}
      </div>
      {open !== null && <PlanDialog {...data[open]} onClose={() => setOpen(null)} />}
    </section>
  )
}

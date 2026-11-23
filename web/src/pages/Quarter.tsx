import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { PlanningPrompt } from '../components/PlanningPrompt'
import { goalsApi, type Goal, type KeyResult } from '../api'
import { Icon } from '../icons'
import { periodDay, quarterSpan } from '../format'
import { useToast } from '../components/Toast'
import { AddGoalDialog, Dot } from '../components/goals'
import { colorVar, PACE_LABEL, paceStatus, pct, useGoals } from '../goals'

const krShare = (k: KeyResult) => (k.target ? Math.min(k.current / k.target, 1) : 0)
const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0)

/** Update a key result's current value, moving the goal's progress before the server answers. */
function useEditCurrent() {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: ({ kr, current }: { kr: KeyResult; current: number }) => goalsApi.editKeyResult(kr.id, { current }),
    onMutate: async ({ kr, current }) => {
      await qc.cancelQueries({ queryKey: ['goals', 'quarter'] })
      const before = qc.getQueryData<Goal[]>(['goals', 'quarter'])
      qc.setQueryData<Goal[]>(['goals', 'quarter'], (goals) =>
        goals?.map((g) => {
          if (!g.key_results.some((k) => k.id === kr.id)) return g
          const key_results = g.key_results.map((k) => (k.id === kr.id ? { ...k, current } : k))
          const progress = mean(key_results.map(krShare))
          return { ...g, key_results, progress, pace_status: g.pace === null ? null : paceStatus(progress, g.pace) }
        }),
      )
      return { before }
    },
    onError: (err, _v, ctx) => {
      qc.setQueryData(['goals', 'quarter'], ctx?.before)
      toast(err.message)
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['goals'] }),
  })
}

function KrRow({ kr, color, onSave }: { kr: KeyResult; color: number | null; onSave: (current: number) => void }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState('')
  const save = () => {
    setEditing(false)
    const n = Number(value)
    if (value.trim() !== '' && Number.isFinite(n) && n !== kr.current) onSave(n)
  }
  return (
    <div className="kr">
      <span>{kr.title}</span>
      <div className="meter">
        <i style={{ width: `${krShare(kr) * 100}%`, background: colorVar(color) }} />
      </div>
      {editing ? (
        <input
          className="num"
          type="number"
          step="any"
          autoFocus
          aria-label={`Current value for ${kr.title}`}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => {
            if (e.key === 'Enter') save()
            if (e.key === 'Escape') setEditing(false)
          }}
        />
      ) : (
        <button
          className="num"
          title="Update the current value"
          onClick={() => {
            setValue(String(kr.current))
            setEditing(true)
          }}
        >
          {kr.current} / {kr.target}
          {kr.unit ? ` ${kr.unit}` : ''}
        </button>
      )}
    </div>
  )
}

function GoalCard({ goal, theme, onSave }: { goal: Goal; theme?: Goal; onSave: (kr: KeyResult, current: number) => void }) {
  return (
    <div className="goal">
      <div>
        <h3>
          <Dot color={goal.color} />
          {goal.title}
        </h3>
        {theme && (
          <p className="support" style={{ marginBottom: 6 }}>
            Supports{' '}
            <a className="link" href="#year">
              {theme.title}
            </a>
          </p>
        )}
        {goal.key_results.map((k) => (
          <KrRow key={k.id} kr={k} color={goal.color} onSave={(current) => onSave(k, current)} />
        ))}
      </div>
      <aside>
        {goal.pace_status && (
          <span className={`chip ${PACE_LABEL[goal.pace_status][0]}`} data-testid={`pace-${goal.id}`}>
            {PACE_LABEL[goal.pace_status][1]}
          </span>
        )}
        <p className="figure" style={{ marginTop: 10 }} data-testid={`progress-${goal.id}`}>
          {pct(goal.progress)}
          <small>%</small>
        </p>
        <div className="pace">
          <i style={{ width: `${pct(goal.progress)}%`, background: colorVar(goal.color) }} />
          {goal.pace !== null && <em style={{ left: `${pct(goal.pace)}%` }} />}
        </div>
      </aside>
    </div>
  )
}

/** This quarter: up to five goals, each with key results you update in place. */
export function QuarterPage({ today }: { today: string }) {
  const goals = useGoals('quarter')
  const themes = useGoals('year')
  const edit = useEditCurrent()
  const [adding, setAdding] = useState(false)
  const q = quarterSpan(today)
  const [n, of] = periodDay(q.start, q.end, today)
  const list = goals.data ?? []
  const themeById = new Map((themes.data ?? []).map((t) => [t.id, t]))

  return (
    <>
      <div className="pagehead">
        <div>
          <div className="over kicker" style={{ color: 'var(--rust)' }}>
            <Icon name="quarter" />
            {q.label} · {q.from} to {q.to}
          </div>
          <h1>This quarter</h1>
        </div>
        <span>
          Day {n} of {of}
        </span>
      </div>
      <PlanningPrompt />
      <p className="lead">
        Up to five goals, each with one to three measurable results. Click a number to update it. The small tick on each bar marks where you should be today, {Math.round((n / of) * 100)}% through the quarter.
      </p>
      <section className="card">
        {list.map((g) => (
          <GoalCard key={g.id} goal={g} theme={themeById.get(g.parent_id ?? -1)} onSave={(kr, current) => edit.mutate({ kr, current })} />
        ))}
        {goals.isSuccess && list.length === 0 && <p className="empty">No goals for this quarter yet.</p>}
        {list.length < 5 && (
          <div className="foot">
            <span>
              {list.length} of 5 goals
            </span>
            <button className="link" onClick={() => setAdding(true)} disabled={!themes.data?.length} title={themes.data?.length ? undefined : 'Add a year theme first'}>
              <Icon name="plus" />
              Add a goal
            </button>
          </div>
        )}
      </section>
      {adding && <AddGoalDialog horizon="quarter" parents={themes.data ?? []} onClose={() => setAdding(false)} />}
    </>
  )
}

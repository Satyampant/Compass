import { useState } from 'react'
import type { Goal, GoalIn, Horizon } from '../api'
import { COLORS, colorVar, HORIZON_NAMES, PARENT, useConfirmDraft, useCreateGoal, useDeleteGoal } from '../goals'
import { Dialog } from './Dialog'

export function Dot({ color }: { color: number | null | undefined }) {
  return <i className="dot" style={{ background: colorVar(color) }} />
}

export function GoalTag({ goal }: { goal: Goal | undefined }) {
  if (!goal) return null
  return (
    <span className="gtag">
      <Dot color={goal.color} />
      {goal.short || goal.title}
    </span>
  )
}

type KrDraft = { title: string; target: string; unit: string }
const emptyKr = (): KrDraft => ({ title: '', target: '', unit: '' })

/** Fields for one new goal. Used by the add dialog and by guided setup. */
export function GoalFields({ horizon, parents, onSave, saving, error, submitLabel = 'Save' }: {
  horizon: Horizon
  parents: Goal[]
  onSave: (goal: GoalIn) => void
  saving?: boolean
  error?: string
  submitLabel?: string
}) {
  const [title, setTitle] = useState('')
  const [parentId, setParentId] = useState<number | ''>(parents.length === 1 ? parents[0].id : '')
  const [short, setShort] = useState('')
  const [color, setColor] = useState(1)
  const [due, setDue] = useState('')
  const [krs, setKrs] = useState<KrDraft[]>([emptyKr()])
  const parentHorizon = PARENT[horizon]
  const setKr = (i: number, patch: Partial<KrDraft>) => setKrs(krs.map((k, j) => (j === i ? { ...k, ...patch } : k)))

  const submit = () => {
    const goal: GoalIn = { horizon, title: title.trim(), parent_id: parentId || null }
    if (horizon === 'year' || horizon === 'quarter') goal.short = short.trim() || null
    if (horizon === 'quarter') {
      goal.color = color
      goal.key_results = krs.filter((k) => k.title.trim()).map((k) => ({ title: k.title.trim(), target: Number(k.target) || 1, unit: k.unit.trim() }))
    }
    if (horizon === 'month') goal.due_date = due || null
    onSave(goal)
  }

  return (
    <form
      className="goalform"
      onSubmit={(e) => {
        e.preventDefault()
        if (title.trim()) submit()
      }}
    >
      <label>
        <span className="kicker">{HORIZON_NAMES[horizon]}</span>
        <input type="text" aria-label={`${HORIZON_NAMES[horizon]} title`} autoFocus value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      {parentHorizon && (
        <label>
          <span className="kicker">Supports</span>
          <select aria-label="Parent goal" value={parentId} onChange={(e) => setParentId(Number(e.target.value) || '')}>
            <option value="">Choose a {HORIZON_NAMES[parentHorizon].toLowerCase()}</option>
            {parents.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
        </label>
      )}
      {(horizon === 'year' || horizon === 'quarter') && (
        <label>
          <span className="kicker">Short label</span>
          <input type="text" aria-label="Short label" placeholder={horizon === 'year' ? 'Company, Craft, Life' : 'Backtest'} maxLength={24} value={short} onChange={(e) => setShort(e.target.value)} />
        </label>
      )}
      {horizon === 'quarter' && (
        <>
          <div className="swatches" role="radiogroup" aria-label="Colour">
            {COLORS.map((c) => (
              <button type="button" key={c} role="radio" aria-checked={color === c} aria-label={`Colour ${c}`} style={{ background: colorVar(c) }} onClick={() => setColor(c)} />
            ))}
          </div>
          <span className="kicker">Key results, one to three</span>
          {krs.map((k, i) => (
            <div className="krrow" key={i}>
              <input type="text" aria-label={`Key result ${i + 1}`} placeholder="Engine parity on strategies" value={k.title} onChange={(e) => setKr(i, { title: e.target.value })} />
              <input type="number" aria-label={`Target ${i + 1}`} placeholder="Target" min={0} step="any" value={k.target} onChange={(e) => setKr(i, { target: e.target.value })} />
              <input type="text" aria-label={`Unit ${i + 1}`} placeholder="Unit" value={k.unit} onChange={(e) => setKr(i, { unit: e.target.value })} />
            </div>
          ))}
          {krs.length < 3 && (
            <button type="button" className="link" onClick={() => setKrs([...krs, emptyKr()])}>
              Add a key result
            </button>
          )}
        </>
      )}
      {horizon === 'month' && (
        <label>
          <span className="kicker">Due date</span>
          <input type="date" aria-label="Due date" value={due} onChange={(e) => setDue(e.target.value)} />
        </label>
      )}
      {error && <p className="dialog-error">{error}</p>}
      <div className="actions">
        <button className="btn primary" disabled={saving || !title.trim()}>
          {submitLabel}
        </button>
      </div>
    </form>
  )
}

export function AddGoalDialog({ horizon, parents, onClose, on, title }: { horizon: Horizon; parents: Goal[]; onClose: () => void; on?: string; title?: string }) {
  const create = useCreateGoal(onClose)
  return (
    <Dialog title={title ?? `Add a ${HORIZON_NAMES[horizon].toLowerCase()}`} onClose={onClose}>
      <GoalFields horizon={horizon} parents={parents} onSave={(g) => create.mutate({ ...g, on })} saving={create.isPending} error={create.error?.message} />
    </Dialog>
  )
}

/** A goal waiting for its parent: drafted by the review, or left behind by a deleted goal. */
export function DraftRow({ goal, parents, why }: { goal: Goal; parents: Goal[]; why: string }) {
  const confirm = useConfirmDraft()
  const parentName = HORIZON_NAMES[PARENT[goal.horizon]!].toLowerCase()
  return (
    <div className="decide">
      <span className="taskbody">
        <span className="title">{goal.title}</span>
        <span className="sub">
          <span className="chip">{why}</span>
        </span>
      </span>
      <select aria-label={`Parent for ${goal.title}`} value="" onChange={(e) => e.target.value && confirm.mutate({ goal, parent_id: Number(e.target.value) })}>
        <option value="">Choose the {parentName} it serves</option>
        {parents.map((p) => (
          <option key={p.id} value={p.id}>
            {p.title}
          </option>
        ))}
      </select>
    </div>
  )
}

export function DeleteGoal({ goal }: { goal: Goal }) {
  const remove = useDeleteGoal()
  return (
    <button type="button" className="link quiet" aria-label={`Delete ${goal.title}`} onClick={() => remove.mutate(goal)}>
      Delete
    </button>
  )
}

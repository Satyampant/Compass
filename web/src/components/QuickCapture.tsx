import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import { ageDays } from '../format'
import { Dialog } from './Dialog'
import { useToast } from './Toast'
import { GoalPicker } from './GoalPicker'
import { useHasGoals } from '../goals'

export type CaptureKind = 'learn' | 'task' | 'note'

const KINDS: [CaptureKind, string][] = [
  ['learn', 'Learn later'],
  ['task', 'Task'],
  ['note', 'Note'],
]
const PROMPTS: Record<CaptureKind, [string, string, string]> = {
  learn: ['A link or what you want to learn', 'Paste a link, or e.g. How Kubernetes schedules a Pod', 'Save to queue'],
  task: ['What needs doing?', 'e.g. Send the metrics pack', 'Add to today'],
  note: ['What is on your mind?', 'e.g. Idea for the stock page', 'Save note'],
}

/** C, paste, Enter: save a link, a task or a note without leaving the current screen. */
export function QuickCapture({ initial, onClose }: { initial: CaptureKind; onClose: () => void }) {
  const [kind, setKind] = useState<CaptureKind>(initial)
  const [text, setText] = useState('')
  const [minutes, setMinutes] = useState(25)
  const [goalId, setGoalId] = useState<number | null>(null)
  const [reason, setReason] = useState('')
  const hasGoals = useHasGoals()
  const toast = useToast()
  const qc = useQueryClient()
  const save = useMutation({
    mutationFn: async () => {
      if (kind === 'task') {
        await api.addTask(text.trim(), minutes, goalId)
        return 'Added to today'
      }
      const r = await api.capture(text.trim(), kind, kind === 'learn' ? { goal_id: goalId, reason: reason.trim() } : {})
      if (r.outcome === 'duplicate' && r.first_saved_at) {
        const d = ageDays(r.first_saved_at)
        return `Already saved ${d <= 0 ? 'earlier today' : d === 1 ? 'yesterday' : `${d} days ago`}. It is now top of today's list.`
      }
      return r.outcome === 'note' ? 'Note saved' : 'Saved. It returns in 3 days if untouched.'
    },
    onSuccess: (message) => {
      qc.invalidateQueries()
      toast(message)
      onClose()
    },
  })
  const [label, placeholder, button] = PROMPTS[kind]
  return (
    <Dialog title="Quick capture" onClose={onClose}>
      <div className="strip" role="radiogroup" aria-label="Capture type">
        {KINDS.map(([k, name]) => (
          <button key={k} type="button" role="radio" aria-checked={k === kind} className={`soft ${k === kind ? 'selected' : ''}`} onClick={() => setKind(k)}>
            {name}
          </button>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (text.trim()) save.mutate()
        }}
      >
        <label className="q" htmlFor="ctitle">
          {label}
        </label>
        <input type="text" id="ctitle" autoFocus required maxLength={2000} placeholder={placeholder} value={text} onChange={(e) => setText(e.target.value)} />
        {kind === 'task' && (
          <>
            <label className="q" htmlFor="cmin">
              Minutes
            </label>
            <input type="number" id="cmin" min={1} max={600} value={minutes} onChange={(e) => setMinutes(Number(e.target.value) || 25)} />
          </>
        )}
        {kind !== 'note' && hasGoals && (
          <>
            <label className="q" htmlFor="cgoal">
              Goal <span className="muted">optional</span>
            </label>
            <GoalPicker id="cgoal" value={goalId} onChange={setGoalId} />
          </>
        )}
        {kind === 'learn' && (
          <>
            <label className="q" htmlFor="creason">
              Why save it? <span className="muted">optional</span>
            </label>
            <input type="text" id="creason" maxLength={200} placeholder="One line" value={reason} onChange={(e) => setReason(e.target.value)} />
          </>
        )}
        {save.error && <p className="dialog-error">{save.error.message}</p>}
        <div className="actions">
          <button className="btn primary" disabled={save.isPending}>
            {button}
          </button>
        </div>
      </form>
    </Dialog>
  )
}

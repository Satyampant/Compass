import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { dayApi, type Decision, type DecisionAction, type Task } from '../api'
import { day, isoDay } from '../format'
import { Dialog } from './Dialog'
import { TagLabel } from './GoalPicker'
import { useToast } from './Toast'

const CHOICES: [DecisionAction, string][] = [
  ['tomorrow', 'Tomorrow'],
  ['reschedule', 'Pick a day'],
  ['drop', 'Drop'],
]

function DecideRow({ task, decision, minDate, onDecide }: { task: Task; decision?: Decision; minDate: string; onDecide: (d: Decision) => void }) {
  return (
    <div className="decide">
      <span className="taskbody">
        <span className="title">{task.title}</span>
        <span className="sub">
          <TagLabel tag={task.tag} />
        </span>
      </span>
      <div className="strip" role="radiogroup" aria-label={`Decision for ${task.title}`}>
        {CHOICES.map(([action, label]) => (
          <button
            key={action}
            type="button"
            role="radio"
            aria-checked={decision?.action === action}
            className={`soft ${decision?.action === action ? 'selected' : ''}`}
            onClick={() => onDecide({ task_id: task.id, action, to: action === 'reschedule' ? (decision?.to ?? minDate) : undefined })}
          >
            {label}
          </button>
        ))}
      </div>
      {decision?.action === 'reschedule' && (
        <input type="date" aria-label={`New day for ${task.title}`} min={minDate} value={decision.to} onChange={(e) => onDecide({ ...decision, to: e.target.value })} />
      )}
    </div>
  )
}

/** Plan tomorrow: one decision for each open task, then the top three. */
export function PlanDialog({ today, topLimit, onClose }: { today: string; topLimit: number; onClose: () => void }) {
  const next = day(today)
  next.setDate(next.getDate() + 1)
  const tomorrow = isoDay(next)
  const draft = useQuery({ queryKey: ['plan', tomorrow], queryFn: () => dayApi.draft(tomorrow) })
  const [step, setStep] = useState(0)
  const [decisions, setDecisions] = useState<Record<number, Decision>>({})
  const [top, setTop] = useState<number[] | null>(null)
  const qc = useQueryClient()
  const toast = useToast()
  const commit = useMutation({
    mutationFn: () => dayApi.plan(tomorrow, Object.values(decisions), chosen),
    onSuccess: () => {
      qc.invalidateQueries()
      toast('Tomorrow is planned')
      onClose()
    },
  })
  if (!draft.data) return null
  const open = draft.data.open
  const undecided = open.filter((t) => !decisions[t.id] || (decisions[t.id].action === 'reschedule' && !decisions[t.id].to)).length
  const candidates = [...draft.data.planned, ...open.filter((t) => decisions[t.id]?.action === 'tomorrow')]
  const chosen = top ?? draft.data.planned.filter((t) => t.top_rank).map((t) => t.id)
  const pick = (id: number) => setTop(chosen.includes(id) ? chosen.filter((x) => x !== id) : chosen.length < topLimit ? [...chosen, id] : chosen)
  const stepOne = step === 0 && open.length > 0

  return (
    <Dialog title="Plan tomorrow" onClose={onClose}>
      {stepOne ? (
        <>
          <p className="support">
            <b>Step 1 of 2.</b> {open.length} open task{open.length === 1 ? '' : 's'}. Move each to tomorrow, pick another day, or drop it. Nothing carries over on its own.
          </p>
          {open.map((t) => (
            <DecideRow key={t.id} task={t} decision={decisions[t.id]} minDate={tomorrow} onDecide={(d) => setDecisions({ ...decisions, [t.id]: d })} />
          ))}
          <div className="actions">
            <button className="btn primary" disabled={undecided > 0} onClick={() => setStep(1)}>
              {undecided ? `${undecided} left to decide` : 'Next: top three'}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="support">
            <b>{open.length ? 'Step 2 of 2.' : 'Top three.'}</b> Choose up to {topLimit} for tomorrow, in order. The first becomes your focus.
          </p>
          <div className="picklist">
            {candidates.map((t) => {
              const rank = chosen.indexOf(t.id) + 1
              return (
                <button key={t.id} type="button" className={`soft ${rank ? 'selected' : ''}`} aria-pressed={!!rank} onClick={() => pick(t.id)}>
                  <span className="rankno">{rank || ''}</span>
                  {t.title}
                </button>
              )
            })}
            {candidates.length === 0 && <p className="empty">Nothing on tomorrow yet. Add tasks after planning.</p>}
          </div>
          {commit.error && <p className="dialog-error">{commit.error.message}</p>}
          <div className="actions">
            {open.length > 0 && (
              <button className="btn outline" onClick={() => setStep(0)}>
                Back
              </button>
            )}
            <button className="btn primary" disabled={commit.isPending} onClick={() => commit.mutate()}>
              Commit plan
            </button>
          </div>
        </>
      )}
    </Dialog>
  )
}

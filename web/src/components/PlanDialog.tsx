import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { dayApi, type Block, type Decision, type DecisionAction, type Placement, type Task } from '../api'
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

const hm = (iso: string) => new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })

/** The day's meetings and learning blocks, then the proposed task blocks. Task times can be changed. */
function PlaceStep({ tomorrow, fixed, tasks, placements, onChange }: { tomorrow: string; fixed: Block[]; tasks: Task[]; placements: Placement[]; onChange: (p: Placement[]) => void }) {
  const title = (id: number) => tasks.find((t) => t.id === id)?.title ?? ''
  type Row = { fixed?: Block; placed?: Placement }
  const rows: Row[] = [...fixed.map((b) => ({ fixed: b })), ...placements.map((p) => ({ placed: p }))]
  const unplaced = tasks.filter((t) => !placements.some((p) => p.task_id === t.id))
  const moveTo = (p: Placement, time: string) => {
    const start = new Date(`${tomorrow}T${time}:00`)
    const end = new Date(start.getTime() + (new Date(p.end).getTime() - new Date(p.start).getTime()))
    onChange(placements.map((x) => (x === p ? { ...p, start: start.toISOString(), end: end.toISOString() } : x)))
  }
  return (
    <div className="section">
      {rows.map((r) =>
        r.fixed ? (
          <div className="slot" key={`f${r.fixed.id}`}>
            <span className="t">
              {hm(r.fixed.start)} – {hm(r.fixed.end)}
            </span>
            <span className="name muted">{r.fixed.title}</span>
            <span className="chip">{r.fixed.source === 'calendar' ? 'Meeting' : 'Learning'}</span>
          </div>
        ) : (
          <div className="slot" key={`p${r.placed!.task_id}`}>
            <input type="time" aria-label={`Start of ${title(r.placed!.task_id)}`} step={900} value={hm(r.placed!.start)} onChange={(e) => e.target.value && moveTo(r.placed!, e.target.value)} />
            <span className="name">{title(r.placed!.task_id)}</span>
            <button className="link" aria-label={`Leave ${title(r.placed!.task_id)} unscheduled`} onClick={() => onChange(placements.filter((x) => x !== r.placed))}>
              Remove
            </button>
          </div>
        ),
      )}
      {unplaced.length > 0 && <p className="support">No block: {unplaced.map((t) => t.title).join(', ')}. They stay on tomorrow’s list.</p>}
    </div>
  )
}

/** Plan tomorrow: one decision for each open task, the top three, then blocks around meetings. */
export function PlanDialog({ today, topLimit, onClose }: { today: string; topLimit: number; onClose: () => void }) {
  const next = day(today)
  next.setDate(next.getDate() + 1)
  const tomorrow = isoDay(next)
  const draft = useQuery({ queryKey: ['plan', tomorrow], queryFn: () => dayApi.draft(tomorrow) })
  const [step, setStep] = useState<'decide' | 'top' | 'place' | null>(null)
  const [decisions, setDecisions] = useState<Record<number, Decision>>({})
  const [top, setTop] = useState<number[] | null>(null)
  const [placements, setPlacements] = useState<Placement[]>([])
  const qc = useQueryClient()
  const toast = useToast()
  const commit = useMutation({
    mutationFn: () => dayApi.plan(tomorrow, Object.values(decisions), chosen, placements),
    onSuccess: () => {
      qc.invalidateQueries()
      toast('Tomorrow is planned')
      onClose()
    },
  })
  const propose = useMutation({
    mutationFn: (ids: number[]) => dayApi.propose(tomorrow, ids),
    onSuccess: (p) => {
      setPlacements(p)
      setStep('place')
    },
    onError: (err) => toast(err.message),
  })
  if (!draft.data) return null
  const open = draft.data.open
  const current = step ?? (open.length ? 'decide' : 'top')
  const steps = open.length ? 3 : 2
  const n = (s: string) => (open.length ? { decide: 1, top: 2, place: 3 } : { top: 1, place: 2 })[s as 'top']
  const undecided = open.filter((t) => !decisions[t.id] || (decisions[t.id].action === 'reschedule' && !decisions[t.id].to)).length
  const candidates = [...draft.data.planned, ...open.filter((t) => decisions[t.id]?.action === 'tomorrow')]
  const chosen = top ?? draft.data.planned.filter((t) => t.top_rank).map((t) => t.id)
  const pick = (id: number) => setTop(chosen.includes(id) ? chosen.filter((x) => x !== id) : chosen.length < topLimit ? [...chosen, id] : chosen)
  const ordered = [...chosen, ...candidates.map((t) => t.id).filter((id) => !chosen.includes(id))]
  const fixed = draft.data.blocks.filter((b) => b.kind !== 'task')

  return (
    <Dialog title="Plan tomorrow" onClose={onClose}>
      <p className="support">
        <b>
          Step {n(current)} of {steps}.
        </b>{' '}
        {current === 'decide' && `${open.length} open task${open.length === 1 ? '' : 's'}. Move each to tomorrow, pick another day, or drop it. Nothing carries over on its own.`}
        {current === 'top' && `Choose up to ${topLimit} for tomorrow, in order. The first becomes your focus.`}
        {current === 'place' && 'Blocks go around your meetings: the first task into the longest free morning stretch. Change any start time.'}
      </p>
      {current === 'decide' && (
        <>
          {open.map((t) => (
            <DecideRow key={t.id} task={t} decision={decisions[t.id]} minDate={tomorrow} onDecide={(d) => setDecisions({ ...decisions, [t.id]: d })} />
          ))}
          <div className="actions">
            <button className="btn primary" disabled={undecided > 0} onClick={() => setStep('top')}>
              {undecided ? `${undecided} left to decide` : 'Next: top three'}
            </button>
          </div>
        </>
      )}
      {current === 'top' && (
        <>
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
          <div className="actions">
            {open.length > 0 && (
              <button className="btn outline" onClick={() => setStep('decide')}>
                Back
              </button>
            )}
            <button className="btn primary" disabled={propose.isPending} onClick={() => propose.mutate(ordered)}>
              Next: place blocks
            </button>
          </div>
        </>
      )}
      {current === 'place' && (
        <>
          <PlaceStep tomorrow={tomorrow} fixed={fixed} tasks={candidates} placements={placements} onChange={setPlacements} />
          {commit.error && <p className="dialog-error">{commit.error.message}</p>}
          <div className="actions">
            <button className="btn outline" onClick={() => setStep('top')}>
              Back
            </button>
            <button className="btn primary" disabled={commit.isPending} onClick={() => commit.mutate()}>
              Commit plan
            </button>
          </div>
        </>
      )}
    </Dialog>
  )
}

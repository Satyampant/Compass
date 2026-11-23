import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Item } from '../api'
import { Icon } from '../icons'
import { SOURCE_NAMES, ageDays, slotLabel } from '../format'
import { useItemTransition } from '../useTransition'
import { Dialog } from './Dialog'
import { GoalPicker } from './GoalPicker'
import { useToast } from './Toast'
import { useHasGoals } from '../goals'

/** Link an item to a goal, or untie it. Linked items never expire. */
/** Add minutes to an item in Learning, so the next block picks up where you stopped. */
function useSaveProgress(item: Item) {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (minutes: number) => api.saveProgress(item.id, minutes),
    onSuccess: (r) => {
      qc.invalidateQueries()
      toast(`Progress saved: ${r.progress_min} of ${r.estimate_min} min`)
    },
    onError: (err) => toast(err.message),
  })
}

function useLinkGoal(item: Item) {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (goal_id: number | null) => api.editItem(item.id, { goal_id }),
    onSuccess: (r) => {
      qc.invalidateQueries()
      toast(r.goal_id ? 'Linked. It will wait for a learning block and not expire.' : 'Goal removed')
    },
    onError: (err) => toast(err.message),
  })
}

function where(item: Item): string {
  const d = ageDays(item.captured_at)
  switch (item.state) {
    case 'inbox':
      return d <= 0 ? 'Saved today' : `Saved ${d} day${d === 1 ? '' : 's'} ago`
    case 'booked':
      return `Booked for ${slotLabel(item.booked_for!)}`
    case 'learning':
      return 'In progress'
    default:
      return item.note || 'Learned'
  }
}

/** The title, with a way to rename it, for example when the page title could not be fetched. */
function RenameTitle({ item }: { item: Item }) {
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(item.title)
  const qc = useQueryClient()
  const toast = useToast()
  const save = useMutation({
    mutationFn: () => api.editItem(item.id, { title: title.trim() }),
    onSuccess: () => {
      setEditing(false)
      qc.invalidateQueries()
    },
    onError: (err) => toast(err.message),
  })
  if (!editing)
    return (
      <div className="titlerow">
        <h3 style={{ marginTop: 8 }}>{item.title}</h3>
        <button className="link quiet" onClick={() => setEditing(true)}>
          Rename
        </button>
      </div>
    )
  return (
    <form
      className="addtask"
      onSubmit={(e) => {
        e.preventDefault()
        if (title.trim()) save.mutate()
      }}
    >
      <input type="text" aria-label="Item title" autoFocus value={title} onChange={(e) => setTitle(e.target.value)} />
      <button className="btn outline">Save</button>
    </form>
  )
}

/** A learning item with only the moves that are valid for its state. */
export function ItemDialog({ item, onClose, onStart }: { item: Item; onClose: () => void; onStart?: () => void }) {
  const move = useItemTransition()
  const link = useLinkGoal(item)
  const hasGoals = useHasGoals()
  const progress = useSaveProgress(item)
  const [spent, setSpent] = useState(25)
  const [goalId, setGoalId] = useState(item.goal_id)
  const [when, setWhen] = useState('')
  const [note, setNote] = useState('')
  const can = (a: string) => item.actions.includes(a as Item['actions'][number])
  const run = (action: Item['actions'][number], extra = {}) => {
    move.mutate({ id: item.id, action, ...extra })
    onClose()
  }
  return (
    <Dialog title="Learning item" onClose={onClose}>
      <p className="kicker">
        {SOURCE_NAMES[item.source_type] ?? item.source_type} · {item.estimate_min} min
      </p>
      <RenameTitle item={item} />
      {item.url && (
        <p className="support">
          <a className="link" href={item.url} target="_blank" rel="noreferrer">
            Open link <Icon name="arrow" />
          </a>
        </p>
      )}
      {item.reason && <p className="support">{item.reason}</p>}
      <p className="support" style={{ marginTop: 12 }}>
        {where(item)}
      </p>
      {item.state !== 'learned' && hasGoals && (
        <>
          <label className="q" htmlFor="igoal">
            Goal
          </label>
          <GoalPicker
            id="igoal"
            value={goalId}
            onChange={(g) => {
              setGoalId(g)
              link.mutate(g)
            }}
          />
        </>
      )}
      {can('book') && (
        <>
          <label className="q" htmlFor="bwhen">
            Or pick a time
          </label>
          <input id="bwhen" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />
        </>
      )}
      {item.state === 'learning' && (
        <>
          <label className="q" htmlFor="bspent">
            Minutes spent so far <span className="muted">{item.progress_min} of {item.estimate_min} saved</span>
          </label>
          <div className="addtask">
            <input id="bspent" type="number" min={1} max={600} value={spent} onChange={(e) => setSpent(Number(e.target.value) || 25)} />
            <button className="btn outline" onClick={() => progress.mutate(spent)}>
              Save progress
            </button>
          </div>
        </>
      )}
      {can('finish') && (
        <>
          <label className="q" htmlFor="bnote">
            What did you take from it, or do with it? <span className="muted">One line, required</span>
          </label>
          <textarea id="bnote" value={note} onChange={(e) => setNote(e.target.value)} />
        </>
      )}
      <div className="actions">
        {can('book') && (
          <button className="btn primary" onClick={() => run('book', when ? { booked_for: new Date(when).toISOString() } : {})}>
            <Icon name="plus" />
            {when ? 'Book this time' : 'Book next learning block'}
          </button>
        )}
        {can('start') && (
          <button
            className="btn primary"
            onClick={() => {
              if (onStart) {
                onClose()
                onStart()
              } else run('start')
            }}
          >
            <Icon name="play" />
            Start now
          </button>
        )}
        {can('finish') && (
          <button className="btn primary" disabled={!note.trim()} onClick={() => run('finish', { note: note.trim() })}>
            <Icon name="check" />
            Mark learned
          </button>
        )}
        {can('return') && (
          <button className="btn outline" onClick={() => run('return')}>
            Return to booked
          </button>
        )}
        {can('unbook') && (
          <button className="btn outline" onClick={() => run('unbook')}>
            Back to inbox
          </button>
        )}
        {can('let_go') && (
          <button className="btn outline" onClick={() => run('let_go')}>
            Let go
          </button>
        )}
      </div>
    </Dialog>
  )
}

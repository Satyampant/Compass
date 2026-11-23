import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Task, type Today } from '../api'
import { Icon } from '../icons'
import { dur } from '../format'
import { Dialog } from './Dialog'
import { TagLabel } from './GoalPicker'
import { useToast } from './Toast'
import type { CaptureKind } from './QuickCapture'

function useToggleTask() {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (t: Task) => api.editTask(t.id, { done: !t.done_at }),
    onMutate: async (t) => {
      await qc.cancelQueries({ queryKey: ['today'] })
      const before = qc.getQueryData<Today>(['today'])
      qc.setQueryData<Today>(['today'], (d) => d && { ...d, tasks: d.tasks.map((x) => (x.id === t.id ? { ...x, done_at: x.done_at ? null : new Date().toISOString() } : x)) })
      return { before }
    },
    onError: (err, _t, ctx) => {
      qc.setQueryData(['today'], ctx?.before)
      toast(err.message)
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['today'] }),
  })
}

function useSetTop(day: string) {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (ids: number[]) => api.setTop(day, ids),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['today'] }),
    onError: (err) => toast(err.message),
  })
}

function TaskRow({ task, ranked, onToggle, onOpen, onRank }: { task: Task; ranked: boolean; onToggle: () => void; onOpen: () => void; onRank: () => void }) {
  const done = !!task.done_at
  return (
    <div className={`task ${done ? 'done' : ''}`}>
      <button className="check" aria-pressed={done} aria-label={`${done ? 'Reopen' : 'Complete'} ${task.title}`} onClick={onToggle}>
        <Icon name="check" />
      </button>
      <button className="taskbody" onClick={onOpen}>
        <span className="title">{task.title}</span>
        <span className="sub">
          <TagLabel tag={task.tag} />
        </span>
      </button>
      <button className={`rank ${ranked ? 'on' : ''}`} aria-pressed={ranked} aria-label={`${ranked ? 'Remove from' : 'Add to'} top three: ${task.title}`} title={ranked ? 'Remove from top three' : 'Add to top three'} onClick={onRank}>
        <Icon name="mark" />
      </button>
      <span className="chip">
        <Icon name="clock" />
        {dur(task.estimate_min)}
      </span>
    </div>
  )
}

function AddTask() {
  const [title, setTitle] = useState('')
  const [minutes, setMinutes] = useState(25)
  const qc = useQueryClient()
  const add = useMutation({
    mutationFn: () => api.addTask(title.trim(), minutes),
    onSuccess: () => {
      setTitle('')
      qc.invalidateQueries({ queryKey: ['today'] })
    },
  })
  return (
    <form
      className="addtask"
      onSubmit={(e) => {
        e.preventDefault()
        if (title.trim()) add.mutate()
      }}
    >
      <input type="text" aria-label="New task" placeholder="Add a task for today" value={title} onChange={(e) => setTitle(e.target.value)} />
      <input type="number" aria-label="Minutes" min={1} max={600} value={minutes} onChange={(e) => setMinutes(Number(e.target.value) || 25)} />
      <button className="btn outline">Add</button>
    </form>
  )
}

/** Ranking one more task than the limit asks which ranked task it replaces. */
function ReplaceDialog({ task, top, onPick, onClose }: { task: Task; top: Task[]; onPick: (replaced: Task) => void; onClose: () => void }) {
  return (
    <Dialog title="Which one does it replace?" onClose={onClose}>
      <p className="support">
        “{task.title}” would be a fourth top priority. Choose the one it replaces. That one stays on today’s list.
      </p>
      <div className="actions" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
        {top.map((t) => (
          <button key={t.id} className="btn outline" onClick={() => onPick(t)}>
            {t.top_rank}. {t.title}
          </button>
        ))}
      </div>
    </Dialog>
  )
}

/** Today's tasks: the ranked top three first, then the smaller things. */
export function TodayPlan({ data, onCapture, onOpen }: { data: Today; onCapture: (k: CaptureKind) => void; onOpen: (id: number) => void }) {
  const toggle = useToggleTask()
  const setTop = useSetTop(data.date)
  const [replacing, setReplacing] = useState<Task | null>(null)
  const isTop = (t: Task) => !!t.top_rank && t.planned_date === data.date
  const top = data.tasks.filter(isTop)
  const rest = data.tasks.filter((t) => !isTop(t))
  const done = data.tasks.filter((t) => t.done_at).length
  const ids = top.map((t) => t.id)

  const rank = (t: Task) => {
    if (isTop(t)) setTop.mutate(ids.filter((id) => id !== t.id))
    else if (top.length < data.top_limit) setTop.mutate([...ids, t.id])
    else setReplacing(t)
  }
  const row = (t: Task) => <TaskRow key={t.id} task={t} ranked={isTop(t)} onToggle={() => toggle.mutate(t)} onOpen={() => onOpen(t.id)} onRank={() => rank(t)} />

  return (
    <section className="card">
      <div className="cardhead">
        <h2>Today’s plan</h2>
        <button className="link" onClick={() => onCapture('task')}>
          <Icon name="plus" />
          Add task
        </button>
      </div>
      {data.tasks.length > 0 && (
        <div className="meterwrap">
          <span>
            {done} / {data.tasks.length} complete
          </span>
          <div className="meter">
            <i style={{ width: `${(done / data.tasks.length) * 100}%` }} />
          </div>
        </div>
      )}
      {top.length > 0 && (
        <>
          <p className="kicker sub-k">Top three</p>
          {top.map(row)}
          {rest.length > 0 && <p className="kicker sub-k">Smaller things</p>}
        </>
      )}
      {rest.map(row)}
      {data.tasks.length === 0 && <p className="empty">Nothing planned yet.</p>}
      <AddTask />
      {replacing && (
        <ReplaceDialog
          task={replacing}
          top={top}
          onClose={() => setReplacing(null)}
          onPick={(old) => {
            setTop.mutate(ids.map((id) => (id === old.id ? replacing.id : id)))
            setReplacing(null)
          }}
        />
      )}
    </section>
  )
}

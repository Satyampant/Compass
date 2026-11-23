import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Item, type Task, type Today } from '../api'
import { Icon, sourceIcon } from '../icons'
import { dur, ageDays, savedAgo, slotLabel } from '../format'
import { ItemDialog } from '../components/ItemDialog'
import { useToast } from '../components/Toast'
import type { CaptureKind } from '../components/QuickCapture'
import { useGoals } from '../goals'

const SPINES = ['var(--g1)', 'var(--g2)', 'var(--g3)', 'var(--g4)', 'var(--g5)']

function greeting(): string {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
}

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

function TaskRow({ task, onToggle }: { task: Task; onToggle: () => void }) {
  const done = !!task.done_at
  return (
    <div className={`task ${done ? 'done' : ''}`}>
      <button className="check" aria-pressed={done} aria-label={`${done ? 'Reopen' : 'Complete'} ${task.title}`} onClick={onToggle}>
        <Icon name="check" />
      </button>
      <span className="taskbody">
        <span className="title">{task.title}</span>
      </span>
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

function RevisitRow({ item, onOpen }: { item: Item; onOpen: () => void }) {
  return (
    <button className="row" onClick={onOpen}>
      <span className="spine" style={{ background: SPINES[item.id % 5] }}>
        <Icon name={sourceIcon(item.source_type)} />
      </span>
      <span style={{ minWidth: 0 }}>
        <span className="title">{item.title}</span>
        <span className="sub">
          <span>{item.estimate_min} min</span>
          <span className={ageDays(item.captured_at) >= 14 ? 'aging' : ''}>{savedAgo(item.captured_at)}</span>
        </span>
      </span>
      <Icon name="right" />
    </button>
  )
}

/** Today: the day's tasks and what is back on your desk. */
export function TodayPage({ onCapture }: { onCapture: (k: CaptureKind) => void }) {
  const { data } = useQuery({ queryKey: ['today'], queryFn: api.today })
  const toggle = useToggleTask()
  const themes = useGoals('year')
  const [openId, setOpenId] = useState<number | null>(null)
  if (!data) return null
  const open = data.revisit.find((i) => i.id === openId)
  const done = data.tasks.filter((t) => t.done_at).length
  const dateLine = new Date(`${data.date}T12:00:00`).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <>
      <div className="pagehead">
        <div>
          <div className="over kicker">
            <Icon name="sun" />
            {dateLine}
          </div>
          <h1>{greeting()}</h1>
        </div>
      </div>
      {themes.isSuccess && themes.data.length === 0 && (
        <section className="card banner welcome">
          <div>
            <p className="kicker">Set your direction</p>
            <h3 style={{ marginTop: 6 }}>Choose this year’s themes, this quarter’s goals and this week’s outcomes</h3>
            <p className="support">A guided setup that takes about fifteen minutes.</p>
          </div>
          <a className="btn primary" href="#setup">
            Start setup
          </a>
        </section>
      )}
      {!data.has_items && (
        <section className="card banner welcome">
          <div>
            <p className="kicker">First step</p>
            <h3 style={{ marginTop: 6 }}>Share your first link to the Compass bot</h3>
            <p className="support">From any app on your phone, share a link to the bot in Telegram. Here, press C and paste.</p>
          </div>
        </section>
      )}
      <div className="cols">
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
          {data.tasks.map((t) => (
            <TaskRow key={t.id} task={t} onToggle={() => toggle.mutate(t)} />
          ))}
          {data.tasks.length === 0 && <p className="empty">Nothing planned yet.</p>}
          <AddTask />
        </section>
        <section className="card">
          <div className="cardhead">
            <h2>Time to revisit</h2>
            <span className="chip">{data.inbox_count} waiting</span>
          </div>
          <p className="support">Saved learning that is back on your desk. Book it or let it go.</p>
          {data.revisit.map((i) => (
            <RevisitRow key={i.id} item={i} onOpen={() => setOpenId(i.id)} />
          ))}
          {data.revisit.length === 0 && <p className="empty">Nothing waiting today.</p>}
          <div className="foot">
            <span>Next learning block: {slotLabel(data.next_slot)}</span>
            <a className="link" href="#learn">
              Open queue <Icon name="arrow" />
            </a>
          </div>
        </section>
      </div>
      {open && <ItemDialog item={open} onClose={() => setOpenId(null)} />}
    </>
  )
}

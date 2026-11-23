import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type Item } from '../api'
import { Icon, sourceIcon } from '../icons'
import { ageDays, savedAgo, slotLabel } from '../format'
import { ItemDialog } from '../components/ItemDialog'
import type { CaptureKind } from '../components/QuickCapture'
import { useGoals } from '../goals'
import { FocusCard } from '../components/Focus'
import { TodayPlan } from '../components/TodayPlan'
import { TaskDialog } from '../components/TaskDialog'

const SPINES = ['var(--g1)', 'var(--g2)', 'var(--g3)', 'var(--g4)', 'var(--g5)']

function greeting(): string {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
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
  const themes = useGoals('year')
  const [openId, setOpenId] = useState<number | null>(null)
  const [taskId, setTaskId] = useState<number | null>(null)
  if (!data) return null
  const open = data.revisit.find((i) => i.id === openId)
  const openTask = data.tasks.find((t) => t.id === taskId)
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
      <FocusCard focus={data.focus} hasTop={data.tasks.some((t) => t.top_rank && t.planned_date === data.date)} onOpen={setTaskId} />
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
        <TodayPlan data={data} onCapture={onCapture} onOpen={setTaskId} />
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
      {openTask && <TaskDialog task={openTask} onClose={() => setTaskId(null)} />}
    </>
  )
}

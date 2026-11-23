import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { DndContext, KeyboardSensor, PointerSensor, useDraggable, useDroppable, useSensor, useSensors, type DragEndEvent } from '@dnd-kit/core'
import { api, weekApi, type DayColumn, type Task, type Week } from '../api'
import { Icon } from '../icons'
import { day } from '../format'
import { useToast } from '../components/Toast'
import { TagLabel } from '../components/GoalPicker'
import { TaskDialog } from '../components/TaskDialog'
import { AddGoalDialog, DraftRow } from '../components/goals'
import { GoalCheck } from './Month'
import { quarterOf, useGoals, useToggleGoal } from '../goals'

const hrs = (min: number) => `${Math.round((min / 60) * 100) / 100}h`

/** Move a task to another day. Both day totals change before the server answers. */
function useMoveTask() {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: ({ task, to }: { task: Task; to: string }) => api.editTask(task.id, { planned_date: to }),
    onMutate: async ({ task, to }) => {
      await qc.cancelQueries({ queryKey: ['week'] })
      const before = qc.getQueryData<Week>(['week'])
      qc.setQueryData<Week>(['week'], (w) => {
        if (!w) return w
        const days = w.days.map((d) => {
          const tasks = d.date === to ? [...d.tasks.filter((t) => t.id !== task.id), { ...task, planned_date: to, top_rank: null }] : d.tasks.filter((t) => t.id !== task.id)
          const planned_min = tasks.reduce((s, t) => s + t.estimate_min, 0)
          return { ...d, tasks, planned_min, over: planned_min > d.capacity_min }
        })
        return { ...w, days }
      })
      return { before }
    },
    onError: (err, _v, ctx) => {
      qc.setQueryData(['week'], ctx?.before)
      toast(err.message)
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['week'] }),
  })
}

function Card({ task, onOpen }: { task: Task; onOpen: () => void }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: task.id, data: { task } })
  const style = transform ? { transform: `translate(${transform.x}px, ${transform.y}px)`, zIndex: 3, position: 'relative' as const } : undefined
  return (
    <button ref={setNodeRef} style={style} className={`kcard ${isDragging ? 'dragging' : ''} ${task.done_at ? 'done' : ''}`} onClick={onOpen} {...listeners} {...attributes}>
      <span className="title">{task.title}</span>
      <span className="sub">
        <TagLabel tag={task.tag} />
        <span>{hrs(task.estimate_min)}</span>
      </span>
    </button>
  )
}

function Column({ col, today, onOpen }: { col: DayColumn; today: string; onOpen: (t: Task) => void }) {
  const { setNodeRef, isOver } = useDroppable({ id: col.date })
  const d = day(col.date)
  const name = `${d.toLocaleDateString('en-GB', { weekday: 'short' })} ${d.getDate()}`
  return (
    <section ref={setNodeRef} className={`col ${isOver ? 'over' : ''} ${col.date === today ? 'today-col' : ''}`} aria-label={name}>
      <div className="colhead">
        {name}
        <span className={col.over ? 'aging' : ''} title={`${hrs(col.capacity_min)} capacity`} data-testid={`hours-${col.date}`}>
          {hrs(col.planned_min)}
        </span>
      </div>
      {col.tasks.length ? col.tasks.map((t) => <Card key={t.id} task={t} onOpen={() => onOpen(t)} />) : <div className="coldrop">Free</div>}
    </section>
  )
}

/** This week: up to three outcomes and a board of seven days against capacity. */
export function WeekPage({ today }: { today: string }) {
  const { data: week } = useQuery({ queryKey: ['week'], queryFn: weekApi.get })
  const outcomes = useGoals('week')
  const months = useGoals('month')
  const quarters = useGoals('quarter')
  const toggle = useToggleGoal('week')
  const move = useMoveTask()
  const [adding, setAdding] = useState(false)
  const [taskId, setTaskId] = useState<number | null>(null)
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }), useSensor(KeyboardSensor))
  if (!week) return null
  const list = outcomes.data ?? []
  const byId = new Map([...(months.data ?? []), ...(quarters.data ?? [])].map((g) => [g.id, g]))
  const openTask = week.days.flatMap((d) => d.tasks).find((t) => t.id === taskId)
  const end = day(week.days[6].date)
  const range = `${day(week.start).getDate()} – ${end.getDate()} ${end.toLocaleDateString('en-GB', { month: 'long' })}`

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    const task = active.data.current?.task as Task
    const to = over?.id as string | undefined
    if (to && to !== task.planned_date) move.mutate({ task, to })
  }

  return (
    <>
      <div className="pagehead">
        <div>
          <div className="over kicker" style={{ color: 'var(--rust)' }}>
            <Icon name="week" />
            {range}
          </div>
          <h1>This week</h1>
        </div>
      </div>
      <section className="card">
        <div className="cardhead">
          <span className="kicker">Weekly outcomes</span>
          <span className={`chip ${week.over ? 'warn' : 'good'}`} data-testid="week-total">
            {hrs(week.planned_min)} planned · {hrs(week.capacity_min)} capacity
          </span>
        </div>
        {week.over && <p className="support aging">This week is planned beyond its capacity. Move or drop something.</p>}
        {list.length > 0 && (
          <div className="meterwrap">
            <span>
              {list.filter((o) => o.done).length} / {list.length} outcomes
            </span>
            <div className="meter">
              <i style={{ width: `${(list.filter((o) => o.done).length / list.length) * 100}%` }} />
            </div>
          </div>
        )}
        {list.map((o) =>
          o.draft ? (
            <DraftRow key={o.id} goal={o} parents={months.data ?? []} why="Needs a milestone" />
          ) : (
            <GoalCheck key={o.id} goal={o} tag={quarterOf(o, byId)} onToggle={() => toggle.mutate(o)} />
          ),
        )}
        {list.length < 3 && (
          <div className="foot">
            <span>{list.length} of 3 outcomes</span>
            <button className="link" onClick={() => setAdding(true)} disabled={!months.data?.length} title={months.data?.length ? undefined : 'Add a month milestone first'}>
              <Icon name="plus" />
              Add an outcome
            </button>
          </div>
        )}
      </section>
      <div className="cardhead section" style={{ marginBottom: 12 }}>
        <h2>Week board</h2>
        <span className="muted" style={{ fontSize: 12 }}>
          Drag a card to another day
        </span>
      </div>
      <DndContext sensors={sensors} onDragEnd={onDragEnd}>
        <div className="board week">
          {week.days.map((d) => (
            <Column key={d.date} col={d} today={today} onOpen={(t) => setTaskId(t.id)} />
          ))}
        </div>
      </DndContext>
      {adding && <AddGoalDialog horizon="week" parents={months.data ?? []} onClose={() => setAdding(false)} />}
      {openTask && <TaskDialog task={openTask} onClose={() => setTaskId(null)} />}
    </>
  )
}

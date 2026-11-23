import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { TagLabel } from '../components/GoalPicker'
import { DndContext, KeyboardSensor, PointerSensor, useDraggable, useDroppable, useSensor, useSensors, type DragEndEvent } from '@dnd-kit/core'
import { api, type Action, type Item, type ItemState } from '../api'
import { Icon } from '../icons'
import { SOURCE_NAMES, ageDays, savedAgo, slotLabel } from '../format'
import { ItemDialog } from '../components/ItemDialog'
import { useToast } from '../components/Toast'
import { useItemTransition } from '../useTransition'

const COLS: [ItemState, string, string][] = [
  ['inbox', 'Inbox', 'Decide within 48 hours'],
  ['booked', 'Booked', 'Has a slot on the calendar'],
  ['learning', 'Learning', 'Picks up where you stopped'],
  ['learned', 'Learned', 'Ends with a note or an action'],
]

/** The move a drag between two columns makes, the same as the matching button. */
const DRAG_MOVES: Record<string, Action> = {
  'inbox>booked': 'book',
  'booked>learning': 'start',
  'learning>learned': 'finish',
  'booked>inbox': 'unbook',
}

function Card({ item, onOpen }: { item: Item; onOpen: () => void }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: item.id, data: { state: item.state } })
  const age = ageDays(item.captured_at)
  const style = transform ? { transform: `translate(${transform.x}px, ${transform.y}px)`, zIndex: 3, position: 'relative' as const } : undefined
  return (
    <button ref={setNodeRef} style={style} className={`kcard ${isDragging ? 'dragging' : ''}`} onClick={onOpen} {...listeners} {...attributes}>
      <span className="title">{item.title}</span>
      <span className="sub">
        {item.tag && <TagLabel tag={item.tag} />}
        <span>
          {SOURCE_NAMES[item.source_type] ?? item.source_type} · {item.estimate_min} min
        </span>
        {item.state === 'inbox' && <span className={age >= 14 ? 'aging' : ''}>{age >= 14 ? `Day ${age} · still want this?` : savedAgo(item.captured_at)}</span>}
        {item.state === 'booked' && item.booked_for && <span className="chip good">{slotLabel(item.booked_for)}</span>}
        {item.state === 'learned' && (
          <>
            <Icon name="check" />
            <span>{item.note || 'Learned'}</span>
          </>
        )}
      </span>
    </button>
  )
}

function Column({ state, name, note, items, onOpen }: { state: ItemState; name: string; note: string; items: Item[]; onOpen: (i: Item) => void }) {
  const { setNodeRef, isOver } = useDroppable({ id: state })
  return (
    <section ref={setNodeRef} className={`col ${isOver ? 'over' : ''}`} aria-label={name}>
      <div className="colhead">
        {name}
        <span>{items.length}</span>
      </div>
      <p className="colnote">{note}</p>
      {items.length ? items.map((i) => <Card key={i.id} item={i} onOpen={() => onOpen(i)} />) : <div className="coldrop">Nothing here</div>}
    </section>
  )
}

const RULES = [
  ['Capture from anywhere', 'The phone share sheet to the Telegram bot, or the C key here.'],
  ['Decide within 48 hours', 'Every capture gets one of three answers: book a slot, link it to a goal, or let it go.'],
  ['Resurface, then expire', 'Untouched items return on days 3, 7 and 14. On day 21 you get one last ask, then they archive.'],
]

function sortFor(state: ItemState, items: Item[]): Item[] {
  if (state === 'booked') return [...items].sort((a, b) => (a.booked_for ?? '').localeCompare(b.booked_for ?? ''))
  if (state === 'learned') return [...items].sort((a, b) => (b.closed_at ?? '').localeCompare(a.closed_at ?? ''))
  return [...items].sort((a, b) => a.captured_at.localeCompare(b.captured_at))
}

/** Learning queue: drag a card to move it, or open it to decide. */
export function QueuePage() {
  const { data: items = [] } = useQuery({ queryKey: ['items'], queryFn: api.items })
  const [openId, setOpenId] = useState<number | null>(null)
  const move = useItemTransition()
  const toast = useToast()
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }), useSensor(KeyboardSensor))
  const by = (s: ItemState) => sortFor(s, items.filter((i) => i.state === s))
  const open = items.find((i) => i.id === openId)

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    const from = active.data.current?.state as ItemState
    const to = over?.id as ItemState | undefined
    if (!to || to === from) return
    const action = DRAG_MOVES[`${from}>${to}`]
    if (action) move.mutate({ id: Number(active.id), action })
    else toast(from === 'inbox' && to === 'learning' ? 'Book it first, then start it' : 'That move is not allowed')
  }

  return (
    <>
      <div className="pagehead">
        <div>
          <div className="over kicker">
            <Icon name="queue" />
            Capture now · learn on schedule · let go on purpose
          </div>
          <h1>Learning queue</h1>
        </div>
        <span>
          {by('inbox').length} waiting · {by('booked').length} booked
        </span>
      </div>
      <p className="lead">Everything you save lands in the inbox. Drag a card to move it, or open it to book a slot or let it go.</p>
      <DndContext sensors={sensors} onDragEnd={onDragEnd}>
        <div className="board">
          {COLS.map(([s, name, note]) => (
            <Column key={s} state={s} name={name} note={note} items={by(s)} onOpen={(i) => setOpenId(i.id)} />
          ))}
        </div>
      </DndContext>
      <div className="cols even">
        <section className="card">
          <div className="cardhead">
            <h2>House rules</h2>
          </div>
          <div className="rules section">
            {RULES.map(([b, p]) => (
              <div className="rule" key={b}>
                <b>{b}</b>
                <p>{p}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
      {open && <ItemDialog item={open} onClose={() => setOpenId(null)} />}
    </>
  )
}

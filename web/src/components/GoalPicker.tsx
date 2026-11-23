import type { Tag } from '../api'
import { useGoals } from '../goals'
import { Dot } from './goals'

/** Choose the goal a task or item serves, lowest horizon first. Empty means untied. */
export function GoalPicker({ value, onChange, id }: { value: number | null; onChange: (goalId: number | null) => void; id?: string }) {
  const week = useGoals('week')
  const month = useGoals('month')
  const quarter = useGoals('quarter')
  const groups: [string, typeof week.data][] = [
    ['This week', week.data],
    ['This month', month.data],
    ['This quarter', quarter.data],
  ]
  return (
    <select id={id} aria-label="Goal" value={value ?? ''} onChange={(e) => onChange(Number(e.target.value) || null)}>
      <option value="">No goal (untied)</option>
      {groups.map(
        ([label, goals]) =>
          !!goals?.length && (
            <optgroup key={label} label={label}>
              {goals.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.title}
                </option>
              ))}
            </optgroup>
          ),
      )}
    </select>
  )
}

/** The goal label on a task or item, or "Untied" when it serves no goal. */
export function TagLabel({ tag }: { tag: Tag | null }) {
  if (!tag) return <span className="untied">Untied</span>
  return (
    <span className="gtag">
      <Dot color={tag.color} />
      {tag.short || tag.title}
    </span>
  )
}

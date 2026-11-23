import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, goalsApi, type Task } from '../api'
import { dur } from '../format'
import { Dialog } from './Dialog'
import { Trace } from './Focus'
import { useHasGoals } from '../goals'
import { GoalPicker } from './GoalPicker'
import { useToast } from './Toast'

/** A task's details: the goal it serves and the chain up to its year theme. */
export function TaskDialog({ task, onClose }: { task: Task; onClose: () => void }) {
  const qc = useQueryClient()
  const toast = useToast()
  const [goalId, setGoalId] = useState(task.goal_id)
  const hasGoals = useHasGoals()
  const trace = useQuery({
    queryKey: ['trace', task.goal_id],
    queryFn: () => goalsApi.trace(task.goal_id!),
    enabled: !!task.goal_id,
  })
  const move = useMutation({
    mutationFn: (planned_date: string) => api.editTask(task.id, { planned_date }),
    onSuccess: () => qc.invalidateQueries(),
    onError: (err) => toast(err.message),
  })
  const link = useMutation({
    mutationFn: (goal_id: number | null) => api.editTask(task.id, { goal_id }),
    onSuccess: () => qc.invalidateQueries(),
    onError: (err) => toast(err.message),
  })
  return (
    <Dialog title="Task" onClose={onClose}>
      <p className="kicker">{dur(task.estimate_min)}</p>
      <h3 style={{ marginTop: 8 }}>{task.title}</h3>
      <Trace steps={task.goal_id ? (trace.data ?? []) : []} />
      <label className="q" htmlFor="tday">
        Day
      </label>
      <input
        id="tday"
        type="date"
        value={task.planned_date}
        onChange={(e) => e.target.value && move.mutate(e.target.value)}
      />
      {hasGoals && (
        <>
          <label className="q" htmlFor="tgoal">
            Goal
          </label>
          <GoalPicker
            id="tgoal"
            value={goalId}
            onChange={(g) => {
              setGoalId(g)
              link.mutate(g)
            }}
          />
        </>
      )}
    </Dialog>
  )
}

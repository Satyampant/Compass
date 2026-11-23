import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Task } from '../api'
import { dur } from '../format'
import { Dialog } from './Dialog'
import { GoalPicker } from './GoalPicker'
import { useToast } from './Toast'

/** A task's details: the goal it serves. */
export function TaskDialog({ task, onClose }: { task: Task; onClose: () => void }) {
  const qc = useQueryClient()
  const toast = useToast()
  const [goalId, setGoalId] = useState(task.goal_id)
  const link = useMutation({
    mutationFn: (goal_id: number | null) => api.editTask(task.id, { goal_id }),
    onSuccess: () => qc.invalidateQueries(),
    onError: (err) => toast(err.message),
  })
  return (
    <Dialog title="Task" onClose={onClose}>
      <p className="kicker">{dur(task.estimate_min)}</p>
      <h3 style={{ marginTop: 8 }}>{task.title}</h3>
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
    </Dialog>
  )
}

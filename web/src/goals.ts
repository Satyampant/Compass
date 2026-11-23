/** Goal helpers shared by the horizon pages. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { goalsApi, type Goal, type Horizon } from './api'
import { useToast } from './components/Toast'

export const HORIZON_NAMES: Record<Horizon, string> = { year: 'Year theme', quarter: 'Quarter goal', month: 'Milestone', week: 'Weekly outcome' }
export const PARENT: Partial<Record<Horizon, Horizon>> = { quarter: 'year', month: 'quarter', week: 'month' }
export const COLORS = [1, 2, 3, 4, 5]

export const colorVar = (c: number | null | undefined) => (c ? `var(--g${c})` : 'var(--line)')
export const pct = (p: number) => Math.round(p * 100)

/** All goals of one horizon in the current period. */
export function useGoals(horizon: Horizon) {
  return useQuery({ queryKey: ['goals', horizon], queryFn: () => goalsApi.list(horizon) })
}

/** The quarter goal a goal sits under, for its colour and short label. */
export function quarterOf(goal: Goal | undefined, byId: Map<number, Goal>): Goal | undefined {
  let g = goal
  while (g && g.horizon !== 'quarter') g = g.parent_id ? byId.get(g.parent_id) : undefined
  return g
}

/** Create a goal and refresh every goal list. */
export function useCreateGoal(onDone?: () => void) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: goalsApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['goals'] })
      onDone?.()
    },
  })
}

/** Tick a milestone or outcome done, before the server answers. */
export function useToggleGoal(horizon: 'month' | 'week') {
  const qc = useQueryClient()
  const toast = useToast()
  const key = ['goals', horizon]
  return useMutation({
    mutationFn: (g: Goal) => goalsApi.edit(g.id, { done: !g.done }),
    onMutate: async (g) => {
      await qc.cancelQueries({ queryKey: key })
      const before = qc.getQueryData<Goal[]>(key)
      qc.setQueryData<Goal[]>(key, (list) => list?.map((x) => (x.id === g.id ? { ...x, done: !x.done, progress: x.done ? 0 : 1 } : x)))
      return { before }
    },
    onError: (err, _g, ctx) => {
      qc.setQueryData(key, ctx?.before)
      toast(err.message)
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['goals'] }),
  })
}

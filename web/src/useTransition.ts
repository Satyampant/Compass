import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Action, type Item, type ItemState } from './api'
import { useToast } from './components/Toast'
import { slotLabel } from './format'

const TARGET: Record<Action, ItemState> = { book: 'booked', start: 'learning', finish: 'learned', unbook: 'inbox', let_go: 'let_go' }

function message(item: Item): string {
  switch (item.state) {
    case 'booked':
      return `Booked for ${slotLabel(item.booked_for!)}`
    case 'learning':
      return 'Started'
    case 'learned':
      return 'Marked as learned'
    case 'inbox':
      return 'Back in the inbox, top of today’s list'
    default:
      return 'Let go. It will not come back.'
  }
}

interface Vars {
  id: number
  action: Action
  booked_for?: string
  note?: string
}

/** Move a learning item. The board updates at once and rolls back if the server refuses. */
export function useItemTransition() {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: ({ id, action, ...extra }: Vars) => api.transition(id, action, extra),
    onMutate: async ({ id, action }) => {
      await qc.cancelQueries({ queryKey: ['items'] })
      const before = qc.getQueryData<Item[]>(['items'])
      qc.setQueryData<Item[]>(['items'], (items) => items?.map((i) => (i.id === id ? { ...i, state: TARGET[action], actions: [] } : i)))
      return { before }
    },
    onError: (err, _vars, ctx) => {
      qc.setQueryData(['items'], ctx?.before)
      toast(err.message)
    },
    onSuccess: (item) => toast(message(item)),
    onSettled: () => qc.invalidateQueries(),
  })
}

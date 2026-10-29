import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createExpense,
  listCategories,
  listExpenses,
  listSpendingTypes,
  type ExpenseCreate,
} from './generated'

// Server state lives here: components ask for data, TanStack Query fetches, caches and refetches.
// `throwOnError: true` makes failed requests reject, which is what TanStack Query expects.

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: async () => (await listCategories({ throwOnError: true })).data,
    staleTime: Infinity, // categories practically never change during a session
  })
}

export function useSpendingTypes() {
  return useQuery({
    queryKey: ['spending-types'],
    queryFn: async () => (await listSpendingTypes({ throwOnError: true })).data,
    staleTime: Infinity,
  })
}

export function useExpenses(month: string) {
  return useQuery({
    queryKey: ['expenses', month],
    queryFn: async () => (await listExpenses({ query: { month }, throwOnError: true })).data,
  })
}

export function useCreateExpense() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (expense: ExpenseCreate) =>
      (await createExpense({ body: expense, throwOnError: true })).data,
    // Every cached expense list may now be outdated, whatever month it shows.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['expenses'] }),
  })
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createExpense,
  getCurrentUser,
  listCategories,
  listExpenses,
  listSpendingTypes,
  logIn,
  logOut,
  signUp,
  updateExpense,
  type ExpenseCreate,
  type ExpenseUpdate,
  type LogIn,
  type UserRead,
} from './generated'

// Server state lives here: components ask for data, TanStack Query fetches, caches and refetches.
// `throwOnError: true` makes failed requests reject, which is what TanStack Query expects.

export const currentUserKey = ['current-user']

/** The logged-in user, or `null` when there is no session (the API answers 401). */
export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserKey,
    queryFn: async () => {
      const { data, error, response } = await getCurrentUser()
      if (response?.status === 401) return null
      if (error) throw error
      return data!
    },
    staleTime: Infinity, // only changes on login and logout, which update the cache themselves
  })
}

/** Log in or sign up: both answer with the user and set the session cookie. */
function useStartSession(request: (credentials: LogIn) => Promise<UserRead>) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: request,
    onSuccess: (user) => queryClient.setQueryData(currentUserKey, user),
  })
}

export function useLogIn() {
  return useStartSession(async (body) => (await logIn({ body, throwOnError: true })).data)
}

export function useSignUp() {
  return useStartSession(async (body) => (await signUp({ body, throwOnError: true })).data)
}

export function useLogOut() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => logOut({ throwOnError: true }),
    onSuccess: () => {
      queryClient.setQueryData(currentUserKey, null)
      // Forget the previous user's data, so the next one to log in never sees it.
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== currentUserKey[0] })
    },
  })
}

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

export function useUpdateExpense() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, changes }: { id: number; changes: ExpenseUpdate }) =>
      (await updateExpense({ path: { expense_id: id }, body: changes, throwOnError: true })).data,
    // The date may have moved the expense to another month, so refresh every cached list.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['expenses'] }),
  })
}

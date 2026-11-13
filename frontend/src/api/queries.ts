import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createApiToken,
  createExpense,
  createIncome,
  deleteExpense,
  getCurrentUser,
  inviteToHousehold,
  listApiTokens,
  listCategories,
  listExpenses,
  listIncomes,
  listMembers,
  listSpendingTypes,
  logIn,
  logOut,
  revokeApiToken,
  signUp,
  updateExpense,
  type ApiTokenCreate,
  type ExpenseCreate,
  type ExpenseUpdate,
  type IncomeCreate,
  type LogIn,
  type SignUp,
  type UserRead,
} from './generated'

// Server state lives here: components ask for data, TanStack Query fetches, caches and refetches.
// `throwOnError: true` makes failed requests reject, which is what TanStack Query expects.

export const currentUserKey = ['current-user']

/** A failed request that keeps its HTTP status, so the UI can tell errors apart. */
export class ApiError extends Error {
  status: number

  constructor(status: number) {
    super(`Request failed with status ${status}`)
    this.status = status
  }
}

/** The data of a successful call, or an `ApiError` with the response status. */
async function dataOrThrow<T>(request: Promise<{ data?: T; response?: Response }>): Promise<T> {
  const { data, response } = await request
  if (!response?.ok) throw new ApiError(response?.status ?? 0)
  return data as T
}

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
function useStartSession<Body>(request: (body: Body) => Promise<UserRead>) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: request,
    onSuccess: (user) => queryClient.setQueryData(currentUserKey, user),
  })
}

export function useLogIn() {
  return useStartSession((body: LogIn) => dataOrThrow(logIn({ body })))
}

export function useSignUp() {
  return useStartSession((body: SignUp) => dataOrThrow(signUp({ body })))
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

export function useMembers() {
  const householdId = useHouseholdId()

  return useQuery({
    queryKey: ['members', householdId],
    queryFn: async () =>
      (await listMembers({ path: { household_id: householdId }, throwOnError: true })).data,
    staleTime: 5 * 60_000, // someone joining shows up within minutes, without refetching often
  })
}

/**
 * The household the app works on: for now, the user's first one (a switcher can come later).
 * Only for components shown while logged in, which is when the current user is in the cache.
 */
function useHouseholdId() {
  const { data: user } = useCurrentUser()
  return user!.households[0].id
}

export function useExpenses(month: string) {
  const householdId = useHouseholdId()

  return useQuery({
    queryKey: ['expenses', householdId, month],
    queryFn: async () =>
      (
        await listExpenses({
          path: { household_id: householdId },
          query: { month },
          throwOnError: true,
        })
      ).data,
  })
}

export function useCreateExpense() {
  const queryClient = useQueryClient()
  const householdId = useHouseholdId()

  return useMutation({
    mutationFn: async (expense: ExpenseCreate) =>
      (
        await createExpense({
          path: { household_id: householdId },
          body: expense,
          throwOnError: true,
        })
      ).data,
    // Every cached expense list may now be outdated, whatever month it shows.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['expenses'] }),
  })
}

export function useUpdateExpense() {
  const queryClient = useQueryClient()
  const householdId = useHouseholdId()

  return useMutation({
    mutationFn: async ({ id, changes }: { id: number; changes: ExpenseUpdate }) =>
      (
        await updateExpense({
          path: { household_id: householdId, expense_id: id },
          body: changes,
          throwOnError: true,
        })
      ).data,
    // The date may have moved the expense to another month, so refresh every cached list.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['expenses'] }),
  })
}

export function useDeleteExpense() {
  const queryClient = useQueryClient()
  const householdId = useHouseholdId()

  return useMutation({
    mutationFn: (id: number) =>
      deleteExpense({ path: { household_id: householdId, expense_id: id }, throwOnError: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['expenses'] }),
  })
}

export function useIncomes(month: string) {
  const householdId = useHouseholdId()

  return useQuery({
    queryKey: ['incomes', householdId, month],
    queryFn: async () =>
      (
        await listIncomes({
          path: { household_id: householdId },
          query: { month },
          throwOnError: true,
        })
      ).data,
  })
}

export function useCreateIncome() {
  const queryClient = useQueryClient()
  const householdId = useHouseholdId()

  return useMutation({
    mutationFn: async (income: IncomeCreate) =>
      (
        await createIncome({
          path: { household_id: householdId },
          body: income,
          throwOnError: true,
        })
      ).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['incomes'] }),
  })
}

export function useCreateInvitation() {
  const householdId = useHouseholdId()

  return useMutation({
    mutationFn: async () =>
      (await inviteToHousehold({ path: { household_id: householdId }, throwOnError: true })).data,
  })
}

const apiTokensKey = ['api-tokens']

/** The user's API tokens. `enabled`: only fetched once the section is opened. */
export function useApiTokens(enabled: boolean) {
  return useQuery({
    queryKey: apiTokensKey,
    queryFn: async () => (await listApiTokens({ throwOnError: true })).data,
    enabled,
  })
}

/** Creates a token. Its secret is only in this mutation's `data`: the API never shows it again. */
export function useCreateApiToken() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: ApiTokenCreate) => dataOrThrow(createApiToken({ body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: apiTokensKey }),
  })
}

export function useRevokeApiToken() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => revokeApiToken({ path: { token_id: id }, throwOnError: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: apiTokensKey }),
  })
}

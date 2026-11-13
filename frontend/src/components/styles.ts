// Tailwind classes shared by every form, so inputs and buttons look the same everywhere.

export const inputClass =
  'h-11 w-full rounded-lg border border-gray-300 bg-white px-3 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20'

export const primaryButtonClass =
  'w-full rounded-lg bg-emerald-600 py-3 font-semibold text-white hover:bg-emerald-700 disabled:opacity-60'

/** The white card that holds the form and every list. */
export const cardClass = 'rounded-2xl bg-white shadow-sm'

export const listCardClass = `divide-y divide-gray-100 overflow-hidden ${cardClass}`

/** A tappable row in a list: opens the item to edit it. */
export const rowButtonClass = 'flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-gray-50'

/** Today's date as YYYY-MM-DD in the user's own timezone (not UTC, unlike toISOString). */
export function todayISO(now: Date = new Date()): string {
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/** Current month as YYYY-MM, the format the API's `month` filter expects. */
export function currentMonth(now: Date = new Date()): string {
  return todayISO(now).slice(0, 7)
}

const dayFormatter = new Intl.DateTimeFormat('es-ES', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
})

/** "2026-10-23" → "viernes, 23 de octubre" */
export function formatDay(isoDate: string): string {
  // Appending a time makes the browser parse it as local midnight instead of UTC.
  return dayFormatter.format(new Date(`${isoDate}T00:00`))
}

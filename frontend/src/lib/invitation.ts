/** The token of an invitation link (`/#invitation=…`), if the page was opened from one. */
export function readInvitation(hash = window.location.hash): string | null {
  return new URLSearchParams(hash.slice(1)).get('invitation')
}

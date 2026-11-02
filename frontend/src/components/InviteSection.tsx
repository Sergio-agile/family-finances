import { useState } from 'react'
import { useCreateInvitation } from '../api/queries'
import { primaryButtonClass } from './styles'

/**
 * Creates a one-time link to join the household. On phones it opens the share sheet
 * (WhatsApp…); elsewhere it copies the link. Both browser APIs need HTTPS or localhost, so
 * the link is also shown in a field to copy by hand.
 */
export function InviteSection({ householdName }: { householdName: string }) {
  const invitation = useCreateInvitation()
  const [copied, setCopied] = useState(false)

  if (!invitation.data) {
    return (
      <section className="space-y-2">
        <button
          type="button"
          onClick={() => invitation.mutate()}
          disabled={invitation.isPending}
          className="w-full rounded-lg border border-emerald-600 py-3 font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-60"
        >
          {invitation.isPending ? 'Creando enlace…' : `Invitar a alguien a ${householdName}`}
        </button>
        {invitation.isError && (
          <p className="text-sm text-red-600">No se ha podido crear el enlace. Inténtalo de nuevo.</p>
        )}
      </section>
    )
  }

  const { url } = invitation.data

  return (
    <section className="space-y-3 rounded-2xl bg-white p-4 shadow-sm">
      <p className="text-sm text-gray-700">
        Envía este enlace a quien quieras invitar. Sirve para crear <strong>una</strong> cuenta y
        caduca en 7 días.
      </p>
      <input
        readOnly
        value={url}
        onFocus={(event) => event.target.select()}
        aria-label="Enlace de invitación"
        className="h-11 w-full rounded-lg border border-gray-300 bg-gray-50 px-3 text-sm"
      />
      {'share' in navigator ? (
        <button
          type="button"
          onClick={() =>
            navigator
              .share({ title: 'Family Finances', text: `Únete a ${householdName}`, url })
              .catch(() => {}) // closing the share sheet without choosing an app is not an error
          }
          className={primaryButtonClass}
        >
          Compartir
        </button>
      ) : (
        'clipboard' in navigator && (
          <button
            type="button"
            onClick={() => navigator.clipboard.writeText(url).then(() => setCopied(true))}
            className={primaryButtonClass}
          >
            {copied ? 'Copiado' : 'Copiar enlace'}
          </button>
        )
      )}
    </section>
  )
}

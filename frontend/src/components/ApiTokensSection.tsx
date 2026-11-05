import { useState, type FormEvent } from 'react'
import { ApiError, useApiTokens, useCreateApiToken, useRevokeApiToken } from '../api/queries'
import type { ApiTokenRead } from '../api/generated'
import { ACCESS_OPTIONS, accessLabel } from '../lib/apiTokens'
import { formatDate } from '../lib/dates'
import { inputClass, primaryButtonClass } from './styles'

/**
 * Personal access tokens for scripts and integrations (n8n). Folded by default, since it is
 * rarely needed: the list is only fetched once the section is opened.
 */
export function ApiTokensSection() {
  const [open, setOpen] = useState(false)

  return (
    <details
      onToggle={(event) => setOpen(event.currentTarget.open)}
      className="rounded-2xl bg-white p-4 shadow-sm"
    >
      <summary className="cursor-pointer font-semibold text-gray-700">Tokens de API</summary>
      {open && <TokensPanel />}
    </details>
  )
}

function TokensPanel() {
  const tokens = useApiTokens(true)
  const create = useCreateApiToken()

  return (
    <div className="mt-3 space-y-4">
      <p className="text-sm text-gray-600">
        Para que programas como n8n usen la app en tu nombre, sin tu contraseña. Cada token solo
        puede hacer lo que elijas, y puedes revocarlo cuando quieras.
      </p>

      {/* The secret is only in the mutation's data: once dismissed, it is gone for good. */}
      {create.data ? (
        <NewToken token={create.data.token} onDone={() => create.reset()} />
      ) : (
        <CreateTokenForm create={create} />
      )}

      {tokens.isPending ? (
        <p className="text-sm text-gray-500">Cargando tokens…</p>
      ) : tokens.isError ? (
        <p className="text-sm text-red-600">No se han podido cargar los tokens.</p>
      ) : tokens.data.length === 0 ? (
        <p className="text-sm text-gray-500">Todavía no has creado ningún token.</p>
      ) : (
        <ul className="divide-y divide-gray-100">
          {tokens.data.map((token) => (
            <TokenRow key={token.id} token={token} />
          ))}
        </ul>
      )}
    </div>
  )
}

function CreateTokenForm({ create }: { create: ReturnType<typeof useCreateApiToken> }) {
  const [name, setName] = useState('')
  const [scope, setScope] = useState(ACCESS_OPTIONS[0].scope)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    create.mutate({ name, scopes: [scope] })
  }

  const tooMany = create.error instanceof ApiError && create.error.status === 409

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <label className="block">
        <span className="mb-1 block text-sm font-medium text-gray-700">Nombre</span>
        <input
          required
          maxLength={50}
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="n8n banco"
          className={inputClass}
        />
      </label>

      <fieldset className="space-y-2">
        <legend className="mb-1 text-sm font-medium text-gray-700">Qué puede hacer</legend>
        {ACCESS_OPTIONS.map((option) => (
          <label key={option.scope} className="flex items-start gap-2 text-sm">
            <input
              type="radio"
              name="scope"
              checked={scope === option.scope}
              onChange={() => setScope(option.scope)}
              className="mt-1 accent-emerald-600"
            />
            <span>
              {option.label}
              <span className="block text-gray-500">{option.hint}</span>
            </span>
          </label>
        ))}
      </fieldset>

      <button type="submit" disabled={create.isPending} className={primaryButtonClass}>
        {create.isPending ? 'Creando…' : 'Crear token'}
      </button>
      {create.isError && (
        <p className="text-sm text-red-600">
          {tooMany
            ? 'Ya tienes 20 tokens: revoca alguno que no uses.'
            : 'No se ha podido crear el token. Inténtalo de nuevo.'}
        </p>
      )}
    </form>
  )
}

function NewToken({ token, onDone }: { token: string; onDone: () => void }) {
  const [copied, setCopied] = useState(false)

  return (
    <div className="space-y-3 rounded-xl bg-amber-50 p-3">
      <p className="text-sm text-amber-900">
        <strong>Cópialo ahora:</strong> no se volverá a mostrar. Trátalo como una contraseña.
      </p>
      <input
        readOnly
        value={token}
        onFocus={(event) => event.target.select()}
        aria-label="Token nuevo"
        className="h-11 w-full rounded-lg border border-amber-200 bg-white px-3 font-mono text-sm"
      />
      <div className="flex gap-2">
        {/* Needs HTTPS or localhost; the field above can always be copied by hand. */}
        {'clipboard' in navigator && (
          <button
            type="button"
            onClick={() => navigator.clipboard.writeText(token).then(() => setCopied(true))}
            className={primaryButtonClass}
          >
            {copied ? 'Copiado' : 'Copiar'}
          </button>
        )}
        <button
          type="button"
          onClick={onDone}
          className="w-full rounded-lg border border-gray-300 py-3 font-semibold text-gray-700 hover:bg-gray-50"
        >
          Hecho
        </button>
      </div>
    </div>
  )
}

function TokenRow({ token }: { token: ApiTokenRead }) {
  const revoke = useRevokeApiToken()

  function handleRevoke() {
    if (window.confirm(`¿Revocar «${token.name}»? Dejará de funcionar al momento.`)) {
      revoke.mutate(token.id)
    }
  }

  return (
    <li className="flex items-center justify-between gap-3 py-3">
      <div className="min-w-0 text-sm">
        <p className="truncate font-medium">{token.name}</p>
        <p className="text-gray-500">{accessLabel(token.scopes)}</p>
        <p className="text-gray-500">
          Creado el {formatDate(token.created_at)} ·{' '}
          {token.last_used_at ? `usado el ${formatDate(token.last_used_at)}` : 'sin usar todavía'}
        </p>
        {revoke.isError && <p className="text-red-600">No se ha podido revocar.</p>}
      </div>
      <button
        type="button"
        onClick={handleRevoke}
        disabled={revoke.isPending}
        className="shrink-0 text-sm font-semibold text-red-600 disabled:opacity-60"
      >
        Revocar
      </button>
    </li>
  )
}

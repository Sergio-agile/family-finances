import { useState } from 'react'
import type { FormEvent } from 'react'
import { useLogIn, useSignUp } from '../api/queries'
import { inputClass, primaryButtonClass } from './styles'

const copy = {
  login: {
    title: 'Entrar',
    submit: 'Entrar',
    pending: 'Entrando…',
    error: 'Email o contraseña incorrectos.',
    switchPrompt: '¿Vienes por la invitación?',
    switchTo: 'Crear cuenta',
  },
  signup: {
    title: 'Crear cuenta',
    submit: 'Crear cuenta',
    pending: 'Creando…',
    error:
      'No se ha podido crear la cuenta. Puede que ya tengas una con ese email, o que la invitación haya caducado o ya se haya usado.',
    switchPrompt: '¿Ya tienes cuenta?',
    switchTo: 'Entrar',
  },
}

/** The token of an invitation link (`/#invitation=…`), if the page was opened from one. */
function readInvitation() {
  return new URLSearchParams(window.location.hash.slice(1)).get('invitation')
}

/**
 * Login and sign-up share the same two fields, so one form switches between both.
 * Sign-up is only offered when the page was opened from an invitation link.
 */
export function AuthScreen() {
  const [invitation] = useState(readInvitation)
  const [mode, setMode] = useState<'login' | 'signup'>(invitation ? 'signup' : 'login')
  const logIn = useLogIn()
  const signUp = useSignUp()
  const mutation = mode === 'login' ? logIn : signUp
  const text = copy[mode]

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const credentials = { email: String(data.get('email')), password: String(data.get('password')) }

    if (mode === 'login') {
      logIn.mutate(credentials)
    } else {
      signUp.mutate(
        { ...credentials, invitation_token: invitation! },
        // The invitation is used up: drop it from the URL so a later logout shows plain login.
        { onSuccess: () => history.replaceState(null, '', window.location.pathname) },
      )
    }
  }

  function switchMode() {
    mutation.reset() // don't carry one form's error over to the other
    setMode(mode === 'login' ? 'signup' : 'login')
  }

  return (
    <main className="mx-auto max-w-sm space-y-6 px-4 py-12">
      <h1 className="text-center text-2xl font-bold">Family Finances</h1>

      <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold">{text.title}</h2>

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-gray-700">Email</span>
          <input name="email" type="email" required autoComplete="email" className={inputClass} />
        </label>

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-gray-700">Contraseña</span>
          <input
            name="password"
            type="password"
            required
            minLength={mode === 'signup' ? 12 : undefined}
            maxLength={128}
            // Tells password managers whether to fill a saved password or suggest a new one.
            autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
            className={inputClass}
          />
          {mode === 'signup' && (
            <span className="mt-1 block text-sm text-gray-500">Mínimo 12 caracteres.</span>
          )}
        </label>

        {mutation.isError && <p className="text-sm text-red-600">{text.error}</p>}

        <button type="submit" disabled={mutation.isPending} className={primaryButtonClass}>
          {mutation.isPending ? text.pending : text.submit}
        </button>
      </form>

      <p className="text-center text-sm text-gray-600">
        {invitation ? (
          <>
            {text.switchPrompt}{' '}
            <button type="button" onClick={switchMode} className="font-semibold text-emerald-700">
              {text.switchTo}
            </button>
          </>
        ) : (
          '¿No tienes cuenta? Pide un enlace de invitación a alguien de tu hogar.'
        )}
      </p>
    </main>
  )
}

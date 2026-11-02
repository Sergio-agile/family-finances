import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, useLogIn, useSignUp } from '../api/queries'
import { readInvitation } from '../lib/invitation'
import { inputClass, primaryButtonClass } from './styles'

const copy = {
  login: {
    title: 'Entrar',
    submit: 'Entrar',
    pending: 'Entrando…',
    errors: { 401: 'Email o contraseña incorrectos.' } as Record<number, string>,
    switchPrompt: '¿Vienes por la invitación?',
    switchTo: 'Crear cuenta',
  },
  signup: {
    title: 'Crear cuenta',
    submit: 'Crear cuenta',
    pending: 'Creando…',
    errors: {
      400: 'La invitación ha caducado o ya se ha usado. Pide un enlace nuevo.',
      409: 'Ya existe una cuenta con ese email. Pulsa «Entrar» abajo.',
    } as Record<number, string>,
    switchPrompt: '¿Ya tienes cuenta?',
    switchTo: 'Entrar',
  },
}

const tooManyAttempts = 'Demasiados intentos fallidos. Espera 15 minutos y vuelve a probar.'
const genericError = 'No se ha podido completar. Inténtalo de nuevo.'

/** The message for a failed login or sign-up, from the HTTP status the API answered. */
function errorMessage(error: Error, errors: Record<number, string>) {
  const status = error instanceof ApiError ? error.status : 0
  if (status === 429) return tooManyAttempts
  return errors[status] ?? genericError
}

/**
 * Login and sign-up share the same two fields, so one form switches between both.
 * Sign-up is only offered when the page was opened from an invitation link.
 */
export function AuthScreen() {
  const [invitation] = useState(() => readInvitation())
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
        { ...credentials, name: String(data.get('name')), invitation_token: invitation! },
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

        {mode === 'signup' && (
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700">Nombre</span>
            <input
              name="name"
              required
              maxLength={50}
              autoComplete="given-name"
              className={inputClass}
            />
            <span className="mt-1 block text-sm text-gray-500">
              Es como te verán los demás en el hogar.
            </span>
          </label>
        )}

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

        {mutation.error && (
          <p className="text-sm text-red-600">{errorMessage(mutation.error, text.errors)}</p>
        )}

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

type Props = {
  defaultValue?: string
  /** Shown under the field, which is then marked invalid. */
  error: string | null
}

/** The big amount input at the top of the expense and income forms, named `amount`. */
export function AmountField({ defaultValue, error }: Props) {
  return (
    <label className="block">
      <span className="sr-only">Importe</span>
      <div className="flex items-baseline gap-2 border-b-2 border-gray-200 focus-within:border-emerald-600">
        <input
          name="amount"
          inputMode="decimal"
          placeholder="0,00"
          autoComplete="off"
          required
          defaultValue={defaultValue}
          aria-invalid={error !== null}
          className="w-full bg-transparent py-2 text-4xl font-semibold tabular-nums focus:outline-none"
        />
        <span className="text-2xl text-gray-400">€</span>
      </div>
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </label>
  )
}

export const AMOUNT_ERROR = 'Escribe un importe positivo, por ejemplo 12,50'

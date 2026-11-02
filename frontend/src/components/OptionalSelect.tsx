import type { UseQueryResult } from '@tanstack/react-query'
import { inputClass } from './styles'

type Props = {
  name: string
  label: string
  /** Text of the empty option, which the form sends as `null`. */
  emptyLabel: string
  options: UseQueryResult<{ id: number; name: string }[]>
  defaultValue?: number
}

/** A labelled <select> whose first option means "none", filled from a server query. */
export function OptionalSelect({ name, label, emptyLabel, options, defaultValue }: Props) {
  return (
    <label className="block min-w-0">
      <span className="mb-1 block text-sm font-medium text-gray-700">
        {label} <span className="font-normal text-gray-400">(opcional)</span>
      </span>
      <select
        name={name}
        disabled={!options.isSuccess}
        defaultValue={defaultValue ?? ''}
        className={inputClass}
      >
        <option value="">{options.isPending ? 'Cargando…' : emptyLabel}</option>
        {options.data?.map((option) => (
          <option key={option.id} value={option.id}>
            {option.name}
          </option>
        ))}
      </select>
    </label>
  )
}

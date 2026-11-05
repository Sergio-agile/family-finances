import type { ReactNode } from 'react'

type Props = {
  /** Id of the element that names the dialog, for screen readers. */
  labelledBy: string
  onClose: () => void
  className: string
  children: ReactNode
}

/**
 * Native <dialog> as a modal: focus trap, Escape to close and backdrop come from the browser,
 * and on Android the system back button closes it too. It opens as soon as it is mounted, so
 * the parent only decides whether to render it.
 */
export function Dialog({ labelledBy, onClose, className, children }: Props) {
  return (
    <dialog
      ref={(dialog) => {
        if (dialog && !dialog.open) dialog.showModal()
      }}
      onClose={onClose}
      // A click on the dialog element itself (not its content) is a click on the backdrop.
      onClick={(event) => event.target === event.currentTarget && onClose()}
      aria-labelledby={labelledBy}
      className={className}
    >
      {children}
    </dialog>
  )
}

/** The × button every dialog closes with. */
export function CloseButton({ onClick, className }: { onClick: () => void; className: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Cerrar"
      className={`rounded-full px-3 py-1 text-2xl leading-none ${className}`}
    >
      ×
    </button>
  )
}

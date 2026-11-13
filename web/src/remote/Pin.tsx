/** A feature's pin, which holds it still while the walk moves the rest. */
export default function Pin({ name, pinned, onClick }: { name: string; pinned: boolean; onClick: () => void }) {
  return (
    <button className="pin" aria-pressed={pinned} aria-label={`Pin ${name}`} onClick={onClick}>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M9 3h6l-1 6 3 3v2h-4v6l-1 2-1-2v-6H7v-2l3-3z" />
      </svg>
    </button>
  )
}

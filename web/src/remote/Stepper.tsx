/** A control's minus and plus round its value, ticking on each tap; with onPick, a tap on the value too. */
export default function Stepper({
  name,
  value,
  onStep,
  onPick,
}: {
  name: string
  value: string
  onStep: (step: number) => void
  onPick?: () => void
}) {
  const step = (by: number) => {
    navigator.vibrate?.(10)
    onStep(by)
  }
  const label = (
    <>
      <span className="control">{name}:</span> {value}
    </>
  )
  return (
    <div className="stepper">
      <button aria-label={`${name} down`} onClick={() => step(-1)}>
        −
      </button>
      {onPick ? (
        <button className="value" onClick={onPick}>
          {label}
        </button>
      ) : (
        <span className="value">{label}</span>
      )}
      <button aria-label={`${name} up`} onClick={() => step(1)}>
        +
      </button>
    </div>
  )
}

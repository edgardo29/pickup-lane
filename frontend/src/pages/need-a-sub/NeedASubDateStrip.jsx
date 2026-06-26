function NeedASubDateStrip({
  canGoNext,
  canGoPrevious,
  dates,
  onNext,
  onPrevious,
  onSelectDate,
  selectedDateKey,
}) {
  return (
    <div className="need-sub-date-strip-shell">
      <button
        aria-label="Previous week"
        className="need-sub-date-arrow"
        disabled={!canGoPrevious}
        onClick={onPrevious}
        type="button"
      >
        ←
      </button>

      <div aria-label="Need a Sub posts by date" className="need-sub-date-strip">
        {dates.map((date) => (
          <button
            className={`need-sub-date ${date.key === selectedDateKey ? 'need-sub-date--active' : ''}`}
            key={date.key}
            onClick={() => onSelectDate(date.key)}
            type="button"
          >
            <span>{date.weekday}</span>
            <strong>{date.month}</strong>
            <em>{date.day}</em>
          </button>
        ))}
      </div>

      <button
        aria-label="Next week"
        className="need-sub-date-arrow"
        disabled={!canGoNext}
        onClick={onNext}
        type="button"
      >
        →
      </button>
    </div>
  )
}

export default NeedASubDateStrip

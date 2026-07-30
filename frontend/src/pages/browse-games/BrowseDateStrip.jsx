function BrowseDateStrip({
  canGoNext,
  canGoPrevious,
  dates,
  onNext,
  onPrevious,
  onSelectDate,
  selectedDateKey,
}) {
  return (
    <div className="browse-date-strip-shell">
      <button
        className="browse-date-arrow"
        type="button"
        aria-label="Previous week"
        disabled={!canGoPrevious}
        onClick={onPrevious}
      >
        ←
      </button>

      <div className="browse-date-strip pl-scrollbar" aria-label="Browse games by date">
        {dates.map((date) => (
          <button
            className={`browse-date ${date.key === selectedDateKey ? 'browse-date--active' : ''}`}
            type="button"
            key={date.key}
            aria-current={date.key === selectedDateKey ? 'date' : undefined}
            aria-label={`Browse games on ${date.weekday} ${date.month} ${date.day}`}
            onClick={() => onSelectDate(date.key)}
          >
            <span>{date.weekday}</span>
            <strong>{date.month}</strong>
            <em>{date.day}</em>
          </button>
        ))}
      </div>

      <button
        className="browse-date-arrow"
        type="button"
        aria-label="Next week"
        disabled={!canGoNext}
        onClick={onNext}
      >
        →
      </button>
    </div>
  )
}

export default BrowseDateStrip

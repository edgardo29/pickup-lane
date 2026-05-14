function BrowseDateStrip({ dates, selectedDateKey, onSelectDate }) {
  return (
    <div className="browse-date-strip" aria-label="Browse games by date">
      {dates.map((date) => (
        <button
          className={`browse-date ${date.key === selectedDateKey ? 'browse-date--active' : ''}`}
          type="button"
          key={date.key}
          onClick={() => onSelectDate(date.key)}
        >
          <span>{date.weekday}</span>
          <strong>{date.month}</strong>
          <em>{date.day}</em>
        </button>
      ))}
    </div>
  )
}

export default BrowseDateStrip

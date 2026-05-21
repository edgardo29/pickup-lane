import { monthOptions } from './authConstants.js'
import {
  getBirthYearOptions,
  getDaysInMonth,
  pad2,
} from './authHelpers.js'

export function BirthdayField({
  day,
  disabled,
  month,
  onDayChange,
  onMonthChange,
  onYearChange,
  year,
}) {
  const maxDay = getDaysInMonth(month, year)
  const dayOptions = Array.from({ length: maxDay }, (_, index) => pad2(index + 1))
  const yearOptions = getBirthYearOptions()

  function updateMonth(nextMonth) {
    onMonthChange(nextMonth)

    if (day && Number(day) > getDaysInMonth(nextMonth, year)) {
      onDayChange('')
    }
  }

  function updateYear(nextYear) {
    onYearChange(nextYear)

    if (day && Number(day) > getDaysInMonth(month, nextYear)) {
      onDayChange('')
    }
  }

  return (
    <fieldset className="auth-field auth-birthday-field" disabled={disabled}>
      <legend className="auth-field__label">Date of Birth</legend>
      <div className="auth-birthday-grid">
        <label className="auth-select-field">
          <span>Month</span>
          <select
            aria-label="Birth month"
            onChange={(event) => updateMonth(event.target.value)}
            value={month}
          >
            <option value="">Month</option>
            {monthOptions.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="auth-select-field">
          <span>Day</span>
          <select
            aria-label="Birth day"
            onChange={(event) => onDayChange(event.target.value)}
            value={day}
          >
            <option value="">Day</option>
            {dayOptions.map((value) => (
              <option key={value} value={value}>
                {Number(value)}
              </option>
            ))}
          </select>
        </label>
        <label className="auth-select-field">
          <span>Year</span>
          <select
            aria-label="Birth year"
            onChange={(event) => updateYear(event.target.value)}
            value={year}
          >
            <option value="">Year</option>
            {yearOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      </div>
    </fieldset>
  )
}

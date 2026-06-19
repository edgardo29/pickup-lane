function parseDateValue(dateValue) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(dateValue || ''))
  if (!match) {
    throw new Error('Enter a valid game date.')
  }

  const [, yearText, monthText, dayText] = match
  const parts = {
    year: Number(yearText),
    month: Number(monthText),
    day: Number(dayText),
  }
  const validationDate = new Date(Date.UTC(parts.year, parts.month - 1, parts.day))
  if (
    validationDate.getUTCFullYear() !== parts.year
    || validationDate.getUTCMonth() + 1 !== parts.month
    || validationDate.getUTCDate() !== parts.day
  ) {
    throw new Error('Enter a valid game date.')
  }

  return parts
}

function parseTimeValue(timeValue) {
  const match = /^(\d{2}):(\d{2})$/.exec(String(timeValue || ''))
  if (!match) {
    throw new Error('Enter a valid game time.')
  }

  const [, hourText, minuteText] = match
  const parts = {
    hour: Number(hourText),
    minute: Number(minuteText),
  }
  if (parts.hour > 23 || parts.minute > 59) {
    throw new Error('Enter a valid game time.')
  }

  return parts
}

function getDateTimePartsInZone(value, timeZone) {
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) {
    throw new Error('Game schedule is unavailable.')
  }

  let formatter
  try {
    formatter = new Intl.DateTimeFormat('en-CA-u-ca-iso8601', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hourCycle: 'h23',
    })
  } catch {
    throw new Error('Enter a valid game timezone.')
  }

  const parts = Object.fromEntries(
    formatter
      .formatToParts(date)
      .filter((part) => part.type !== 'literal')
      .map((part) => [part.type, Number(part.value)]),
  )

  return {
    year: parts.year,
    month: parts.month,
    day: parts.day,
    hour: parts.hour,
    minute: parts.minute,
    second: parts.second,
  }
}

function pad(value) {
  return String(value).padStart(2, '0')
}

export function getOfficialGameDateTimeInputs(value, timeZone) {
  const parts = getDateTimePartsInZone(value, timeZone)

  return {
    date: `${parts.year}-${pad(parts.month)}-${pad(parts.day)}`,
    time: `${pad(parts.hour)}:${pad(parts.minute)}`,
  }
}

export function buildOfficialGameIsoDateTime(dateValue, timeValue, timeZone) {
  const dateParts = parseDateValue(dateValue)
  const timeParts = parseTimeValue(timeValue)
  const expectedUtcMs = Date.UTC(
    dateParts.year,
    dateParts.month - 1,
    dateParts.day,
    timeParts.hour,
    timeParts.minute,
  )
  let candidateUtcMs = expectedUtcMs

  for (let attempt = 0; attempt < 4; attempt += 1) {
    const actualParts = getDateTimePartsInZone(new Date(candidateUtcMs), timeZone)
    const actualUtcMs = Date.UTC(
      actualParts.year,
      actualParts.month - 1,
      actualParts.day,
      actualParts.hour,
      actualParts.minute,
    )
    const adjustmentMs = expectedUtcMs - actualUtcMs
    candidateUtcMs += adjustmentMs

    if (adjustmentMs === 0) {
      break
    }
  }

  const finalParts = getDateTimePartsInZone(new Date(candidateUtcMs), timeZone)
  if (
    finalParts.year !== dateParts.year
    || finalParts.month !== dateParts.month
    || finalParts.day !== dateParts.day
    || finalParts.hour !== timeParts.hour
    || finalParts.minute !== timeParts.minute
  ) {
    throw new Error('This local time does not exist in the selected timezone.')
  }

  return new Date(candidateUtcMs).toISOString()
}


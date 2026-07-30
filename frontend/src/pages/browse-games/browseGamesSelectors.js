export function buildDateOptions({
  maximumDate,
  minimumDate,
  timeZone,
}) {
  if (!minimumDate || !maximumDate || !timeZone) {
    return []
  }

  const dates = []
  const current = parseDateKeyParts(minimumDate)

  while (current) {
    const key = getDateKeyFromParts(current)
    const labelDate = new Date(Date.UTC(current.year, current.month - 1, current.day, 12))
    dates.push({
      key,
      weekday: new Intl.DateTimeFormat('en-US', { timeZone, weekday: 'short' }).format(labelDate).toUpperCase(),
      month: new Intl.DateTimeFormat('en-US', { timeZone, month: 'short' }).format(labelDate),
      day: new Intl.DateTimeFormat('en-US', { timeZone, day: 'numeric' }).format(labelDate),
    })

    if (key >= maximumDate) {
      break
    }

    addCalendarDays(current, 1)
  }

  return dates
}

export function groupLoadedGamesByTimeGroups(games = [], timeGroups = []) {
  const loadedGamesByGroup = games.reduce((groups, game) => {
    const key = game.time_group_key || ''

    if (!groups.has(key)) {
      groups.set(key, [])
    }

    groups.get(key).push(game)
    return groups
  }, new Map())

  const knownGroupKeys = new Set(timeGroups.map((group) => group.group_key))
  const knownGroups = timeGroups
    .map((group) => ({
      key: group.group_key,
      label: group.group_key,
      totalGames: group.total_games,
      games: loadedGamesByGroup.get(group.group_key) || [],
    }))
    .filter((group) => group.games.length > 0)

  const fallbackGroups = [...loadedGamesByGroup.entries()]
    .filter(([key]) => !knownGroupKeys.has(key))
    .map(([key, groupGames]) => ({
      key,
      label: key,
      totalGames: groupGames.length,
      games: groupGames,
    }))

  return [...knownGroups, ...fallbackGroups]
}

export function isDateKey(value) {
  return Boolean(parseDateKeyParts(value))
}

export function resolveRequestedDateKey(value) {
  return isDateKey(value) ? value : ''
}

export function getDatePageIndexForDate(dateOptions = [], dateKey = '', pageSize = 7) {
  const activeDateIndex = dateOptions.findIndex((date) => date.key === dateKey)
  return activeDateIndex >= 0 ? Math.floor(activeDateIndex / pageSize) : null
}

export function buildBrowseMetaFromPageData(pageData) {
  return {
    browse_date: pageData.browse_date,
    browse_timezone: pageData.browse_timezone,
    browse_today: pageData.browse_today,
    maximum_browse_date: pageData.maximum_browse_date,
    minimum_browse_date: pageData.minimum_browse_date,
    time_groups: pageData.time_groups || [],
  }
}

export function buildSelectedDateResetMeta(currentMeta, nextDateKey) {
  return currentMeta
    ? {
        ...currentMeta,
        browse_date: nextDateKey,
        time_groups: [],
      }
    : currentMeta
}

export function getNextBrowseListGeneration(
  currentGeneration,
  { append = false } = {},
) {
  return append ? currentGeneration : currentGeneration + 1
}

export function shouldApplyBrowseRequest({
  currentDateKey,
  currentGeneration,
  currentVersion,
  requestDateKey,
  requestGeneration,
  requestVersion,
}) {
  const generationMatches = (
    currentGeneration === undefined
    || requestGeneration === undefined
    || requestGeneration === currentGeneration
  )

  return (
    requestVersion === currentVersion
    && requestDateKey === currentDateKey
    && generationMatches
  )
}

function parseDateKeyParts(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || '')
  if (!match) {
    return null
  }

  const parts = {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
  }
  const normalizedDate = new Date(Date.UTC(parts.year, parts.month - 1, parts.day, 12))
  const isValidDate = (
    normalizedDate.getUTCFullYear() === parts.year
    && normalizedDate.getUTCMonth() + 1 === parts.month
    && normalizedDate.getUTCDate() === parts.day
  )

  return isValidDate ? parts : null
}

function getDateKeyFromParts({ year, month, day }) {
  return [
    String(year).padStart(4, '0'),
    String(month).padStart(2, '0'),
    String(day).padStart(2, '0'),
  ].join('-')
}

function addCalendarDays(parts, days) {
  const date = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + days, 12))
  parts.year = date.getUTCFullYear()
  parts.month = date.getUTCMonth() + 1
  parts.day = date.getUTCDate()
}

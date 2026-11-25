import { formatAgendaDate, formatLocalDateKey } from './myGamesFormatters.js'

export function groupUpcomingAgendaItems(items) {
  const dateGroups = new Map()

  items.forEach((item) => {
    const agendaRecord = getAgendaRecord(item)
    const dateKey = getDateKey(agendaRecord)

    if (!dateGroups.has(dateKey)) {
      dateGroups.set(dateKey, {
        key: dateKey,
        label: formatAgendaDate(agendaRecord.starts_at, agendaRecord.timezone),
        items: [],
      })
    }

    dateGroups.get(dateKey).items.push(item)
  })

  return [...dateGroups.values()]
}

export function groupHistoryAgendaItems(items) {
  const groups = items.reduce((groupMap, item) => {
    const agendaRecord = getAgendaRecord(item)
    const key = getDateKey(agendaRecord)
    const label = formatAgendaDate(agendaRecord.starts_at, agendaRecord.timezone)

    if (!groupMap.has(key)) {
      groupMap.set(key, { key, label, items: [] })
    }

    groupMap.get(key).items.push(item)
    return groupMap
  }, new Map())

  return [...groups.values()]
}

function getAgendaRecord(item) {
  return item.game || item.post
}

// Group by the calendar date where the game or post happens.
function getDateKey(agendaRecord) {
  return formatLocalDateKey(agendaRecord.starts_at, agendaRecord.timezone)
}

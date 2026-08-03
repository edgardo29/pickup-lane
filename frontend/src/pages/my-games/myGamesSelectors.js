import { formatAgendaDate } from './myGamesFormatters.js'

export function groupUpcomingAgendaItems(items) {
  const dateGroups = new Map()

  items.forEach((item) => {
    const agendaRecord = getAgendaRecord(item)
    const dateKey = getDateKey(agendaRecord.starts_at)

    if (!dateGroups.has(dateKey)) {
      dateGroups.set(dateKey, {
        key: dateKey,
        label: formatAgendaDate(agendaRecord.starts_at),
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
    const key = getDateKey(agendaRecord.starts_at)
    const label = formatAgendaDate(agendaRecord.starts_at)

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

function getDateKey(value) {
  const date = new Date(value)
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
}

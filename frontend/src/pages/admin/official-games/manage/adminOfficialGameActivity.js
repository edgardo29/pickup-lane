export async function collectOfficialGameActivityPages({ loadPage }) {
  const actions = []
  let cursor = ''

  for (let page = 0; page < 2; page += 1) {
    const response = await loadPage(cursor)
    actions.push(...(response.actions ?? []))
    cursor = response.next_cursor || ''
    if (!cursor) break
  }

  return actions
}

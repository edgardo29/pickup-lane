export function canCancelAdminCommunityGame(game, now = new Date()) {
  if (
    game?.game_status !== 'active' ||
    game?.publish_status !== 'published' ||
    !game?.starts_at
  ) {
    return false
  }

  const startsAt = new Date(game.starts_at)
  return !Number.isNaN(startsAt.getTime()) && startsAt.getTime() > now.getTime()
}

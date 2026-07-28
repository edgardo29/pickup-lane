export function selectAdminActionPrimaryTarget({
  detailTargets = [],
  listPrimaryTarget = null,
} = {}) {
  const targets = Array.isArray(detailTargets) ? detailTargets : []
  return targets.find((target) => target?.is_primary) || listPrimaryTarget || null
}

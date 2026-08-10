export function compareDisplayImages(first, second) {
  return (
    Number(Boolean(second?.is_primary)) - Number(Boolean(first?.is_primary)) ||
    Number(first?.sort_order || 0) - Number(second?.sort_order || 0) ||
    String(first?.id || '').localeCompare(String(second?.id || ''))
  )
}

export function sortDisplayImages(images) {
  return images.slice().sort(compareDisplayImages)
}

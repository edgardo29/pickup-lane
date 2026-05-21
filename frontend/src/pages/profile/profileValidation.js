export function isValidPassword(value) {
  return value.length >= 8 && /[\d\W_]/.test(value)
}

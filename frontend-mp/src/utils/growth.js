export function gramsToKilograms(value) {
  return Number(value) / 1000
}

export function kilogramsToGrams(value) {
  return Math.round(Number(value) * 1000)
}

export function formatKilograms(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '—'
  return String(Number(gramsToKilograms(number).toFixed(2)))
}

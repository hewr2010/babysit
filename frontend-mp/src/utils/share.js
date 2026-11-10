export function decodeMediaName(value) {
  try {
    return decodeURIComponent(value || '')
  } catch (error) {
    return value || ''
  }
}

export function mediaSharePath(item) {
  const query = [`media=${encodeURIComponent(item.name)}`]
  const [year, month] = (item.date || '').split('-')
  if (/^\d{4}$/.test(year || '') && /^\d{2}$/.test(month || '')) {
    query.push(`year=${year}`, `month=${Number(month)}`)
  }
  return `/pages/viewer/viewer?${query.join('&')}`
}

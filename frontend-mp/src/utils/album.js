export function flattenAlbum(groups) {
  return Object.keys(groups || {})
    .sort()
    .reverse()
    .flatMap(date => (groups[date] || [])
      .map(item => ({ ...item, date: item.date || date }))
      .sort((a, b) => (b.time || '').localeCompare(a.time || '')))
}

export function albumMonths(groups) {
  const months = new Set()
  Object.keys(groups || {}).forEach(date => {
    if (/^\d{4}-\d{2}-\d{2}$/.test(date)) months.add(date.slice(0, 7))
  })
  return [...months].sort().reverse().map(key => {
    const [year, month] = key.split('-').map(Number)
    return { key, year, month }
  })
}

export function latestByMetric(records, type) {
  return records.find(record => record.metric_type === type) || null
}

export function previewWindow(media, index, limit = 50) {
  const start = Math.max(0, Math.min(index - Math.floor(limit / 2), media.length - limit))
  return { start, items: media.slice(start, start + limit) }
}

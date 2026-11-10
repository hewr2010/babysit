function pad(value) {
  return String(value).padStart(2, '0')
}

export function today() {
  const date = new Date()
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function currentMonth() {
  const date = new Date()
  return { year: date.getFullYear(), month: date.getMonth() + 1 }
}

export function monthKey(year, month) {
  return `${year}-${pad(month)}`
}

export function monthLabel(year, month) {
  return `${year}年${month}月`
}

export function shiftMonth(year, month, delta) {
  const date = new Date(year, month - 1 + delta, 1)
  return { year: date.getFullYear(), month: date.getMonth() + 1 }
}

function monthAnniversary(year, monthIndex, day) {
  const lastDay = new Date(year, monthIndex + 1, 0).getDate()
  return new Date(year, monthIndex, Math.min(day, lastDay))
}

export function ageText(birthday, now = new Date()) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(birthday || '')) return ''
  const [year, month, day] = birthday.split('-').map(Number)
  const birth = new Date(year, month - 1, day)
  if (birth.getFullYear() !== year || birth.getMonth() !== month - 1 || birth.getDate() !== day || birth > now) {
    return ''
  }

  let months = (now.getFullYear() - year) * 12 + now.getMonth() - (month - 1)
  let anchor = monthAnniversary(year, month - 1 + months, day)
  if (anchor > now) {
    months -= 1
    anchor = monthAnniversary(year, month - 1 + months, day)
  }
  months = Math.max(0, months)
  const days = Math.floor((new Date(now.getFullYear(), now.getMonth(), now.getDate()) - new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate())) / 86400000)
  return months ? `${months}个月${days}天` : `${days}天`
}

export function shortDate(value) {
  if (!value || value === '0000-00-00') return '日期未知'
  const parts = value.split('-')
  return parts.length === 3 ? `${Number(parts[1])}月${Number(parts[2])}日` : value
}

const http = require('node:http')

const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64')

function monthParts(offset = 0) {
  const now = new Date()
  const date = new Date(now.getFullYear(), now.getMonth() + offset, 1)
  return { year: date.getFullYear(), month: date.getMonth() + 1 }
}

function dateKey(year, month, day) {
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

async function startMockServer(videoPath) {
  const current = monthParts()
  const previous = monthParts(-1)
  const currentDate = dateKey(current.year, current.month, 10)
  const state = {
    baby: { name: '测试宝宝', birthday: '2025-01-31', gender: '女' },
    growth: [
      { id: 2, date: dateKey(current.year, current.month, 8), metric_type: 'height', value: 52 },
      { id: 1, date: dateKey(current.year, current.month, 1), metric_type: 'height', value: 50 },
      { id: 3, date: dateKey(current.year, current.month, 8), metric_type: 'weight', value: 4200 }
    ],
    milestones: [],
    requests: []
  }
  const albums = {
    [`${current.year}-${current.month}`]: {
      [currentDate]: [
        { name: '第一张照片.jpg', type: 'photo', size: 1024, time: '09:00:00' },
        { name: '第一段视频.mp4', type: 'video', size: 2048, time: '08:00:00' },
        { name: '第三张照片.jpg', type: 'photo', size: 1024, time: '07:00:00' },
        { name: '第四张照片.jpg', type: 'photo', size: 1024, time: '06:00:00' },
        { name: '第五张照片.jpg', type: 'photo', size: 1024, time: '05:00:00' },
        { name: '第六张照片.jpg', type: 'photo', size: 1024, time: '04:00:00' },
        { name: '第七张照片.jpg', type: 'photo', size: 1024, time: '03:00:00' },
        { name: '第八张照片.jpg', type: 'photo', size: 1024, time: '02:00:00' }
      ]
    },
    [`${previous.year}-${previous.month}`]: {
      [dateKey(previous.year, previous.month, 20)]: [
        { name: '上月照片.jpg', type: 'photo', size: 1024, time: '10:00:00' }
      ]
    }
  }
  let nextGrowthId = 10
  let nextMilestoneId = 10

  const server = http.createServer((request, response) => {
    const url = new URL(request.url, 'http://localhost')
    const pathname = decodeURIComponent(url.pathname)
    state.requests.push(`${request.method} ${pathname}`)
    response.setHeader('Access-Control-Allow-Origin', '*')
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type')
    response.setHeader('Access-Control-Allow-Methods', 'GET,POST,DELETE,OPTIONS')
    if (request.method === 'OPTIONS') {
      response.writeHead(204).end()
      return
    }
    const json = value => response.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify(value))

    if (pathname === '/api/baby') {
      if (request.method === 'POST') {
        readJson(request, data => {
          state.baby = data
          json({ message: 'ok' })
        })
      } else json(state.baby)
      return
    }
    if (pathname === '/api/growth' && request.method === 'GET') return json(state.growth)
    if (pathname === '/api/growth' && request.method === 'POST') {
      readJson(request, data => {
        const type = data.height !== undefined ? 'height' : 'weight'
        state.growth.unshift({ id: nextGrowthId++, date: data.date, metric_type: type, value: data[type] })
        json({ message: 'ok' })
      })
      return
    }
    const growthMatch = pathname.match(/^\/api\/growth\/(\d+)$/)
    if (growthMatch && request.method === 'DELETE') {
      state.growth = state.growth.filter(item => item.id !== Number(growthMatch[1]))
      return json({ message: 'ok' })
    }
    if (pathname === '/api/milestones' && request.method === 'GET') {
      return json(state.milestones.map(item => ({ ...item, file_type: 'photo' })))
    }
    if (pathname === '/api/milestones' && request.method === 'POST') {
      readJson(request, data => {
        const media = Object.values(albums).flatMap(groups => Object.entries(groups).flatMap(([date, items]) => items.map(item => ({ ...item, date })))).find(item => item.name === data.media_filename)
        state.milestones.unshift({ id: nextMilestoneId++, ...data, date: media?.date || currentDate })
        json({ message: 'ok' })
      })
      return
    }
    const milestoneMatch = pathname.match(/^\/api\/milestones\/(\d+)$/)
    if (milestoneMatch && request.method === 'DELETE') {
      state.milestones = state.milestones.filter(item => item.id !== Number(milestoneMatch[1]))
      return json({ message: 'ok' })
    }
    if (pathname === '/api/album') {
      return json(Object.assign({}, ...Object.values(albums)))
    }
    const albumMatch = pathname.match(/^\/api\/album\/(\d+)\/(\d+)$/)
    if (albumMatch) return json(albums[`${Number(albumMatch[1])}-${Number(albumMatch[2])}`] || {})
    if (pathname.startsWith('/thumb/') || pathname.startsWith('/preview/') || pathname.startsWith('/api/download/')) {
      response.writeHead(200, { 'Content-Type': 'image/png' }).end(png)
      return
    }
    if ((pathname.startsWith('/video/') || pathname.startsWith('/livp/')) && videoPath) {
      const fs = require('node:fs')
      response.writeHead(200, { 'Content-Type': 'video/mp4' })
      fs.createReadStream(videoPath).pipe(response)
      return
    }
    response.writeHead(404, { 'Content-Type': 'application/json' }).end(JSON.stringify({ error: 'not found' }))
  })

  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  return { server, state, port: server.address().port, current, previous }
}

function readJson(request, callback) {
  let body = ''
  request.on('data', chunk => { body += chunk })
  request.on('end', () => callback(JSON.parse(body || '{}')))
}

module.exports = { startMockServer }

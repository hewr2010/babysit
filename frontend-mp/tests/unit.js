const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

async function importSource(relativePath) {
  const source = fs.readFileSync(path.resolve(__dirname, relativePath), 'utf8')
  return import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
}

async function run() {
  const dates = await importSource('../src/utils/date.js')
  assert.equal(dates.ageText('2024-01-31', new Date(2024, 1, 29)), '1个月0天')
  assert.equal(dates.ageText('2024-01-31', new Date(2024, 2, 1)), '1个月1天')
  assert.equal(dates.ageText('2024-01-15', new Date(2024, 1, 15)), '1个月0天')
  assert.equal(dates.ageText('2024-01-15', new Date(2024, 1, 14)), '30天')
  assert.equal(dates.ageText('2024-02-30', new Date(2024, 2, 1)), '')
  assert.equal(dates.ageText('2030-01-01', new Date(2024, 0, 1)), '')
  assert.deepEqual(dates.shiftMonth(2024, 1, -1), { year: 2023, month: 12 })
  assert.deepEqual(dates.shiftMonth(2024, 12, 1), { year: 2025, month: 1 })

  const album = await importSource('../src/utils/album.js')
  const flattened = album.flattenAlbum({
    '2024-02-01': [{ name: 'old.jpg', time: '08:00:00' }],
    '2024-03-01': [{ name: 'a.jpg', time: '08:00:00' }, { name: 'b.jpg', time: '09:00:00' }]
  })
  assert.deepEqual(flattened.map(item => item.name), ['b.jpg', 'a.jpg', 'old.jpg'])
  assert.equal(flattened[2].date, '2024-02-01')
  assert.deepEqual(album.albumMonths({ '2024-03-01': [], invalid: [], '2024-02-01': [] }).map(item => item.key), ['2024-03', '2024-02'])
  assert.equal(album.latestByMetric([{ metric_type: 'height', value: 52 }, { metric_type: 'height', value: 50 }], 'height').value, 52)
  const previewItems = Array.from({ length: 80 }, (_, index) => ({ name: `${index}.jpg` }))
  assert.deepEqual(album.previewWindow(previewItems, 0), { start: 0, items: previewItems.slice(0, 50) })
  assert.deepEqual(album.previewWindow(previewItems, 60), { start: 30, items: previewItems.slice(30, 80) })
  assert.deepEqual(album.previewWindow(previewItems, 40), { start: 15, items: previewItems.slice(15, 65) })

  const share = await importSource('../src/utils/share.js')
  const [shareRoute, shareQuery] = share.mediaSharePath({ name: '照片 1#.jpg', date: '2026-11-08' }).split('?')
  const shareParams = new URLSearchParams(shareQuery)
  assert.equal(shareRoute, '/pages/viewer/viewer')
  assert.equal(shareParams.get('media'), '照片 1#.jpg')
  assert.equal(shareParams.get('year'), '2026')
  assert.equal(shareParams.get('month'), '11')
  assert.equal(share.decodeMediaName('2026-11-10%20093849_test.livp'), '2026-11-10 093849_test.livp')
  assert.equal(share.decodeMediaName('已经解码.jpg'), '已经解码.jpg')
  assert.equal(share.decodeMediaName('100%.jpg'), '100%.jpg')
  console.log('Unit tests passed: dates, album helpers and media share paths.')
}

run().catch(error => {
  console.error(error)
  process.exitCode = 1
})

// One click: send the current tab to the local Compass API. The badge says what happened.
const BASE = 'http://127.0.0.1:8000'

const BADGES = {
  item: ['SAVE', '#3f6b4a'],
  duplicate: ['DUP', '#a98e55'],
  error: ['ERR', '#b5533c'],
}

async function badge(tabId, kind) {
  const [text, color] = BADGES[kind]
  await chrome.action.setBadgeBackgroundColor({ color, tabId })
  await chrome.action.setBadgeText({ text, tabId })
  setTimeout(() => chrome.action.setBadgeText({ text: '', tabId }), 3000)
}

// Exposed for tests: returns the API's answer, or { outcome: 'error' }.
async function saveTab(tab, base = BASE) {
  if (!/^https?:/.test(tab.url || '')) return { outcome: 'error', detail: 'not a web page' }
  try {
    const res = await fetch(`${base}/v1/captures`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID() },
      body: JSON.stringify({ text: `${tab.title || ''} ${tab.url}`, channel: 'extension', kind: 'learn' }),
    })
    if (!res.ok) return { outcome: 'error', detail: `HTTP ${res.status}` }
    return await res.json()
  } catch (err) {
    return { outcome: 'error', detail: String(err) }
  }
}

chrome.action.onClicked.addListener(async (tab) => {
  const result = await saveTab(tab)
  await badge(tab.id, result.outcome === 'duplicate' ? 'duplicate' : result.outcome === 'item' ? 'item' : 'error')
})

self.saveTab = saveTab

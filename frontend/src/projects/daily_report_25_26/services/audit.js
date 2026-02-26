import { postAdminAuditEvents } from './api'

const BUFFER_LIMIT = 20
const FLUSH_INTERVAL_MS = 4000
const CLICK_SELECTOR = 'button, a, [role="button"], .btn, .tab-btn, .list-btn'

let queue = []
let timerId = null
let initialized = false
let detachClick = null
let stopRouterHook = null
let getAuthStore = null

function nowIso() {
  return new Date().toISOString()
}

function getCurrentUser() {
  const auth = typeof getAuthStore === 'function' ? getAuthStore() : null
  if (!auth || !auth.isAuthenticated) return null
  return auth.user || null
}

function normalizeLabel(text) {
  const value = String(text || '').replace(/\s+/g, ' ').trim()
  return value.slice(0, 80)
}

function enqueue(event) {
  if (!event || !event.action) return
  queue.push({
    category: event.category || 'ui',
    action: event.action,
    page: event.page || window.location.pathname,
    target: event.target || '',
    detail: event.detail && typeof event.detail === 'object' ? event.detail : {},
    ts: nowIso(),
  })
  if (queue.length >= BUFFER_LIMIT) {
    flush().catch(() => {})
  }
}

async function flush() {
  if (!queue.length) return
  const user = getCurrentUser()
  if (!user) {
    queue = []
    return
  }
  const batch = queue.slice(0, BUFFER_LIMIT)
  queue = queue.slice(BUFFER_LIMIT)
  try {
    await postAdminAuditEvents(batch)
  } catch (err) {
    console.warn('审计日志上报失败', err)
  }
}

function startTimer() {
  stopTimer()
  timerId = window.setInterval(() => {
    flush().catch(() => {})
  }, FLUSH_INTERVAL_MS)
}

function stopTimer() {
  if (timerId) {
    clearInterval(timerId)
    timerId = null
  }
}

function buildClickTarget(element) {
  const label = normalizeLabel(element?.innerText || element?.textContent || '')
  if (label) return label
  const id = String(element?.id || '').trim()
  if (id) return `#${id}`
  const className = String(element?.className || '').trim()
  if (className) return className.split(/\s+/).slice(0, 2).join('.')
  return element?.tagName?.toLowerCase() || 'unknown'
}

function attachClickTracking() {
  const onClick = (evt) => {
    const target = evt.target instanceof Element ? evt.target.closest(CLICK_SELECTOR) : null
    if (!target) return
    enqueue({
      category: 'ui',
      action: 'click',
      target: buildClickTarget(target),
      detail: {
        tag: target.tagName?.toLowerCase() || '',
      },
    })
  }
  document.addEventListener('click', onClick, true)
  detachClick = () => {
    document.removeEventListener('click', onClick, true)
  }
}

export function initAuditTracking({ router, resolveAuthStore }) {
  if (initialized || typeof window === 'undefined') return
  initialized = true
  getAuthStore = resolveAuthStore

  stopRouterHook = router.afterEach((to, from) => {
    const auth = getCurrentUser()
    if (!auth) return
    enqueue({
      category: 'navigation',
      action: 'page_open',
      page: to.fullPath,
      target: to.name ? String(to.name) : to.path,
      detail: {
        from: from?.fullPath || '',
      },
    })
  })
  attachClickTracking()
  startTimer()
}

export function stopAuditTracking() {
  if (!initialized) return
  stopTimer()
  if (typeof stopRouterHook === 'function') stopRouterHook()
  stopRouterHook = null
  if (typeof detachClick === 'function') detachClick()
  detachClick = null
  initialized = false
}

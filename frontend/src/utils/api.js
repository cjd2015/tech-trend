const TIMEOUT_MS = 10000

export const API_BASE = import.meta.env.VITE_API_BASE || ''

const buildUrl = (path) => `${API_BASE}${path}`

const createAbortableFetch = (timeoutMs = TIMEOUT_MS) => {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  return { controller, timeoutId }
}

export const fetchWithTimeout = async (path, options = {}) => {
  const { timeoutMs = TIMEOUT_MS, ...fetchOptions } = options
  const { controller, timeoutId } = createAbortableFetch(timeoutMs)
  try {
    return await fetch(buildUrl(path), { signal: controller.signal, ...fetchOptions })
  } finally {
    clearTimeout(timeoutId)
  }
}

const requestJson = async (method, path, options = {}) => {
  const headers = new Headers(options.headers || {})
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  let response
  try {
    response = await fetchWithTimeout(path, { ...options, method, headers })
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`${method} ${path} 请求超时`)
    }
    throw error
  }
  if (!response.ok) {
    throw new Error(`${method} ${path} 返回状态 ${response.status}`)
  }

  if (response.status === 204) {
    return null
  }

  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    return response.text()
  }

  return response.json()
}

export const getApi = (path, options = {}) => requestJson('GET', path, options)

export const postApi = (path, options = {}) => requestJson('POST', path, options)

export const putApi = (path, options = {}) => requestJson('PUT', path, options)

export const deleteApi = (path, options = {}) => requestJson('DELETE', path, options)

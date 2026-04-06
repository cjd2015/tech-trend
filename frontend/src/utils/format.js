export const formatSourceKey = (item) => `${item.source_type}/${item.source_name}`

export const formatSignalSourceKey = (sourceType, sourceName) => `${sourceType}/${sourceName}`

export const formatDateTime = (value) => {
  if (!value) return '未知时间'
  try {
    return new Date(value).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}

export const formatNumber = (value) => new Intl.NumberFormat('zh-CN').format(value || 0)

export const formatScore = (value, digits = 1) => {
  if (typeof value !== 'number' || Number.isNaN(value)) return '0.0'
  return value.toFixed(digits)
}

export const parseJsonList = (value) => {
  if (!value) return []
  if (Array.isArray(value)) return value
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export const parseMetadata = (signal) => {
  try {
    return JSON.parse(signal?.metadata_json || '{}')
  } catch {
    return {}
  }
}

export const getSignalPopularity = (signal) => {
  const metadata = parseMetadata(signal)
  return metadata.descendants || metadata.comments || metadata.likes || metadata.score || 0
}

export const statusDisplayMap = {
  observed: { label: 'Observed', tone: 'muted' },
  candidate: { label: 'Candidate', tone: 'warning' },
  validated: { label: 'Validated', tone: 'accent' },
  recorded: { label: 'Recorded', tone: 'success' },
  discarded: { label: 'Discarded', tone: 'danger' },
  useful: { label: 'Useful', tone: 'success' },
  reference: { label: 'Reference', tone: 'warning' },
  pending_review: { label: 'Pending Review', tone: 'warning' },
  approved: { label: 'Approved', tone: 'success' },
  rejected: { label: 'Rejected', tone: 'danger' },
  auto_approved: { label: 'Auto Approved', tone: 'accent' },
}

export const getStatusDisplay = (status) => statusDisplayMap[status] || { label: status || 'Unknown', tone: 'muted' }

export const sourceDisplayMap = {
  'community/hacker_news': { name: 'Hacker News', icon: 'HN', color: '#ff6600' },
  'community/github_trending': { name: 'GitHub Trending', icon: 'GH', color: '#111827' },
  'community/stackoverflow': { name: 'Stack Overflow', icon: 'SO', color: '#f97316' },
  'community/devto': { name: 'Dev.to', icon: 'DV', color: '#0f172a' },
  'community/producthunt': { name: 'Product Hunt', icon: 'PH', color: '#ea580c' },
  'community/techcrunch': { name: 'TechCrunch', icon: 'TC', color: '#16a34a' },
  'community/reddit_tech': { name: 'Reddit Tech', icon: 'RD', color: '#ef4444' },
  'research/arxiv': { name: 'arXiv', icon: 'AX', color: '#b31b1b' },
  'industry/patent': { name: 'Patent', icon: 'PT', color: '#16a34a' },
  'knowledge/technical_book': { name: 'Tech Book', icon: 'BK', color: '#0ea5e9' },
}

export const getSourceDisplay = (sourceKey) => sourceDisplayMap[sourceKey] || { name: sourceKey, icon: 'DS', color: '#64748b' }

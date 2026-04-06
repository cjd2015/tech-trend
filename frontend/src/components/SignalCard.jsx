import { formatDateTime, getSourceDisplay, formatSignalSourceKey } from '../utils/format'

export default function SignalCard({ signal }) {
  const sourceKey = formatSignalSourceKey(signal.source_type, signal.source_name)
  const sourceInfo = getSourceDisplay(sourceKey)

  return (
    <article className="signal-card">
      <div className="signal-card-header" style={{ borderLeftColor: sourceInfo.color }}>
        <div className="signal-card-icon">{sourceInfo.icon}</div>
        <div>
          <h4>{signal.title || '无标题'}</h4>
          <p className="signal-meta">{sourceInfo.name} • {signal.author || '未知作者'}</p>
        </div>
      </div>
      <div className="signal-card-body">
        {signal.url && (
          <p className="signal-link">
            <a href={signal.url} target="_blank" rel="noopener noreferrer">查看原文</a>
          </p>
        )}
        <p className="signal-detail">采集时间：{formatDateTime(signal.fetched_at)}</p>
        <p className="signal-detail">来源：{signal.source_type}/{signal.source_name}</p>
      </div>
    </article>
  )
}

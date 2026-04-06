import { getSourceDisplay, formatSourceKey } from '../utils/format'

export default function SourceCard({ source, count, onCollect, disabled = false }) {
  const sourceKey = formatSourceKey(source)
  const sourceInfo = getSourceDisplay(sourceKey)
  return (
    <article className="source-card">
      <div className="source-card-icon">{sourceInfo.icon}</div>
      <div>
        <h3 style={{ color: sourceInfo.color }}>{sourceInfo.name}</h3>
        <p>{count} 条信号</p>
      </div>
      <button className="secondary-button" disabled={disabled} onClick={() => onCollect(sourceKey)}>
        {disabled ? '处理中...' : '单源采集'}
      </button>
    </article>
  )
}

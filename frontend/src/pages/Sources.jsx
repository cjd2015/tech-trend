import SourceCard from '../components/SourceCard'
import { formatSourceKey } from '../utils/format'

export default function Sources({ sources, isCollecting, statusMessage, onCollectSource }) {
  const sourceCounts = sources.reduce((acc, item) => {
    acc[formatSourceKey(item)] = item.count
    return acc
  }, {})

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">来源</p>
          <h2>来源管理</h2>
          <p className="page-subtitle">查看来源覆盖量并触发采集。</p>
        </div>
      </div>
      <div className="card-list">
        {sources.map((source) => (
          <SourceCard
            key={formatSourceKey(source)}
            source={source}
            count={sourceCounts[formatSourceKey(source)] || 0}
            onCollect={onCollectSource}
            disabled={isCollecting}
          />
        ))}
      </div>
      {statusMessage && <div className="info-panel">{statusMessage}</div>}
      {sources.length === 0 && <p className="empty-state">暂无来源数据，请先执行采集。</p>}
    </section>
  )
}

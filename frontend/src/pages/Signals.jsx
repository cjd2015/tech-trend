import { useMemo } from 'react'
import SignalCard from '../components/SignalCard'
import { formatSourceKey, getSourceDisplay } from '../utils/format'

export default function Signals({ signals, sources, statusMessage, selectedSource, onSelectSource }) {
  const sourceOptions = useMemo(() => {
    return sources.map((item) => ({
      key: formatSourceKey(item),
      label: `${getSourceDisplay(formatSourceKey(item)).name} (${item.count})`
    }))
  }, [sources])

  const filteredSignals = useMemo(() => {
    if (selectedSource === 'all') return signals
    return signals.filter((signal) => formatSourceKey(signal) === selectedSource)
  }, [signals, selectedSource])

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">信号</p>
          <h2>原始信号流</h2>
          <p className="page-subtitle">查看采集到的原始信号。</p>
        </div>
        <div className="filter-row">
          <select value={selectedSource} onChange={(e) => onSelectSource(e.target.value)}>
            <option value="all">所有来源 ({signals.length})</option>
            {sourceOptions.map((option) => (
              <option key={option.key} value={option.key}>{option.label}</option>
            ))}
          </select>
        </div>
      </div>

      {statusMessage && <div className="info-panel">{statusMessage}</div>}

      <div className="card-list">
        {filteredSignals.map((signal) => (
          <SignalCard key={signal.id} signal={signal} />
        ))}
      </div>

      {filteredSignals.length === 0 && (
        <p className="empty-state">当前没有可显示的信号。请先刷新或执行采集。</p>
      )}
    </section>
  )
}

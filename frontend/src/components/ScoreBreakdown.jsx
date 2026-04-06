import { formatScore } from '../utils/format'

const scoreItems = [
  { key: 'community_score', label: '社区' },
  { key: 'research_score', label: '研究' },
  { key: 'industry_score', label: '产业' },
  { key: 'knowledge_score', label: '知识' },
  { key: 'cross_signal_score', label: '交叉' },
]

export default function ScoreBreakdown({ topic, compact = false }) {
  return (
    <div className={compact ? 'score-grid compact' : 'score-grid'}>
      {scoreItems.map((item) => {
        const value = topic?.[item.key] || 0
        const width = Math.min((value / 30) * 100, 100)
        return (
          <div key={item.key} className="score-row">
            <div className="score-row-head">
              <span>{item.label}</span>
              <strong>{formatScore(value)}</strong>
            </div>
            <div className="score-track">
              <div className="score-fill" style={{ width: `${width}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

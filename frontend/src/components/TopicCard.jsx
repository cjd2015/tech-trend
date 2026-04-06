import { Link } from 'react-router-dom'
import ScoreBreakdown from './ScoreBreakdown'
import { formatDateTime, formatScore, getStatusDisplay } from '../utils/format'

const dimensionMap = {
  community: { label: '社区', icon: 'CM', color: '#ff8a3d' },
  research: { label: '研究', icon: 'RS', color: '#2cb1a6' },
  industry: { label: '产业', icon: 'IN', color: '#7ad67a' },
  knowledge: { label: '知识', icon: 'KN', color: '#4db6ff' },
}

export default function TopicCard({ topic, actionLabel, onAction }) {
  const statusMeta = getStatusDisplay(topic.status)

  return (
    <article className="topic-card">
      <div className="topic-card-head">
        <div>
          <div className={`status-pill ${statusMeta.tone}`}>{statusMeta.label}</div>
          <h3>
            <Link to={`/topics/${topic.id}`}>{topic.canonical_name}</Link>
          </h3>
        </div>
        <div className="topic-score">
          <span>总分</span>
          <strong>{formatScore(topic.final_score)}</strong>
        </div>
      </div>

      <p className="topic-meta">
        首次出现：{formatDateTime(topic.first_seen_at)} · 最近出现：{formatDateTime(topic.last_seen_at)} · 证据 {topic.evidence_count || 0} 条
      </p>

      <div className="badge-row">
        {(topic.source_types || []).map((sourceType) => {
          const source = dimensionMap[sourceType] || { label: sourceType, icon: 'DS', color: '#64748b' }
          return (
            <span key={sourceType} className="source-badge">
              <span className="source-badge-icon" style={{ background: source.color }}>{source.icon}</span>
              {source.label}
            </span>
          )
        })}
      </div>

      <ScoreBreakdown topic={topic} compact />

      <div className="topic-card-foot">
        <Link className="text-link" to={`/topics/${topic.id}`}>查看详情</Link>
        {actionLabel && onAction && (
          <button className="secondary-button" onClick={() => onAction(topic.id)}>
            {actionLabel}
          </button>
        )}
      </div>
    </article>
  )
}

import { Link } from 'react-router-dom'
import { formatDateTime, formatScore, getStatusDisplay } from '../utils/format'

export default function RecordCard({ record }) {
  const statusMeta = getStatusDisplay(record.review_status)

  return (
    <article className="record-card">
      <div className="record-card-head">
        <div>
          <div className={`status-pill ${statusMeta.tone}`}>{statusMeta.label}</div>
          <h3>{record.title}</h3>
          <p className="record-meta">
            主题：
            {' '}
            <Link to={`/topics/${record.topic_id}`}>{record.topic_name || '未关联主题'}</Link>
            {' '}
            · 置信度 {formatScore(record.confidence, 2)}
            {' '}
            · 记录于 {formatDateTime(record.recorded_at)}
          </p>
        </div>
        <div className="record-score">
          <span>主题分</span>
          <strong>{formatScore(record.topic_score)}</strong>
        </div>
      </div>

      {record.summary && <p className="record-summary">{record.summary}</p>}
      {record.record_reason && <p className="record-reason">{record.record_reason}</p>}
    </article>
  )
}

import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import RecordCard from '../components/RecordCard'
import ScoreBreakdown from '../components/ScoreBreakdown'
import { getApi } from '../utils/api'
import {
  formatDateTime,
  formatScore,
  getSourceDisplay,
  getStatusDisplay,
} from '../utils/format'

function ReviewMetric({ label, item }) {
  if (!item) return null

  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{formatScore(item.score, 1)}</strong>
      <p>
        {item.judgement || item.source_type || item.official_alignment || item.clarity || item.recommendation || '无'}
      </p>
    </div>
  )
}

export default function TopicDetail({ dataVersion, onReviewTopic }) {
  const { topicId } = useParams()
  const [topic, setTopic] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    const loadTopic = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await getApi(`/api/topics/${topicId}`)
        if (active) {
          setTopic(response)
        }
      } catch (loadError) {
        if (active) {
          setError(loadError.message)
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadTopic()

    return () => {
      active = false
    }
  }, [dataVersion, topicId])

  if (loading) {
    return <p className="info-panel">正在加载主题详情...</p>
  }

  if (error) {
    return <p className="empty-state">主题详情加载失败：{error}</p>
  }

  if (!topic) {
    return <p className="empty-state">未找到该主题。</p>
  }

  const statusMeta = getStatusDisplay(topic.status)
  const reviewMeta = getStatusDisplay(topic.review?.conclusion)
  const existingRecord = topic.records?.[0]

  return (
    <section>
      <div className="detail-hero">
        <div>
          <div className={`status-pill ${statusMeta.tone}`}>{statusMeta.label}</div>
          <h2>{topic.canonical_name}</h2>
          <p className="page-subtitle">
            首次出现于 {formatDateTime(topic.first_seen_at)}，最近一次证据更新时间 {formatDateTime(topic.last_seen_at)}。
          </p>
          <div className="badge-row">
            {(topic.source_types || []).map((sourceType) => (
              <span key={sourceType} className="source-badge">
                {sourceType}
              </span>
            ))}
          </div>
        </div>
        <div className="hero-stats">
          <div>
            <span>Final Score</span>
            <strong>{formatScore(topic.final_score)}</strong>
          </div>
          <div>
            <span>Evidence</span>
            <strong>{topic.evidence_count || 0}</strong>
          </div>
        </div>
      </div>

      <div className="detail-grid">
        <section className="panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">Scoring</p>
              <h3>评分拆解</h3>
            </div>
            {!existingRecord && onReviewTopic && (
              <button className="secondary-button" onClick={() => onReviewTopic(topic.id)}>
                执行自动审核
              </button>
            )}
          </div>
          <ScoreBreakdown topic={topic} />
          {topic.keywords?.length > 0 && (
            <>
              <p className="eyebrow">Keywords</p>
              <div className="badge-row">
                {topic.keywords.map((keyword) => (
                  <span key={keyword} className="summary-pill">{keyword}</span>
                ))}
              </div>
            </>
          )}
        </section>

        <section className="panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">Auto Review</p>
              <h3>自动审核报告</h3>
            </div>
          </div>
          <div className="badge-row">
            <span className={`status-pill ${reviewMeta.tone}`}>{reviewMeta.label}</span>
            <span className="summary-pill">总分 {formatScore(topic.review?.weighted_total || 0, 2)} / 5.0</span>
          </div>
          <p className="record-summary">{topic.review?.summary || '当前尚未生成自动审核报告。'}</p>

          <div className="metric-grid">
            <ReviewMetric label="时效性" item={topic.review?.timeliness} />
            <ReviewMetric label="可信度" item={topic.review?.credibility} />
            <ReviewMetric label="准确性" item={topic.review?.accuracy} />
            <ReviewMetric label="实用性" item={topic.review?.practicality} />
          </div>

          <div className="stack-list">
            <article className="stack-card">
              <div>
                <h4>安全风险</h4>
                <p>{topic.review?.security?.sensitive_operations?.join('、') || '无风险'}</p>
              </div>
              <strong>{topic.review?.security?.risk_level || 'low'}</strong>
            </article>
            <article className="stack-card">
              <div>
                <h4>合规建议</h4>
                <p>{topic.review?.compliance?.recommendation || '未发现明显合规阻碍。'}</p>
              </div>
              <strong>{topic.review?.compliance?.reverse_engineering ? '高风险' : '通过'}</strong>
            </article>
          </div>
        </section>
      </div>

      <section className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Timeline</p>
            <h3>证据时间线</h3>
          </div>
        </div>
        <div className="timeline-list">
          {(topic.timeline || []).map((item) => (
            <div key={item.evidence_id} className="timeline-item">
              <div className="timeline-mark" />
              <div>
                <strong>{item.title}</strong>
                <p>{item.source_type}/{item.source_name}</p>
                <span>{formatDateTime(item.occurred_at)}</span>
              </div>
            </div>
          ))}
        </div>
        {(topic.timeline || []).length === 0 && <p className="empty-state">暂无时间线证据。</p>}
      </section>

      <section className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Evidence</p>
            <h3>原始证据</h3>
          </div>
        </div>
        <div className="card-list">
          {(topic.evidences || []).map((evidence) => {
            const source = getSourceDisplay(`${evidence.signal.source_type}/${evidence.signal.source_name}`)
            return (
              <article key={evidence.id} className="evidence-card">
                <div className="topic-card-head">
                  <div>
                    <div className="badge-row">
                      <span className="source-badge">
                        <span className="source-badge-icon" style={{ background: source.color }}>{source.icon}</span>
                        {source.name}
                      </span>
                    </div>
                    <h4>{evidence.signal.title || '无标题证据'}</h4>
                    <p className="topic-meta">
                      {evidence.signal.author || '未知作者'} · {formatDateTime(evidence.signal.published_at || evidence.signal.fetched_at)}
                    </p>
                  </div>
                  <div className="record-score">
                    <span>匹配</span>
                    <strong>{evidence.matched_by || 'rule'}</strong>
                  </div>
                </div>
                {evidence.signal.content && <p className="record-summary">{evidence.signal.content}</p>}
                <div className="topic-card-foot">
                  {evidence.signal.url && (
                    <a className="text-link" href={evidence.signal.url} target="_blank" rel="noreferrer">
                      查看原文
                    </a>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      </section>

      <section className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Records</p>
            <h3>关联记录</h3>
          </div>
          <Link className="text-link" to="/records">进入记录库</Link>
        </div>
        <div className="card-list">
          {(topic.records || []).map((record) => (
            <RecordCard key={record.id} record={record} />
          ))}
        </div>
        {(topic.records || []).length === 0 && (
          <p className="empty-state">当前主题尚未生成记录。</p>
        )}
      </section>
    </section>
  )
}

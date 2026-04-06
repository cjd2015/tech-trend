import { Link } from 'react-router-dom'
import TopicCard from '../components/TopicCard'
import {
  formatDateTime,
  formatNumber,
  formatScore,
  getSignalPopularity,
  getSourceDisplay,
  getStatusDisplay,
} from '../utils/format'

function MetricCard({ label, value, note }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{note}</p>
    </article>
  )
}

export default function Dashboard({ signals, sources, topics, records, stats }) {
  const hotSignals = [...signals]
    .map((signal) => ({ ...signal, popularity: getSignalPopularity(signal) }))
    .sort((a, b) => b.popularity - a.popularity)
    .slice(0, 5)

  const leadingTopics = [...topics]
    .sort((a, b) => (b.final_score || 0) - (a.final_score || 0))
    .slice(0, 4)

  const reviewTopics = topics
    .filter((topic) => topic.review)
    .sort((a, b) => (b.review_score || 0) - (a.review_score || 0))
    .slice(0, 5)

  const latestAccepted = records[0]
  const dominantSource = [...sources].sort((a, b) => b.count - a.count)[0]
  const acceptanceRatio = stats.totalTopics > 0 ? Math.round((stats.totalRecords / stats.totalTopics) * 100) : 0

  return (
    <section className="dashboard-page">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">概览</p>
          <h2>技术趋势总览</h2>
          <p className="hero-copy">展示当前采集、聚合、审核和入库结果。</p>
          <div className="hero-notes">
            <span className="summary-pill">保留率 {acceptanceRatio}%</span>
            {dominantSource && (
              <span className="summary-pill">
                主来源 {getSourceDisplay(`${dominantSource.source_type}/${dominantSource.source_name}`).name}
              </span>
            )}
            {latestAccepted && <span className="summary-pill">最新入库 {latestAccepted.title}</span>}
          </div>
        </div>
        <div className="hero-highlight">
          <span>已入库</span>
          <strong>{stats.totalRecords}</strong>
          <p>当前记录数量</p>
        </div>
      </div>

      <div className="metric-grid">
        <MetricCard label="原始信号" value={formatNumber(stats.totalSignals)} note="当前入库的采集条目数" />
        <MetricCard label="聚合主题" value={formatNumber(stats.totalTopics)} note="已归并的技术主题" />
        <MetricCard label="有用记录" value={formatNumber(stats.totalRecords)} note="自动审核后保留的正式记录" />
        <MetricCard label="数据来源" value={formatNumber(stats.totalSources)} note="已接入并可采集的来源" />
      </div>

      <div className="content-grid two-up">
        <section className="panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">主题</p>
              <h3>当前优先级最高的主题</h3>
            </div>
            <Link className="text-link" to="/topics">查看全部</Link>
          </div>
          <div className="card-list">
            {leadingTopics.map((topic) => (
              <TopicCard key={topic.id} topic={topic} />
            ))}
          </div>
          {leadingTopics.length === 0 && <p className="empty-state">当前还没有聚合主题。先运行“聚合主题”或“运行全链路”。</p>}
        </section>

        <section className="panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">审核</p>
              <h3>自动审核得分最高的主题</h3>
            </div>
            <Link className="text-link" to="/topics">查看主题</Link>
          </div>
          <div className="stack-list">
            {reviewTopics.map((topic) => {
              const statusMeta = getStatusDisplay(topic.review_conclusion || topic.status)
              return (
                <Link key={topic.id} to={`/topics/${topic.id}`} className="stack-card">
                  <div>
                    <div className={`status-pill ${statusMeta.tone}`}>{statusMeta.label}</div>
                    <h4>{topic.canonical_name}</h4>
                    <p>自动审核 {formatScore(topic.review_score || 0, 2)} / 5 · 证据 {topic.evidence_count || 0} 条</p>
                  </div>
                  <strong>{formatScore(topic.review_score || 0, 2)}</strong>
                </Link>
              )
            })}
          </div>
          {reviewTopics.length === 0 && <p className="empty-state">当前还没有自动审核结果。</p>}
        </section>
      </div>

      <div className="content-grid two-up">
        <section className="panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">信号</p>
              <h3>原始热度最高的信号</h3>
            </div>
            <Link className="text-link" to="/signals">进入信号池</Link>
          </div>
          <div className="stack-list">
            {hotSignals.map((signal) => {
              const source = getSourceDisplay(`${signal.source_type}/${signal.source_name}`)
              return (
                <article key={signal.id} className="stack-card signal-stack-card">
                  <div>
                    <div className="badge-row">
                      <span className="source-badge">
                        <span className="source-badge-icon" style={{ background: source.color }}>{source.icon}</span>
                        {source.name}
                      </span>
                    </div>
                    <h4>{signal.title || '无标题信号'}</h4>
                    <p>热度 {formatNumber(signal.popularity)} · 采集于 {formatDateTime(signal.fetched_at)}</p>
                  </div>
                  {signal.url && (
                    <a className="text-link" href={signal.url} target="_blank" rel="noreferrer">
                      原文
                    </a>
                  )}
                </article>
              )
            })}
          </div>
          {hotSignals.length === 0 && <p className="empty-state">当前没有热门信号。</p>}
        </section>

        <section className="panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">来源</p>
              <h3>来源分布</h3>
            </div>
            <Link className="text-link" to="/sources">管理来源</Link>
          </div>
          <div className="stack-list">
            {sources.map((source) => {
              const sourceInfo = getSourceDisplay(`${source.source_type}/${source.source_name}`)
              return (
                <article key={`${source.source_type}/${source.source_name}`} className="stack-card">
                  <div>
                    <div className="badge-row">
                      <span className="source-badge">
                        <span className="source-badge-icon" style={{ background: sourceInfo.color }}>{sourceInfo.icon}</span>
                        {sourceInfo.name}
                      </span>
                    </div>
                    <h4>{source.source_name}</h4>
                    <p>{source.source_type} 维度</p>
                  </div>
                  <strong>{formatNumber(source.count)}</strong>
                </article>
              )
            })}
          </div>
          {sources.length === 0 && <p className="empty-state">还没有来源统计。</p>}
        </section>
      </div>

      {records.length > 0 && (
        <section className="panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">记录</p>
              <h3>最新自动入库结果</h3>
            </div>
            <Link className="text-link" to="/records">查看全部</Link>
          </div>
          <div className="stack-list">
            {records.slice(0, 4).map((record) => {
              const statusMeta = getStatusDisplay(record.review_status)
              return (
                <Link key={record.id} to={`/topics/${record.topic_id}`} className="stack-card">
                  <div>
                    <div className={`status-pill ${statusMeta.tone}`}>{statusMeta.label}</div>
                    <h4>{record.title}</h4>
                    <p>{record.topic_name} · 置信度 {formatScore(record.confidence, 2)}</p>
                  </div>
                  <strong>{formatDateTime(record.recorded_at)}</strong>
                </Link>
              )
            })}
          </div>
        </section>
      )}
    </section>
  )
}


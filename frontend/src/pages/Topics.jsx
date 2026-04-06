import { useMemo, useState } from 'react'
import TopicCard from '../components/TopicCard'

const STATUS_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'observed', label: 'Observed' },
  { value: 'candidate', label: 'Candidate' },
  { value: 'validated', label: 'Validated' },
  { value: 'recorded', label: 'Recorded' },
  { value: 'discarded', label: 'Discarded' },
]

export default function Topics({ topics }) {
  const [statusFilter, setStatusFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [minScore, setMinScore] = useState('0')

  const filteredTopics = useMemo(() => {
    const needle = search.trim().toLowerCase()
    const threshold = Number(minScore || 0)

    return topics
      .filter((topic) => statusFilter === 'all' || topic.status === statusFilter)
      .filter((topic) => (topic.final_score || 0) >= threshold)
      .filter((topic) => {
        if (!needle) return true
        return topic.canonical_name.toLowerCase().includes(needle)
      })
      .sort((a, b) => (b.final_score || 0) - (a.final_score || 0))
  }, [minScore, search, statusFilter, topics])

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Topics</p>
          <h2>主题总览</h2>
        </div>
        <div className="filter-row">
          <input
            className="input"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="搜索主题名称"
          />
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <select value={minScore} onChange={(event) => setMinScore(event.target.value)}>
            <option value="0">分数不限</option>
            <option value="5">5 分以上</option>
            <option value="10">10 分以上</option>
            <option value="20">20 分以上</option>
          </select>
        </div>
      </div>

      <div className="card-list">
        {filteredTopics.map((topic) => (
          <TopicCard key={topic.id} topic={topic} />
        ))}
      </div>

      {filteredTopics.length === 0 && (
        <p className="empty-state">当前筛选条件下没有主题。</p>
      )}
    </section>
  )
}

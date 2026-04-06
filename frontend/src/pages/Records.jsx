import { useMemo, useState } from 'react'
import RecordCard from '../components/RecordCard'

const STATUS_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'useful', label: 'Useful' },
]

export default function Records({ records }) {
  const [statusFilter, setStatusFilter] = useState('all')
  const [search, setSearch] = useState('')

  const filteredRecords = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return records
      .filter((record) => statusFilter === 'all' || record.review_status === statusFilter)
      .filter((record) => {
        if (!needle) return true
        return (
          record.title?.toLowerCase().includes(needle) ||
          record.topic_name?.toLowerCase().includes(needle) ||
          record.record_reason?.toLowerCase().includes(needle)
        )
      })
  }, [records, search, statusFilter])

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Records</p>
          <h2>自动审核后的记录库</h2>
        </div>
        <div className="filter-row">
          <input
            className="input"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="搜索记录标题或主题"
          />
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="card-list">
        {filteredRecords.map((record) => (
          <RecordCard key={record.id} record={record} />
        ))}
      </div>

      {filteredRecords.length === 0 && (
        <p className="empty-state">当前没有符合条件的记录。</p>
      )}
    </section>
  )
}

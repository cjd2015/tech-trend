import { NavLink } from 'react-router-dom'

const primaryNav = [
  { path: '/', label: '仪表盘' },
  { path: '/topics', label: '主题' },
  { path: '/records', label: '记录库' },
]

const secondaryNav = [
  { path: '/signals', label: '信号池' },
  { path: '/sources', label: '来源管理' },
]

export default function Sidebar({
  backendStatus,
  stats,
  onCollect,
  onAggregate,
  onPipeline,
  isCollecting,
  isAggregating,
  isRunningPipeline,
}) {
  const backendTone = backendStatus === 'ok' ? 'success' : backendStatus === 'error' ? 'danger' : 'muted'

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-mark">TT</div>
        <div>
          <p className="eyebrow">Tech Trend</p>
          <h1>Tech Trend</h1>
          <p className="sidebar-copy">技术趋势监控面板</p>
        </div>
      </div>

      <div className={`backend-pill ${backendTone}`}>
        <span className="status-dot" />
        Backend {backendStatus === 'ok' ? 'Online' : backendStatus === 'error' ? 'Offline' : 'Loading'}
      </div>

      <div className="sidebar-panel">
        <span className="panel-title">概览</span>
        <div className="sidebar-metrics">
          <div>
            <strong>{stats.totalTopics}</strong>
            <span>主题</span>
          </div>
          <div>
            <strong>{stats.autoRejected}</strong>
            <span>已丢弃</span>
          </div>
          <div>
            <strong>{stats.totalRecords}</strong>
            <span>有用</span>
          </div>
        </div>
      </div>

      <nav className="nav-group">
        <span className="panel-title">工作区</span>
        {primaryNav.map((item) => (
          <NavLink key={item.path} to={item.path} end={item.path === '/'} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <nav className="nav-group secondary">
        <span className="panel-title">底层数据</span>
        {secondaryNav.map((item) => (
          <NavLink key={item.path} to={item.path} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-actions">
        <button className="primary-button" onClick={() => onCollect()} disabled={isCollecting}>
          {isCollecting ? '采集中...' : '同步信号'}
        </button>
        <button className="secondary-button" onClick={onAggregate} disabled={isAggregating}>
          {isAggregating ? '聚合中...' : '聚合主题'}
        </button>
        <button className="ghost-button" onClick={onPipeline} disabled={isRunningPipeline}>
          {isRunningPipeline ? '处理中...' : '运行全链路'}
        </button>
      </div>
    </aside>
  )
}

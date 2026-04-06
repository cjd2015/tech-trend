import { useEffect, useMemo, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import StatusBanner from './components/StatusBanner'
import Dashboard from './pages/Dashboard'
import Records from './pages/Records'
import Signals from './pages/Signals'
import Sources from './pages/Sources'
import TopicDetail from './pages/TopicDetail'
import Topics from './pages/Topics'
import { getApi, postApi } from './utils/api'

function App() {
  const [backendStatus, setBackendStatus] = useState('loading')
  const [signals, setSignals] = useState([])
  const [sources, setSources] = useState([])
  const [topics, setTopics] = useState([])
  const [records, setRecords] = useState([])
  const [selectedSource, setSelectedSource] = useState('all')
  const [statusMessage, setStatusMessage] = useState('正在加载最新趋势数据...')
  const [isCollecting, setIsCollecting] = useState(false)
  const [isAggregating, setIsAggregating] = useState(false)
  const [isRunningPipeline, setIsRunningPipeline] = useState(false)
  const [dataVersion, setDataVersion] = useState(0)

  const COLLECT_TIMEOUT_MS = 180000
  const PIPELINE_TIMEOUT_MS = 180000

  useEffect(() => {
    loadAllData()
  }, [])

  const stats = useMemo(() => {
    const autoRejected = topics.filter((topic) => topic.status === 'discarded').length
    const reviewedTopics = topics.filter((topic) => topic.review).length
    return {
      totalSignals: signals.length,
      totalTopics: topics.length,
      totalRecords: records.length,
      totalSources: sources.length,
      autoRejected,
      reviewedTopics,
    }
  }, [records, signals, sources, topics])

  const loadBackendStatus = async () => {
    try {
      const data = await getApi('/health')
      setBackendStatus(data.status === 'ok' ? 'ok' : 'error')
    } catch (error) {
      console.error('Failed to load backend status:', error)
      setBackendStatus('error')
    }
  }

  const loadAllData = async () => {
    await loadBackendStatus()
    try {
      const [sourceData, signalData, topicData, recordData] = await Promise.all([
        getApi('/api/sources'),
        getApi('/api/signals?limit=200'),
        getApi('/api/topics?limit=200'),
        getApi('/api/topics/records?limit=200'),
      ])
      setSources(sourceData)
      setSignals(signalData)
      setTopics(topicData)
      setRecords(recordData)
      setDataVersion(Date.now())
      setStatusMessage('项目数据已同步到最新视图。')
    } catch (error) {
      console.error('Failed to load data:', error)
      setStatusMessage(`数据加载失败：${error.message}`)
    }
  }

  const handleCollect = async (sourceKey = null) => {
    setIsCollecting(true)
    setStatusMessage(sourceKey ? `正在采集 ${sourceKey} ...` : '正在执行全量采集...')
    try {
      const suffix = sourceKey ? `?source=${encodeURIComponent(sourceKey)}` : ''
      await postApi(`/api/collect${suffix}`, { timeoutMs: COLLECT_TIMEOUT_MS })
      await loadAllData()
      setStatusMessage(sourceKey ? `${sourceKey} 采集完成。` : '全量采集完成。')
    } catch (error) {
      console.error('Collection failed:', error)
      setStatusMessage(`采集失败：${error.message}`)
    } finally {
      setIsCollecting(false)
    }
  }

  const handleAggregate = async () => {
    setIsAggregating(true)
    setStatusMessage('正在聚合主题...')
    try {
      await postApi('/api/topics/aggregate')
      await loadAllData()
      setStatusMessage('主题聚合已完成。')
    } catch (error) {
      console.error('Aggregation failed:', error)
      setStatusMessage(`主题聚合失败：${error.message}`)
    } finally {
      setIsAggregating(false)
    }
  }

  const handlePipeline = async () => {
    setIsRunningPipeline(true)
    setStatusMessage('正在运行主题全链路...')
    try {
      await postApi('/api/topics/pipeline', { timeoutMs: PIPELINE_TIMEOUT_MS })
      await loadAllData()
      setStatusMessage('全链路执行完成。')
    } catch (error) {
      console.error('Pipeline failed:', error)
      setStatusMessage(`全链路执行失败：${error.message}`)
    } finally {
      setIsRunningPipeline(false)
    }
  }

  const handleReviewTopic = async (topicId) => {
    setStatusMessage(`正在执行主题 #${topicId} 的自动审核...`)
    try {
      const result = await postApi(`/api/topics/${topicId}/review`)
      await loadAllData()
      setStatusMessage(
        result.stored
          ? `主题 #${topicId} 已通过自动审核并入库。`
          : `主题 #${topicId} 自动审核未通过，已丢弃。`
      )
    } catch (error) {
      console.error('Failed to review topic:', error)
      setStatusMessage(`自动审核失败：${error.message}`)
    }
  }

  return (
    <div className="app-shell">
      <Sidebar
        backendStatus={backendStatus}
        stats={stats}
        onCollect={handleCollect}
        onAggregate={handleAggregate}
        onPipeline={handlePipeline}
        isCollecting={isCollecting}
        isAggregating={isAggregating}
        isRunningPipeline={isRunningPipeline}
      />

      <div className="workspace">
        <div className="workspace-intro workspace-hero">
          <div>
            <p className="eyebrow">总览</p>
            <h2>技术趋势监控</h2>
            <p className="page-subtitle">查看采集、聚合、审核与入库状态。</p>
          </div>
          <div className="workspace-badge">
            <span>已审核主题</span>
            <strong>{stats.reviewedTopics}</strong>
            <p>当前已生成审核结果</p>
          </div>
        </div>

        <StatusBanner message={statusMessage} />

        <main className="page-shell">
          <Routes>
            <Route
              path="/"
              element={
                <Dashboard
                  signals={signals}
                  sources={sources}
                  topics={topics}
                  records={records}
                  stats={stats}
                />
              }
            />
            <Route path="/topics" element={<Topics topics={topics} />} />
            <Route
              path="/topics/:topicId"
              element={
                <TopicDetail
                  dataVersion={dataVersion}
                  onReviewTopic={handleReviewTopic}
                />
              }
            />
            <Route
              path="/records"
              element={
                <Records records={records} />
              }
            />
            <Route
              path="/signals"
              element={
                <Signals
                  signals={signals}
                  sources={sources}
                  statusMessage=""
                  selectedSource={selectedSource}
                  onSelectSource={setSelectedSource}
                />
              }
            />
            <Route
              path="/sources"
              element={
                <Sources
                  sources={sources}
                  isCollecting={isCollecting}
                  statusMessage=""
                  onCollectSource={handleCollect}
                />
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App

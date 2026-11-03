import { useEffect, useRef, useState } from 'react'
import { getTask, startPipeline } from '../apis'

// 轮询任务状态的间隔（毫秒）
const POLL_INTERVAL = 2000

/**
 * 需求分析流水线的全部业务逻辑：提交任务 → 轮询进度 → 拿到结果
 *
 * 页面组件只需要从这个 hook 里取「状态」和「操作方法」，
 * 轮询、定时器清理等细节全部封装在这里。
 */
export default function usePipeline() {
  const [inputMode, setInputMode] = useState('text') // text | file
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [running, setRunning] = useState(false)
  const [taskId, setTaskId] = useState(null)
  const [stage, setStage] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [savedProjectId, setSavedProjectId] = useState(0)  // >0 表示当前结果已保存为该项目（0=未保存）

  const timerRef = useRef(null)

  const stopPolling = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  // 组件卸载时清理定时器
  useEffect(() => () => stopPolling(), [])

  // 拿到 task_id 后开始轮询任务状态
  useEffect(() => {
    if (!taskId) return
    stopPolling()
    timerRef.current = setInterval(async () => {
      try {
        const task = await getTask(taskId)
        setStage(task.stage || '')
        if (task.status === 'done') {
          stopPolling()
          setRunning(false)
          setStage('')
          setResult(task.result)
        } else if (task.status === 'failed') {
          stopPolling()
          setRunning(false)
          setStage('')
          setError(task.error || '分析失败，请重试')
        }
      } catch (e) {
        stopPolling()
        setRunning(false)
        setStage('')
        setError(
          e?.response?.data?.detail || e?.message || '获取任务状态失败，请检查后端是否启动',
        )
      }
    }, POLL_INTERVAL)
    return stopPolling
  }, [taskId])

  // 提交分析任务：先校验输入，再请求后端拿 task_id
  const submit = async () => {
    setError('')
    setResult(null)
    setSavedProjectId(0)  // 新一轮分析，重置保存联动状态
    stopPolling()   //停掉上一个任务的轮训
    setTaskId(null) // 清空 task_id-清空旧任务
    if (inputMode === 'text' && !text.trim()) {
      setError('请输入需求描述')
      return
    }
    if (inputMode === 'file' && !file) {
      setError('请选择要上传的文件')
      return
    }

    setRunning(true)
    setStage('正在提交任务…')
    try {
      const { task_id } = await startPipeline(
        inputMode === 'file' ? { file } : { text },
      )
      setTaskId(task_id)
    } catch (e) {
      setRunning(false)
      setStage('')
      setError(
        e?.response?.data?.detail || e?.message || '提交任务失败，请检查后端是否启动',
      )
    }
  }

  // 重置：停止轮询并清空全部状态，可重新开始分析
  const reset = () => {
    stopPolling()
    setRunning(false)
    setTaskId(null)
    setResult(null)
    setSavedProjectId(0)
    setStage('')
    setError('')
    setText('')
    setFile(null)
  }

  // 从历史记录还原一次已完成的分析：直接展示当时的结果（后端重启后也可用）
  const loadFromHistory = (historyTaskId, historyResult, historyProjectId) => {
    stopPolling()
    setRunning(false)
    setStage('')
    setError('')
    setTaskId(historyTaskId)
    setResult(historyResult)
    setSavedProjectId(historyProjectId || 0)  // 还原时同步该记录的保存联动状态
  }

  // 保存为项目成功后由 SaveProjectModal 回调：标记当前结果已入库
  const markSaved = (projectId) => {
    setSavedProjectId(projectId || 0)
  }

  return {
    inputMode,
    setInputMode,
    text,
    setText,
    file,
    setFile,
    running,
    taskId,
    stage,
    error,
    result,
    savedProjectId,
    submit,
    reset,
    loadFromHistory,
    markSaved,
  }
}

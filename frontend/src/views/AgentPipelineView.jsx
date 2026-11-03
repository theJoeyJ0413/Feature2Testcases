import { useState } from 'react'

import usePipeline from '../hooks/usePipeline'
import '../css/AgentPipelineView.css'
import ErrorCard from '../components/agents/ErrorCard'
import HistoryDrawer from '../components/agents/HistoryDrawer'
import InputCard from '../components/agents/InputCard'
import ProgressCard from '../components/agents/ProgressCard'
import ResultCard from '../components/agents/ResultCard'
import SettingsModal from '../components/agents/SettingsModal'
import SaveProjectModal from '../components/agents/SaveProjectModal'

/**
 * 主页面：只负责"编排"，不负责细节
 *
 * 业务逻辑（提交、轮询、状态）→ hooks/usePipeline.js
 * 每张卡片的界面 → components/ 下的四个卡片组件
 *
 * 将来加子页面：新建 views/xxx.jsx，再到 App.jsx 里加路由切换即可
 */

function guessTitle(result, text) {
  const md = result?.requirement_content || ''
  const m = md.match(/^#\s+(.+)$/m)   // 需求文档第一行 "# 项目名"
  if (m) return m[1].trim()
  return (text || '').trim().slice(0, 20) || '未命名项目'
}

export default function AgentPipelineView() {
  const p = usePipeline()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [saveOpen, setSaveOpen] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)

  return (
      <div className="pipeline-page">
        {/* 顶部工具栏： 历史记录 + 设置按钮 */}
        <div className='page-toolbar'>
          <button className='btn' onClick={() => setHistoryOpen(true)}>
            历史记录
          </button>
          <button className='btn' onClick={() => setSettingsOpen(true)}>
            模型设置
          </button>
        </div>
        
      <>
      {/* 第一步：输入需求 */}
      <InputCard
        mode={p.inputMode}
        onModeChange={p.setInputMode}
        text={p.text}
        onTextChange={p.setText}
        file={p.file}
        onFileChange={p.setFile}
        running={p.running}
        onSubmit={p.submit}
      />

      {/* 第二步：分析进度（running 时显示） */}
      {p.running && <ProgressCard stage={p.stage} onCancel={p.reset} />}

      {/* 出错提示（error 时显示） */}
      {p.error && <ErrorCard error={p.error} onReset={p.reset} />}

      {/* 第三步：查看和下载结果（result 时显示） */}
      {p.result && (
        <ResultCard 
        taskId={p.taskId} 
        result={p.result} 
        savedProjectId={p.savedProjectId}
        onReset={p.reset} 
        onSaveProject={()=>setSaveOpen(true)}
        />
      )}
    </>

    {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}

    {/* 历史记录抽屉：查看历次分析，点击条目还原结果视图 */}
    {historyOpen && (
      <HistoryDrawer
        onClose={() => setHistoryOpen(false)}
        onOpen={p.loadFromHistory}
      />
    )}

    {/* Agent 完成后：询问是否保存为项目 */}
    {saveOpen && p.result && (
      <SaveProjectModal
        taskId={p.taskId}
        defaultName={guessTitle(p.result, p.text)}
        description={(p.text || '').trim().slice(0, 200)}
        features={p.result.features || []}
        testcases={p.result.testcases || []}
        onSaved={p.markSaved}
        onClose={() => setSaveOpen(false)}
      />
    )}
    </div>
  )
}

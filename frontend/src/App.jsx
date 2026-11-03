import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import AgentPipelineView from './views/AgentPipelineView'
import ProjectsView from './views/ProjectsView'
import FeaturesView from './views/FeaturesView'
import TestcasesView from './views/TestcasesView'
import TestrunsView from './views/TestrunsView'

/**
 * 应用路由配置
 *
 * 新增页面步骤：
 * 1. 在 views/ 下创建新组件（如 HistoryView.jsx）
 * 2. 在下方 Routes 中添加 <Route path="/xxx" element={<XxxView />} />
 * 3. 在 layouts/MainLayout.jsx 的 MENUS 数组中添加菜单项
 */
export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<AgentPipelineView />} />
        <Route path="/projects" element={<ProjectsView />} />
        <Route path="/features" element={<FeaturesView />} />
        <Route path="/testcases" element={<TestcasesView />} />
        <Route path="/testruns" element={<TestrunsView />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

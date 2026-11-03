import { NavLink, Outlet } from 'react-router-dom'
import './MainLayout.css'

/**
 * 主布局：左侧菜单 + 右侧内容
 *
 * 菜单项在 MENUS 数组中配置，新增菜单只需添加一行
 */

const MENUS = [
  { path: '/', label: 'Agent' },
  { path: '/projects', label: '项目管理' },
  { path: '/features', label: '需求管理' },
  { path: '/testcases', label: '测试用例管理' },
  { path: '/testruns', label: '测试运行' }
]

export default function MainLayout() {
  return (
    <div className="main-layout">
      {/* 左侧菜单 */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>智能测试工坊</h2>
        </div>
        <nav className="sidebar-nav">
          {MENUS.map((menu) => (
            <NavLink
              key={menu.path}
              to={menu.path}
              end={menu.path === '/'}
              className={({ isActive }) =>
                isActive ? 'nav-item active' : 'nav-item'
              }
            >
              {menu.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* 右侧内容区 */}
      <main className="content-area">
        <Outlet />
      </main>
    </div>
  )
}

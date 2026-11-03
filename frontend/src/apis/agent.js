import http from './http'

/**
 * Agent 页面接口：提交分析任务、查询状态、下载产物、历史记录、模型设置
 *
 * 对应后端 routes/agent.py（任务相关）、routes/history.py（历史记录）
 * 与 routes/agent_settings.py（设置相关），因都属于 Agent 页面，故一并归入此文件。
 */

/**
 * 提交分析任务
 * @param {{ text?: string, file?: File }} payload 文字或文件
 * @returns {Promise<{task_id: string}>}
 */
export async function startPipeline({ text, file }) {
  const form = new FormData()
  if (file) form.append('file', file)
  if (text) form.append('text', text)
  const { data } = await http.post('/pipeline', form)
  return data
}

/**
 * 查询任务状态
 * @param {string} taskId
 */
export async function getTask(taskId) {
  const { data } = await http.get(`/tasks/${taskId}`)
  return data
}

/**
 * 生成下载地址
 * @param {string} taskId
 * @param {'requirement'|'testcase'} kind
 */
export function downloadUrl(taskId, kind) {
  return `/api/download/${taskId}/${kind}`
}

/**
 * 获取历史记录列表（分页 + 关键字 / 状态筛选 + 保存联动分组）
 * @param {{ page?: number, pageSize?: number, keyword?: string, status?: string, saved?: boolean }} params
 *        saved 不传=全部；false=只看未保存为项目；true=只看已保存
 * @returns {Promise<{items: Array<object>, total: number, page: number, page_size: number}>}
 */
export async function listHistory({ page = 1, pageSize = 20, keyword, status, saved } = {}) {
  const { data } = await http.get('/history', {
    params: { page, page_size: pageSize, keyword, status, saved },
  })
  return data
}

/**
 * 回写「保存为项目」结果：标记该历史任务的成果已入库
 * @param {string} taskId
 * @param {number} projectId 保存到的项目 ID
 */
export async function bindHistoryProject(taskId, projectId) {
  const { data } = await http.put(`/history/${taskId}`, { project_id: projectId })
  return data
}

/**
 * 查询单条历史详情（result 由后端从任务目录重建，可直接还原结果视图）
 * @param {string} taskId
 */
export async function getHistory(taskId) {
  const { data } = await http.get(`/history/${taskId}`)
  return data
}

/**
 * 删除历史记录（后端会一并清理 output 下的任务目录）
 * @param {string} taskId
 */
export async function deleteHistory(taskId) {
  const { data } = await http.delete(`/history/${taskId}`)
  return data
}

/**
 * 获取模型配置：model, baseUrl, apiKey
 */
export async function getSettings() {
  const { data } = await http.get('/settings')
  return data
}

/**
 * 更新模型配置
 * @param {{ model: string, baseUrl: string, apiKey?: string }} payload
 */
export async function updateSettings(payload) {
  const { data } = await http.put('/settings', payload)
  return data
}

import http from './http'

/**
 * 测试运行接口：批次列表 / 创建 / 统计 / 详情 / 记录结果 / 结束运行
 *
 * 对应后端 routes/testruns.py
 *
 * 枚举（与后端校验一致）：
 * - mode：smoke（冒烟）/ full（全量）/ regression（回归）/ custom（自定义）
 * - status：running（进行中）/ completed（已完成）
 * - result：open（待执行）/ pass（通过）/ fail（失败）/ blocked（阻塞）
 * - scope：{ type: 'all' } 或 { type: 'features', feature_ids: number[] }
 */

/**
 * 运行批次列表（分页 + 筛选），每条附带执行统计与项目名
 * @param {{page?: number, page_size?: number, project_id?: number, status?: string, mode?: string, keyword?: string}} params
 * @returns {Promise<{items: Array<object>, total: number, page: number, page_size: number}>}
 */
export async function listTestruns(params = {}) {
  const { data } = await http.get('/testruns', { params })
  return data
}

/**
 * 创建运行批次：后端按项目/需求/优先级/阶段快照用例，初始状态 running
 * @param {{project_id: number, mode?: string, scope?: {type: string, feature_ids?: number[]}, priority?: string, stage?: string}} payload
 * @returns {Promise<object>} 批次详情（含 items 与统计）
 */
export async function createTestrun(payload) {
  const { data } = await http.post('/testruns', payload)
  return data
}

/**
 * 运行统计：执行率 / 通过率 / 结果分布 / 批次数
 * @param {{project_id?: number, days?: number}} params
 * @returns {Promise<{run_count: number, total: number, executed: number, passed: number,
 *   failed: number, blocked: number, open: number, execution_rate: number, pass_rate: number, days: number}>}
 */
export async function getTestrunStats(params = {}) {
  const { data } = await http.get('/testruns/stats', { params })
  return data
}

/**
 * 运行详情：批次信息 + 统计 + 按需求排序的用例快照清单
 * @param {number} run_id
 * @returns {Promise<object>}
 */
export async function getTestrun(run_id) {
  const { data } = await http.get(`/testruns/${run_id}`)
  return data
}

/**
 * 记录单条用例结果（同步回写 testcases.status）
 * @param {number} run_id
 * @param {number} item_id
 * @param {{result?: string, actual?: string, remark?: string}} payload
 * @returns {Promise<object>} 更新后的用例快照项
 */
export async function updateRunItem(run_id, item_id, payload) {
  const { data } = await http.patch(`/testruns/${run_id}/items/${item_id}`, payload)
  return data
}

/**
 * 结束运行（幂等），结束后结果锁定
 * @param {number} run_id
 * @returns {Promise<object>} 批次详情
 */
export async function finishTestrun(run_id) {
  const { data } = await http.post(`/testruns/${run_id}/finish`)
  return data
}

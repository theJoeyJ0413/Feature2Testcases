import http from './http'

/**
 * 测试用例管理接口：列表、手动新建、Agent 批量入库、更新、删除
 * 
 * 对应后端 routes/testcases.py
 * 
 * 字段枚举（与后端校验一致）：
 * - priority：P0 / P1 / P2 / P3
 * - status：open（待执行）/ pass（通过）/ fail（失败）/ blocked（阻塞）
 * - dimension：功能 / 性能 / 安全 / 易用性 / 可靠性 / 兼容性
 * - scenario：正向 / 边界 / 异常
 * - stages（数组，多值）：冒烟 / 通道 / 灰度 / 系统 / 回归 / 验收
 */

/**
 * 测试用例列表；分页、筛选（八个筛选维度可组合，均可不传）
 * 直接进菜单 = 全量；从需求页跳转 = 传 project_id / feature_id 预筛选
 * @param {{page?: number, page_size?: number, project_id?: number, feature_id?: number, priority?: string, scenario?: string, dimension?: string, status?: string, stage?: string, keyword?: string}} params
 *   keyword 为用例标题模糊匹配；stage 为单值，命中 stages 数组包含该阶段的用例
 * @returns {Promise<{items: Array<object>, total: number, page: number, page_size: number}>}
 *   items 为用例数组，每项含 testcase_no / title / module / priority / status /
 *   dimension / scenario / stages（数组）/ precondition / steps（数组）/ expected / actual /
 *   feature_ref（关联需求编号，join features 得到）/ project_id（归属项目）
 */
export async function listTestcases(params = {}) {
    const {data} = await http.get('/testcases', {params})
    return data
}

/**
  * 手动新建测试用例
 * feature_id 随请求体提交（归属需求，真正归属）；testcase_no 由后端按需求内递增生成
 * @param {number} feature_id 归属需求
 * @param {{title: string, module?: string, ...}} payload
 * @returns {Promise<object>} 新建的完整用例记录
 */
export async function createTestcaseManual(feature_id, payload) {
    const {data} = await http.post('/testcases', {...payload, feature_id})
    return data
}

/**
 * 保存 Agent 分析结果中的测试用例（批量入库）
 * 后端按 requirement_ref 匹配项目下 feature_no 得到 feature_id；
 * 缺编号（id）或引用需求不存在的用例跳过（计入 skipped）；
 * 已存在的 (feature_id, testcase_no) 覆盖更新，不重置已有 status（保留执行记录）
 * @param {{project_id: number, testcases: Array<{id?: string, title?: string, requirement_ref?: string, module?: string, priority?: string, dimension?: string, scenario?: string, stages?: Array<string>, precondition?: string, steps?: Array<string>, expected?: string}>}} payload
 * @returns {Promise<{saved: number, skipped: number}>} 保存 / 跳过条数
 */
export async function saveAgentTestcases(payload) {
    const {data} = await http.post('/testcases/save-agent', payload)
    return data
}

/**
 * 更新测试用例
 * payload 只传需要更新的字段（后端白名单：title / module / priority / status /
 * dimension / scenario / stages / precondition / steps / expected / actual）
 * 状态徽标点击切换走此接口，只传 { status }（四态：open / pass / fail / blocked）
 * @param {number} testcase_id
 * @param {object} payload
 * @returns {Promise<object>} 更新后的完整用例记录
 */
export async function updateTestcase(testcase_id, payload) {
    const {data} = await http.put(`/testcases/${testcase_id}`, payload)
    return data
}


/**
 * 删除测试用例
 * @param {number} testcase_id
 * @returns {Promise<{status: string}>}
 */
export async function deleteTestcase(testcase_id) {
    const {data} = await http.delete(`/testcases/${testcase_id}`)
    return data
}

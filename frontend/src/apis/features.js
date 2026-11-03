import http from './http'

/**
 * 需求管理接口：列表、手动新建、Agent导入、更新、删除
 * 
 * 对应后端 routes/features.py
 */

/**
 * 单个项目下的需求列表
 * @param {*} project_id 
 */
export async function listFeatures(project_id) {
    const {data} = await http.get(`/features/${project_id}`)
    return data
}

/**
 * 手动新建需求
 */
export async function createFeatureManual(project_id, payload) {
    const {data} = await http.post(`/features/${project_id}`, {
        ...payload, source: 'manual',
    })
    return data
}

/**
 * 保存Agent分析结果中的需求
 */
export async function saveAgentFeatures(project_id, payload) {
    const {data} = await http.post(`/features/${project_id}/save-agent`, payload)
    return data
}


/**
 * 更新需求
 */
export async function updateFeature(project_id, feature_id, payload) {
    const {data} = await http.put(`/features/${project_id}/${feature_id}`, payload)
    return data
}

/**
 * 删除需求
 */
export async function deleteFeature(project_id, feature_id) {
    const {data} = await http.delete(`/features/${project_id}/${feature_id}`)
    return data
}


/**
 * 针对单个需求生成测试用例
 * 同步接口，耗时会比较长，放宽到3分钟
 */
export async function generateFeatureTestcases(project_id, feature_id) {
    const {data} = await http.post(
        `/features/${project_id}/${feature_id}/generate-testcases`,
        null,
        { timeout: 180000 }
    )
    return data
}
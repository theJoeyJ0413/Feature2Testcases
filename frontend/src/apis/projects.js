import http from './http'

/**
 * 项目管理接口：列表、新建、更新、删除
 *
 * 对应后端 routes/projects.py
 */

/**
 * 项目列表，分页、筛选
 * @param {{page?: number, page_size?: number, source?: string, keyword?: string}} params
 */
export async function listProjects(params = {}) {
    const {data} = await http.get('/projects', {params})
    return data
}

/**
 * 新建项目
 * @param {{name: string, description?: string, source?: 'agent' | 'manual'}} payload
 */
export async function createProject(payload) {
    const {data} = await http.post('/projects', payload)
    return data
}

/**
 * 更新项目
 */

export async function updateProject(id, payload) {
    const {data} = await http.put(`/projects/${id}`, payload)
    return data
}

/**
 * 删除项目
 * @param {number} id
 */
export async function deleteProject(id) {
    const {data} = await http.delete(`/projects/${id}`)
    return data
}

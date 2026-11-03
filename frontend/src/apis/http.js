import axios from 'axios'

// 所有请求都走 /api，开发时由 Vite 代理转发到后端
const http = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

export default http

import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const service = axios.create({
  baseURL: '/api/admin',
  timeout: 10000
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('admin_token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    const res = response.data
    if (res.code === 0) {
      return res
    } else {
      ElMessage.error(res.msg || '操作失败')
      return Promise.reject(new Error(res.msg || 'Error'))
    }
  },
  error => {
    if (error.response && error.response.status === 401) {
      ElMessage.error('登录状态已失效，请重新登录')
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_user')
      router.push('/login')
    } else {
      ElMessage.error(error.response?.data?.msg || error.message || '网络连接异常')
    }
    return Promise.reject(error)
  }
)

export default service

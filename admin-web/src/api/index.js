import request from '../utils/request'

// 1. 认证
export const login = (data) => request.post('/login', data)
export const getAdminInfo = () => request.get('/info')
export const logout = () => request.post('/logout')

// 2. 仪表盘
export const getDashboardStats = () => request.get('/dashboard/stats')

// 3. 启事管理
export const getNotices = (params) => request.get('/notices', { params })
export const getNoticeDetail = (id) => request.get(`/notices/${id}`)
export const updateNotice = (id, data) => request.put(`/notices/${id}`, data)
export const deleteNotice = (id) => request.delete(`/notices/${id}`)
export const batchDeleteNotices = (ids) => request.post('/notices/batch-delete', { ids })

// 4. 用户管理
export const getUsers = (params) => request.get('/users', { params })
export const updateUserMembership = (userId, data) => request.put(`/users/${userId}/membership`, data)
export const updateUserQuota = (userId, data) => request.put(`/users/${userId}/quota`, data)

// 5. 订单管理
export const getOrders = (params) => request.get('/orders', { params })
export const fulfillOrder = (orderId) => request.post(`/orders/${orderId}/fulfill`)

// 6. 智能导入与种子数据
export const extractAndImport = (text) => request.post('/extractAndImport', { text })
export const initSeedData = () => request.post('/initData')

import { defineStore } from 'pinia'
import { login as loginApi, logout as logoutApi } from '../api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('admin_token') || '',
    userInfo: JSON.parse(localStorage.getItem('admin_user') || '{}')
  }),
  getters: {
    isLoggedIn: (state) => !!state.token
  },
  actions: {
    async login(loginForm) {
      const res = await loginApi(loginForm)
      if (res.code === 0 && res.data) {
        this.token = res.data.token
        this.userInfo = res.data.user
        localStorage.setItem('admin_token', res.data.token)
        localStorage.setItem('admin_user', JSON.stringify(res.data.user))
        return res
      }
      throw new Error(res.msg || '登录失败')
    },
    async logout() {
      try {
        await logoutApi()
      } catch (e) {}
      this.token = ''
      this.userInfo = {}
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_user')
    }
  }
})

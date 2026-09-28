import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../layout/Index.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/login/Index.vue'),
    meta: { title: '管理员登录' }
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/dashboard/Index.vue'),
        meta: { title: '数据概览', icon: 'Odometer' }
      },
      {
        path: 'notice',
        name: 'Notice',
        component: () => import('../views/notice/Index.vue'),
        meta: { title: '相亲启事管理', icon: 'Document' }
      },
      {
        path: 'user',
        name: 'User',
        component: () => import('../views/user/Index.vue'),
        meta: { title: '用户与会员管理', icon: 'User' }
      },
      {
        path: 'order',
        name: 'Order',
        component: () => import('../views/order/Index.vue'),
        meta: { title: '订单与支付对账', icon: 'Money' }
      },
      {
        path: 'import',
        name: 'Import',
        component: () => import('../views/import/Index.vue'),
        meta: { title: '智能提取与导入', icon: 'Upload' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('admin_token')
  if (to.path === '/login') {
    if (token) {
      next('/dashboard')
    } else {
      next()
    }
  } else {
    if (!token) {
      next('/login')
    } else {
      next()
    }
  }
})

router.afterEach((to) => {
  document.title = (to.meta.title ? `${to.meta.title} - ` : '') + '爱在黄冈管理后台'
})

export default router

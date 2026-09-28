<template>
  <div class="dashboard-container" v-loading="loading">
    <!-- 核心指标卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card card-user">
          <div class="stat-header">
            <span class="stat-title">注册用户总量</span>
            <el-tag size="small" type="primary">今日 +{{ overview.todayUsers || 0 }}</el-tag>
          </div>
          <div class="stat-value">{{ overview.totalUsers || 0 }}</div>
          <div class="stat-footer">
            <span>会员比例：{{ vipPercent }}%</span>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card card-notice">
          <div class="stat-header">
            <span class="stat-title">相亲启事总量</span>
            <el-tag size="small" type="success">今日 +{{ overview.todayNotices || 0 }}</el-tag>
          </div>
          <div class="stat-value">{{ overview.totalNotices || 0 }}</div>
          <div class="stat-footer">
            <span>男: {{ overview.gender?.male || 0 }} / 女: {{ overview.gender?.female || 0 }}</span>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card card-money">
          <div class="stat-header">
            <span class="stat-title">累计支付收入</span>
            <el-tag size="small" type="warning">今日 +¥{{ overview.todayRevenue || '0.00' }}</el-tag>
          </div>
          <div class="stat-value">¥{{ overview.totalRevenue || '0.00' }}</div>
          <div class="stat-footer">
            <span>会员充值与特权变现</span>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card card-view">
          <div class="stat-header">
            <span class="stat-title">累计启事浏览量</span>
            <el-tag size="small" type="info">今日 +{{ overview.todayViews || 0 }}</el-tag>
          </div>
          <div class="stat-value">{{ overview.totalViews || 0 }}</div>
          <div class="stat-footer">
            <span>匹配与解锁联系方式</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表展示区域 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="16">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="chart-title">近7天用户增长与启事发布走势</span>
            </div>
          </template>
          <div ref="lineChartRef" class="chart-box"></div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="chart-title">会员等级分布</span>
            </div>
          </template>
          <div ref="pieChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷入口卡片 -->
    <el-row :gutter="16" class="action-row">
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <span class="chart-title">常用操作快捷通道</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" plain @click="$router.push('/notice')">
              <el-icon><Document /></el-icon> 审核/检索启事
            </el-button>
            <el-button type="success" plain @click="$router.push('/import')">
              <el-icon><Upload /></el-icon> 批量导入相亲文本
            </el-button>
            <el-button type="warning" plain @click="$router.push('/user')">
              <el-icon><User /></el-icon> 调整会员与配额
            </el-button>
            <el-button type="danger" plain @click="$router.push('/order')">
              <el-icon><Money /></el-icon> 订单与对账补单
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { getDashboardStats } from '../../api'

const loading = ref(false)
const overview = ref({})
const trends = ref({ dates: [], users: [], notices: [], revenues: [] })

const lineChartRef = ref(null)
const pieChartRef = ref(null)
let lineChart = null
let pieChart = null

const vipPercent = computed(() => {
  const total = overview.value.totalUsers || 0
  if (!total) return 0
  const vips = (overview.value.membership?.member || 0) + (overview.value.membership?.vip || 0)
  return Math.round((vips / total) * 100)
})

const fetchStats = async () => {
  loading.value = true
  try {
    const res = await getDashboardStats()
    if (res.code === 0 && res.data) {
      overview.value = res.data.overview || {}
      trends.value = res.data.trends || { dates: [], users: [], notices: [], revenues: [] }
      initCharts()
    }
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

const initCharts = () => {
  if (lineChartRef.value) {
    if (!lineChart) lineChart = echarts.init(lineChartRef.value)
    lineChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['新增用户', '发布启事', '订单金额(元)'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: trends.value.dates
      },
      yAxis: [
        { type: 'value', name: '数量' },
        { type: 'value', name: '金额(元)', position: 'right' }
      ],
      series: [
        {
          name: '新增用户',
          type: 'line',
          smooth: true,
          data: trends.value.users,
          itemStyle: { color: '#409EFF' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(64,158,255,0.3)' },
              { offset: 1, color: 'rgba(64,158,255,0.01)' }
            ])
          }
        },
        {
          name: '发布启事',
          type: 'line',
          smooth: true,
          data: trends.value.notices,
          itemStyle: { color: '#67C23A' }
        },
        {
          name: '订单金额(元)',
          type: 'bar',
          yAxisIndex: 1,
          data: trends.value.revenues,
          itemStyle: { color: '#E6A23C' }
        }
      ]
    })
  }

  if (pieChartRef.value) {
    if (!pieChart) pieChart = echarts.init(pieChartRef.value)
    const m = overview.value.membership || {}
    pieChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} 人 ({d}%)' },
      legend: { bottom: '5%', left: 'center' },
      series: [
        {
          name: '会员分布',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 8,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: { show: false, position: 'center' },
          emphasis: {
            label: { show: true, fontSize: 16, fontWeight: 'bold' }
          },
          data: [
            { value: m.free || 0, name: '普通用户', itemStyle: { color: '#909399' } },
            { value: m.member || 0, name: '月度会员', itemStyle: { color: '#409EFF' } },
            { value: m.vip || 0, name: '年度大会员', itemStyle: { color: '#E6A23C' } }
          ]
        }
      ]
    })
  }
}

const handleResize = () => {
  lineChart?.resize()
  pieChart?.resize()
}

onMounted(() => {
  fetchStats()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  lineChart?.dispose()
  pieChart?.dispose()
})
</script>

<style scoped>
.dashboard-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stat-card {
  border-radius: 8px;
  border: none;
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-title {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin: 12px 0 6px;
}

.stat-footer {
  font-size: 12px;
  color: #909399;
}

.chart-card {
  border-radius: 8px;
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.chart-box {
  width: 100%;
  height: 320px;
}

.action-row {
  margin-top: 4px;
}

.quick-actions {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
</style>

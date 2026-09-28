<template>
  <div class="order-container">
    <!-- 筛选 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="query" class="filter-form">
        <el-form-item label="单号搜索">
          <el-input
            v-model="query.keyword"
            placeholder="商户订单号 / 微信单号"
            clearable
            style="width: 240px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>

        <el-form-item label="支付状态">
          <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 120px">
            <el-option label="已支付" value="paid" />
            <el-option label="待支付" value="pending" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>

        <el-form-item label="购买类型">
          <el-select v-model="query.type" placeholder="全部类型" clearable style="width: 130px">
            <el-option label="月度会员" value="member" />
            <el-option label="年度大会员" value="vip" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 订单列表 -->
    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <span class="total-text">共登记订单 {{ total }} 笔</span>
      </div>

      <el-table :data="list" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" align="center" />

        <el-table-column prop="orderNo" label="商户订单号" min-width="190">
          <template #default="{ row }">
            <span class="code-font">{{ row.orderNo || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="transactionId" label="微信支付单号" min-width="210">
          <template #default="{ row }">
            <span class="code-font">{{ row.transactionId || '尚未产生微信流水' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="用户信息" min-width="160">
          <template #default="{ row }">
            <div>{{ row.userName }}</div>
            <div class="phone-sub">{{ row.userPhone }} (UID: {{ row.userId }})</div>
          </template>
        </el-table-column>

        <el-table-column prop="type" label="购买类型" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.type === 'vip' ? 'warning' : 'primary'" size="small">
              {{ row.type === 'vip' ? '大会员' : '月会员' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="amountYuan" label="实付金额" width="110" align="center">
          <template #default="{ row }">
            <span class="amount-text">¥{{ row.amountYuan }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="订单状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="dark" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="paidAt" label="支付时间" min-width="160" align="center">
          <template #default="{ row }">
            <span>{{ formatTime(row.paidAt) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.status !== 'paid'"
              type="danger"
              size="small"
              link
              @click="handleFulfill(row)"
            >
              手动补单
            </el-button>
            <span v-else style="color: #67c23a; font-size: 13px;">已正常核销</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-box">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getOrders, fulfillOrder } from '../../api'

const loading = ref(false)
const list = ref([])
const total = ref(0)

const query = reactive({
  page: 1,
  pageSize: 10,
  keyword: '',
  status: '',
  type: ''
})

const statusLabel = (s) => {
  const map = { paid: '已支付', pending: '待支付', cancelled: '已取消' }
  return map[s] || s
}

const statusTagType = (s) => {
  const map = { paid: 'success', pending: 'warning', cancelled: 'info' }
  return map[s] || 'info'
}

const formatTime = (iso) => {
  if (!iso) return '-'
  return iso.replace('T', ' ').split('.')[0]
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getOrders(query)
    if (res.code === 0 && res.data) {
      list.value = res.data.list || []
      total.value = res.data.total || 0
    }
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  query.page = 1
  fetchData()
}

const handleReset = () => {
  query.keyword = ''
  query.status = ''
  query.type = ''
  handleSearch()
}

const handleFulfill = (row) => {
  ElMessageBox.confirm(
    `确定要对该订单进行【手动补单】吗？系统将自动将该订单设为已支付，并为用户 (${row.userPhone}) 自动开通对应的会员权益并顺延到期时间。`,
    '手动补单确认',
    {
      type: 'warning',
      confirmButtonText: '确定开通',
      cancelButtonText: '取消'
    }
  ).then(async () => {
    try {
      const res = await fulfillOrder(row.id)
      if (res.code === 0) {
        ElMessage.success('补单成功，用户权益已即时生效')
        fetchData()
      }
    } catch (e) {}
  }).catch(() => {})
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.order-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card, .table-card {
  border-radius: 8px;
}

.filter-form .el-form-item {
  margin-bottom: 0;
  margin-right: 16px;
}

.table-toolbar {
  margin-bottom: 16px;
  display: flex;
  justify-content: flex-end;
}

.total-text {
  font-size: 13px;
  color: #909399;
}

.code-font {
  font-family: monospace;
  font-size: 12px;
  color: #606266;
}

.phone-sub {
  font-size: 12px;
  color: #909399;
}

.amount-text {
  font-weight: bold;
  color: #e6a23c;
  font-size: 14px;
}

.pagination-box {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>

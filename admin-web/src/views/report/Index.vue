<template>
  <div class="report-container">
    <!-- 筛选卡片 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="query" class="filter-form">
        <el-form-item label="处理状态">
          <el-select
            v-model="query.status"
            placeholder="全部状态"
            clearable
            style="width: 140px"
            @change="handleSearch"
          >
            <el-option label="待处理" value="pending" />
            <el-option label="已下架处理" value="resolved" />
            <el-option label="已驳回/忽略" value="rejected" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 查询
          </el-button>
          <el-button @click="resetQuery">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表数据卡片 -->
    <el-card shadow="never" class="table-card">
      <div class="table-header">
        <div class="left-actions">
          <span class="total-text">共收到 {{ total }} 条投诉举报</span>
        </div>
      </div>

      <el-table
        :data="list"
        v-loading="loading"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="70" align="center" />

        <el-table-column label="举报类型" width="130" align="center">
          <template #default="{ row }">
            <el-tag type="danger" size="small">{{ row.reason }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="举报补充描述" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.description || '无详细描述' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="被举报启事对象" min-width="160">
          <template #default="{ row }">
            <div><strong>{{ row.noticeName }}</strong> ({{ row.noticeGender || '保密' }})</div>
            <div style="font-size: 12px; color: #909399;">电话: {{ row.noticePhone || '未公开' }}</div>
          </template>
        </el-table-column>

        <el-table-column label="举报人" width="140" align="center">
          <template #default="{ row }">
            <div>{{ row.reporterName || '普通用户' }}</div>
            <div style="font-size: 12px; color: #909399;">{{ row.reporterPhone || '未知手机' }}</div>
          </template>
        </el-table-column>

        <el-table-column prop="createdAt" label="举报时间" width="165" align="center">
          <template #default="{ row }">
            {{ formatTime(row.createdAt) }}
          </template>
        </el-table-column>

        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'pending'" type="warning" size="small">待处理</el-tag>
            <el-tag v-else-if="row.status === 'resolved'" type="success" size="small">已下架启事</el-tag>
            <el-tag v-else-if="row.status === 'rejected'" type="info" size="small">已驳回</el-tag>
            <el-tag v-else size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="处理结果/说明" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.handleResult">{{ row.handleResult }}</span>
            <span v-else style="color: #c0c4cc;">暂无</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button
                type="danger"
                link
                size="small"
                @click="openHandleDialog(row, 'take_down')"
              >
                下架启事
              </el-button>
              <el-button
                type="info"
                link
                size="small"
                @click="openHandleDialog(row, 'reject')"
              >
                驳回举报
              </el-button>
            </template>
            <span v-else style="color: #909399; font-size: 13px;">已处理</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页组件 -->
      <div class="pagination-box">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchList"
          @current-change="fetchList"
        />
      </div>
    </el-card>

    <!-- 处理弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="actionType === 'take_down' ? '确认下架被举报启事' : '确认驳回该举报'"
      width="480px"
      destroy-on-close
    >
      <div v-if="actionType === 'take_down'" style="margin-bottom: 12px; color: #f56c6c; font-size: 13px;">
        ⚠️ 注意：下架操作将同步从平台物理下架/删除该启事以及相关推荐记录。
      </div>
      <el-form label-position="top">
        <el-form-item label="处理批注 / 回复理由">
          <el-input
            v-model="handleRemark"
            type="textarea"
            :rows="3"
            :placeholder="actionType === 'take_down' ? '请输入下架原因（默认为“违规已下架处理”）' : '请输入驳回理由（默认为“经核实不构成违规，驳回举报”）'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button :type="actionType === 'take_down' ? 'danger' : 'primary'" :loading="submitting" @click="confirmHandle">
            确定处理
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getReports, handleReport } from '../../api'

const query = reactive({
  status: '',
  page: 1,
  pageSize: 20
})

const list = ref([])
const total = ref(0)
const loading = ref(false)

const dialogVisible = ref(false)
const currentReport = ref(null)
const actionType = ref('take_down')
const handleRemark = ref('')
const submitting = ref(false)

const fetchList = async () => {
  loading.value = true
  try {
    const res = await getReports(query)
    if (res.code === 0 && res.data) {
      list.value = res.data.reports || []
      total.value = res.data.total || 0
    }
  } catch (err) {
    ElMessage.error('获取举报列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  query.page = 1
  fetchList()
}

const resetQuery = () => {
  query.status = ''
  query.page = 1
  query.pageSize = 20
  fetchList()
}

const openHandleDialog = (row, action) => {
  currentReport.value = row
  actionType.value = action
  handleRemark.value = ''
  dialogVisible.value = true
}

const confirmHandle = async () => {
  if (!currentReport.value) return
  submitting.value = true
  try {
    const res = await handleReport(currentReport.value.id, {
      action: actionType.value,
      remark: handleRemark.value.trim()
    })
    if (res.code === 0) {
      ElMessage.success('处理成功')
      dialogVisible.value = false
      fetchList()
    } else {
      ElMessage.error(res.msg || '处理失败')
    }
  } catch (e) {
    ElMessage.error('网络请求失败')
  } finally {
    submitting.value = false
  }
}

const formatTime = (isoStr) => {
  if (!isoStr) return '-'
  const d = new Date(isoStr)
  if (isNaN(d.getTime())) return isoStr
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.report-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.filter-card {
  border-radius: 8px;
}
.table-card {
  border-radius: 8px;
}
.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.total-text {
  font-size: 14px;
  color: #606266;
}
.pagination-box {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
}
</style>

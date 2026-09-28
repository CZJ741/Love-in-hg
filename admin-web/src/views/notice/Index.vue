<template>
  <div class="notice-container">
    <!-- 筛选卡片 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="query" class="filter-form">
        <el-form-item label="关键字">
          <el-input
            v-model="query.keyword"
            placeholder="姓名/昵称/手机号/职业"
            clearable
            style="width: 220px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>

        <el-form-item label="性别">
          <el-select v-model="query.gender" placeholder="全部" clearable style="width: 100px">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>

        <el-form-item label="房产归属">
          <el-select v-model="query.housingLocation" placeholder="全部" clearable style="width: 110px">
            <el-option label="本地" value="本地" />
            <el-option label="外地" value="外地" />
          </el-select>
        </el-form-item>

        <el-form-item label="体制内">
          <el-select v-model="query.isPublicSector" placeholder="全部" clearable style="width: 110px">
            <el-option label="体制内" value="true" />
            <el-option label="非体制" value="false" />
          </el-select>
        </el-form-item>

        <el-form-item label="来源">
          <el-select v-model="query.source" placeholder="全部" clearable style="width: 120px">
            <el-option label="用户自发" value="user" />
            <el-option label="种子数据" value="seed" />
            <el-option label="文本导入" value="import" />
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

    <!-- 数据表格卡片 -->
    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="left-actions">
          <el-button
            type="danger"
            plain
            :disabled="!selectedIds.length"
            @click="handleBatchDelete"
          >
            <el-icon><Delete /></el-icon> 批量删除 ({{ selectedIds.length }})
          </el-button>
        </div>
        <div class="right-actions">
          <span class="total-text">共找到 {{ total }} 条启事</span>
        </div>
      </div>

      <el-table
        :data="list"
        v-loading="loading"
        border
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column prop="id" label="ID" width="70" align="center" />

        <el-table-column label="姓名/昵称" min-width="120">
          <template #default="{ row }">
            <div class="name-cell">
              <span class="real-name">{{ row.name }}</span>
              <span v-if="row.nickname" class="nickname">({{ row.nickname }})</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="gender" label="性别" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.gender === '男' ? 'primary' : 'danger'" size="small">
              {{ row.gender }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="age" label="年龄" width="70" align="center" />

        <el-table-column prop="phone" label="联系电话" min-width="130" align="center">
          <template #default="{ row }">
            <span class="phone-text">{{ row.phone || '未填写' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="occupation" label="职业" min-width="120" show-overflow-tooltip />

        <el-table-column prop="income" label="月收入" min-width="100" align="center" />

        <el-table-column label="房产/体制" min-width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info" style="margin-right: 4px;">{{ row.housingLocation }}</el-tag>
            <el-tag size="small" :type="row.isPublicSector ? 'success' : 'info'">
              {{ row.isPublicSector ? '体制内' : '体制外' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="source" label="数据来源" width="95" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="plain" :type="sourceTagType(row.source)">
              {{ sourceLabel(row.source) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="照片" width="70" align="center">
          <template #default="{ row }">
            <span v-if="row.images && row.images.length" class="photo-badge">
              📷 {{ row.images.length }}
            </span>
            <span v-else style="color: #c0c4cc;">-</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button type="info" link size="small" @click="handleDetail(row)">
              详情
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-box">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 编辑抽屉弹窗 -->
    <el-drawer
      v-model="editVisible"
      :title="editForm.id ? '编辑相亲启事资料' : '查看相亲启事详情'"
      size="520px"
    >
      <el-form :model="editForm" label-width="90px" class="edit-form">
        <el-form-item label="真实姓名">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="显示昵称">
          <el-input v-model="editForm.nickname" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="editForm.phone" />
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="editForm.gender">
            <el-radio label="男">男</el-radio>
            <el-radio label="女">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="年龄">
          <el-input-number v-model="editForm.age" :min="18" :max="100" />
        </el-form-item>
        <el-form-item label="身高(cm)">
          <el-input-number v-model="editForm.height" :min="0" :max="230" />
        </el-form-item>
        <el-form-item label="体重(kg)">
          <el-input-number v-model="editForm.weight" :min="0" :max="200" />
        </el-form-item>
        <el-form-item label="房产所在地">
          <el-radio-group v-model="editForm.housingLocation">
            <el-radio label="本地">本地</el-radio>
            <el-radio label="外地">外地</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="工作职业">
          <el-input v-model="editForm.occupation" />
        </el-form-item>
        <el-form-item label="月收入">
          <el-input v-model="editForm.income" />
        </el-form-item>
        <el-form-item label="体制内单位">
          <el-switch v-model="editForm.isPublicSector" />
        </el-form-item>
        <el-form-item label="微信/社交号">
          <el-input v-model="editForm.socialAccount" />
        </el-form-item>
        <el-form-item label="发布者角色">
          <el-input v-model="editForm.publisherRole" placeholder="本人/父母/亲友" />
        </el-form-item>
        <el-form-item label="备注/要求">
          <el-input
            v-model="editForm.remark"
            type="textarea"
            :rows="3"
            placeholder="择偶标准或个人简介..."
          />
        </el-form-item>

        <el-form-item label="已有照片" v-if="editForm.images && editForm.images.length">
          <div class="photo-preview-grid">
            <el-image
              v-for="(img, idx) in editForm.images"
              :key="idx"
              :src="img"
              :preview-src-list="editForm.images"
              class="preview-img"
              fit="cover"
            />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="drawer-footer">
          <el-button @click="editVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">保存修改</el-button>
        </div>
      </template>
    </el-drawer>

    <!-- 详情模态框 -->
    <el-dialog v-model="detailVisible" title="启事完整信息" width="560px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="启事ID">{{ detailData.id }}</el-descriptions-item>
        <el-descriptions-item label="真实姓名">{{ detailData.name }}</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ detailData.phone }}</el-descriptions-item>
        <el-descriptions-item label="微信号">{{ detailData.socialAccount || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="性别/年龄">{{ detailData.gender }} / {{ detailData.age }}岁</el-descriptions-item>
        <el-descriptions-item label="身高/体重">{{ detailData.height || '-' }}cm / {{ detailData.weight || '-' }}kg</el-descriptions-item>
        <el-descriptions-item label="房产情况">{{ detailData.housingLocation }}</el-descriptions-item>
        <el-descriptions-item label="单位性质">{{ detailData.isPublicSector ? '体制内' : '体制外' }}</el-descriptions-item>
        <el-descriptions-item label="工作职业" :span="2">{{ detailData.occupation || '-' }}</el-descriptions-item>
        <el-descriptions-item label="月收入" :span="2">{{ detailData.income || '-' }}</el-descriptions-item>
        <el-descriptions-item label="择偶标准/备注" :span="2">{{ detailData.remark || '无' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">{{ detailData.createdAt }}</el-descriptions-item>
      </el-descriptions>

      <div v-if="detailData.images && detailData.images.length" style="margin-top: 16px;">
        <div style="font-weight: 600; margin-bottom: 8px;">照片预览 ({{ detailData.images.length }})：</div>
        <div class="photo-preview-grid">
          <el-image
            v-for="(img, idx) in detailData.images"
            :key="idx"
            :src="img"
            :preview-src-list="detailData.images"
            class="preview-img"
            fit="cover"
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getNotices, getNoticeDetail, updateNotice, deleteNotice, batchDeleteNotices } from '../../api'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const selectedIds = ref([])

const query = reactive({
  page: 1,
  pageSize: 10,
  keyword: '',
  gender: '',
  housingLocation: '',
  isPublicSector: '',
  source: ''
})

const editVisible = ref(false)
const saving = ref(false)
const editForm = ref({})

const detailVisible = ref(false)
const detailData = ref({})

const sourceLabel = (s) => {
  const map = { user: '用户发布', seed: '种子预置', import: '文本导入' }
  return map[s] || s
}

const sourceTagType = (s) => {
  const map = { user: 'success', seed: 'info', import: 'warning' }
  return map[s] || ''
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getNotices(query)
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
  query.gender = ''
  query.housingLocation = ''
  query.isPublicSector = ''
  query.source = ''
  handleSearch()
}

const handleSelectionChange = (rows) => {
  selectedIds.value = rows.map(r => r.id)
}

const handleDetail = async (row) => {
  try {
    const res = await getNoticeDetail(row.id)
    if (res.code === 0) {
      detailData.value = res.data
      detailVisible.value = true
    }
  } catch (e) {}
}

const handleEdit = (row) => {
  editForm.value = JSON.parse(JSON.stringify(row))
  editVisible.value = true
}

const handleSave = async () => {
  saving.value = true
  try {
    const res = await updateNotice(editForm.value.id, editForm.value)
    if (res.code === 0) {
      ElMessage.success('启事资料更新成功')
      editVisible.value = false
      fetchData()
    }
  } catch (err) {
    console.error(err)
  } finally {
    saving.value = false
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定要彻底删除启事 "${row.name}" 吗？此操作无法撤销。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消'
  }).then(async () => {
    const res = await deleteNotice(row.id)
    if (res.code === 0) {
      ElMessage.success('已成功删除')
      fetchData()
    }
  }).catch(() => {})
}

const handleBatchDelete = () => {
  ElMessageBox.confirm(`确定要批量删除选中的 ${selectedIds.value.length} 条启事吗？`, '批量删除', {
    type: 'warning',
    confirmButtonText: '批量删除',
    cancelButtonText: '取消'
  }).then(async () => {
    const res = await batchDeleteNotices(selectedIds.value)
    if (res.code === 0) {
      ElMessage.success(res.msg || '批量删除成功')
      selectedIds.value = []
      fetchData()
    }
  }).catch(() => {})
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.notice-container {
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
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.total-text {
  font-size: 13px;
  color: #909399;
}

.name-cell {
  display: flex;
  flex-direction: column;
}

.real-name {
  font-weight: 500;
  color: #303133;
}

.nickname {
  font-size: 12px;
  color: #909399;
}

.phone-text {
  font-family: monospace;
  font-weight: 500;
}

.photo-badge {
  color: #409EFF;
  font-size: 12px;
}

.pagination-box {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.photo-preview-grid {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.preview-img {
  width: 72px;
  height: 72px;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>

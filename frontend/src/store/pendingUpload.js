/**
 * 临时存储待上传的文件、需求和可选研究参数
 * 用于首页点击启动引擎后立即跳转，在Process页面再进行API调用
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  researchEnabled: false,
  researchQuery: '',
  isPending: false
})

export function setPendingUpload(files, requirement, options = {}) {
  state.files = files
  state.simulationRequirement = requirement
  state.researchEnabled = Boolean(options.researchEnabled)
  state.researchQuery = options.researchQuery || ''
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    researchEnabled: state.researchEnabled,
    researchQuery: state.researchQuery,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.researchEnabled = false
  state.researchQuery = ''
  state.isPending = false
}

export default state

import axios from 'axios'
import { fetchAuthSession } from 'aws-amplify/auth'

const BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({ baseURL: BASE })

// Attach Cognito Bearer token to every request
api.interceptors.request.use(async config => {
  try {
    const session = await fetchAuthSession()
    const idToken = session.tokens?.idToken?.toString()
    if (idToken) config.headers['Authorization'] = `Bearer ${idToken}`
  } catch {
    // No active session
  }
  return config
})

// On 401, force re-login
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) window.location.href = '/'
    return Promise.reject(err)
  }
)

export const getDevices = (page = 1, pageSize = 50, search = '') =>
  api.get('/api/devices', {
    params: { page, page_size: pageSize, search: search || undefined },
  })

export const getVariables = (deviceLabel, page = 1, pageSize = 100, search = '') =>
  api.get(`/api/devices/${deviceLabel}/variables`, {
    params: { page, page_size: pageSize, search: search || undefined },
  })

export const fetchValues = (deviceLabel, varLabel, startMs, endMs, tzOffset) =>
  api.post('/api/data/values', {
    device_label: deviceLabel,
    var_label: varLabel,
    start_ms: startMs,
    end_ms: endMs,
    tz_offset: tzOffset,
  })

export const generateReport = (config, components, allData) =>
  api.post('/api/generate', { config, components, all_data: allData })

export const listConfigs = () => api.get('/api/configs')
export const getConfig = (id) => api.get(`/api/configs/${id}`)
export const saveConfig = (name, config, components, histRows) =>
  api.post('/api/configs', { name, config, components, hist_rows: histRows })
export const updateConfig = (id, name, config, components, histRows) =>
  api.put(`/api/configs/${id}`, { name, config, components, hist_rows: histRows })
export const deleteConfig = (id) => api.delete(`/api/configs/${id}`)

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './projects/daily_report_25_26/styles/theme.css'
import { useAuthStore } from './projects/daily_report_25_26/store/auth'
import { initAuditTracking } from './projects/daily_report_25_26/services/audit'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

initAuditTracking({
  router,
  resolveAuthStore: () => useAuthStore(pinia),
})

app.mount('#app')

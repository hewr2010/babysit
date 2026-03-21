import { createApp } from 'vue'
import { createPinia } from 'pinia'
import VueECharts from 'vue-echarts'
import App from './App.vue'
import router from './router'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.component('v-chart', VueECharts)
app.mount('#app')

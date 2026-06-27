import { createSSRApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { initPlatform } from './platform'

initPlatform()

export function createApp() {
  const app = createSSRApp(App)
  app.use(createPinia())
  return {
    app
  }
}

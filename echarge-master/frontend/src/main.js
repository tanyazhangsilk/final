import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import VueLazyLoad from 'vue3-lazyload'

import App from './App.vue'
import router from './router'
import './style.css'
import { ensureUserContext } from './config/permissions'

const app = createApp(App)

const getInitialTheme = () => {
  const saved = localStorage.getItem('theme')
  if (saved === 'light' || saved === 'dark') return saved
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

document.documentElement.dataset.theme = getInitialTheme()
ensureUserContext()

app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.use(VueLazyLoad, {
  loading: '',
  error: '',
})

app.mount('#app')

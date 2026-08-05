import { ref } from 'vue'

const STORAGE_KEY = 'cp-theme'
const isDark = ref(localStorage.getItem(STORAGE_KEY) !== 'light')

function applyTheme(dark: boolean) {
  document.documentElement.classList.toggle('dark', dark)
  localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light')
}

applyTheme(isDark.value)

export function useTheme() {
  function toggle() {
    isDark.value = !isDark.value
    applyTheme(isDark.value)
  }
  return { isDark, toggle }
}

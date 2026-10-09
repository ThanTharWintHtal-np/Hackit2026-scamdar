import '@testing-library/jest-dom/vitest'

const storage = new Map()

Object.defineProperty(window, 'localStorage', {
  value: {
    getItem(key) {
      return storage.has(key) ? storage.get(key) : null
    },
    setItem(key, value) {
      storage.set(key, String(value))
    },
    removeItem(key) {
      storage.delete(key)
    },
    clear() {
      storage.clear()
    },
    key(index) {
      return Array.from(storage.keys())[index] ?? null
    },
    get length() {
      return storage.size
    },
  },
  configurable: true,
})
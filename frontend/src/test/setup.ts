import { afterEach, vi } from 'vitest'

afterEach(() => {
  document.body.innerHTML = ''
  vi.restoreAllMocks()
})

if (!Object.getOwnPropertyDescriptor(window.navigator, 'clipboard')) {
  Object.defineProperty(window.navigator, 'clipboard', {
    value: {
      writeText: vi.fn(async () => undefined)
    },
    configurable: true
  })
}

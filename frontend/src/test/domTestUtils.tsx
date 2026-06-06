import React from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { act } from 'react'

export interface RenderResult {
  container: HTMLDivElement
  root: Root
  rerender: (node: React.ReactElement) => void
  unmount: () => void
}

export function renderComponent(node: React.ReactElement): RenderResult {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)

  act(() => {
    root.render(node)
  })

  return {
    container,
    root,
    rerender(nextNode) {
      act(() => {
        root.render(nextNode)
      })
    },
    unmount() {
      act(() => {
        root.unmount()
      })
      container.remove()
    }
  }
}

export function click(element: Element | null): void {
  if (!element) return
  act(() => {
    (element as HTMLElement).click()
  })
}

export function changeInput(element: HTMLInputElement | HTMLTextAreaElement, value: string): void {
  act(() => {
    const descriptor = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), 'value')
    descriptor?.set?.call(element, value)
    element.dispatchEvent(new Event('input', { bubbles: true }))
    element.dispatchEvent(new Event('change', { bubbles: true }))
  })
}

export function keydown(element: Element, key: string, shiftKey = false): void {
  act(() => {
    element.dispatchEvent(new KeyboardEvent('keydown', { key, shiftKey, bubbles: true }))
  })
}

import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import mediumZoom from 'medium-zoom'
import { onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vitepress'
import './custom.css'

function closeOverlay(overlay: HTMLElement) {
  overlay.remove()
  document.body.style.overflow = ''
}

function openMermaidOverlay(source: HTMLElement) {
  const svg = source.querySelector('svg')
  if (!svg) return
  if (document.querySelector('.mermaid-zoom-overlay')) return

  const overlay = document.createElement('div')
  overlay.className = 'mermaid-zoom-overlay'
  overlay.setAttribute('role', 'dialog')
  overlay.setAttribute('aria-modal', 'true')
  overlay.setAttribute('aria-label', 'Diagram zoom')

  const stage = document.createElement('div')
  stage.className = 'mermaid-zoom-stage'

  const clone = svg.cloneNode(true) as SVGElement
  clone.removeAttribute('style')
  clone.setAttribute('width', '100%')
  clone.setAttribute('height', '100%')
  stage.appendChild(clone)
  overlay.appendChild(stage)

  const hint = document.createElement('div')
  hint.className = 'mermaid-zoom-hint'
  hint.textContent = 'Scroll to zoom · drag to pan · Esc or click outside to close'
  overlay.appendChild(hint)

  let scale = 1
  let tx = 0
  let ty = 0
  let dragging = false
  let startX = 0
  let startY = 0

  const apply = () => {
    stage.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`
  }

  overlay.addEventListener(
    'wheel',
    (event) => {
      event.preventDefault()
      const next = Math.min(8, Math.max(0.4, scale * (event.deltaY < 0 ? 1.15 : 0.87)))
      scale = next
      apply()
    },
    { passive: false },
  )

  stage.addEventListener('pointerdown', (event) => {
    dragging = true
    startX = event.clientX - tx
    startY = event.clientY - ty
    stage.setPointerCapture(event.pointerId)
    stage.classList.add('is-dragging')
  })

  stage.addEventListener('pointermove', (event) => {
    if (!dragging) return
    tx = event.clientX - startX
    ty = event.clientY - startY
    apply()
  })

  const stopDrag = () => {
    dragging = false
    stage.classList.remove('is-dragging')
  }
  stage.addEventListener('pointerup', stopDrag)
  stage.addEventListener('pointercancel', stopDrag)

  overlay.addEventListener('click', (event) => {
    if (event.target === overlay) closeOverlay(overlay)
  })

  const onKey = (event: KeyboardEvent) => {
    if (event.key === 'Escape') {
      closeOverlay(overlay)
      document.removeEventListener('keydown', onKey)
    }
  }
  document.addEventListener('keydown', onKey)

  document.body.appendChild(overlay)
  document.body.style.overflow = 'hidden'
}

export default {
  extends: DefaultTheme,
  setup() {
    const route = useRoute()

    const enhance = () => {
      mediumZoom('.main img:not(.no-zoom)', {
        background: 'var(--vp-c-bg)',
        margin: 24,
      })
    }

    onMounted(() => {
      enhance()
      document.addEventListener('click', (event) => {
        const target = (event.target as HTMLElement | null)?.closest('.mermaid')
        if (target) openMermaidOverlay(target as HTMLElement)
      })
    })

    watch(
      () => route.path,
      () => nextTick(enhance),
    )
  },
} satisfies Theme

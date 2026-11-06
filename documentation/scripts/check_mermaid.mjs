#!/usr/bin/env node
/**
 * Parse every Mermaid block in the documentation.
 *
 * VitePress does not fail the build on a Mermaid syntax error; the diagram
 * simply breaks (or, with the wrong Mermaid version, the whole page blanks).
 * This script catches that before deployment.
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { JSDOM } from 'jsdom'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

const dom = new JSDOM('<!doctype html><html><body></body></html>', { pretendToBeVisual: true })
globalThis.window = dom.window
globalThis.document = dom.window.document
globalThis.DOMParser = dom.window.DOMParser
globalThis.Element = dom.window.Element
globalThis.HTMLElement = dom.window.HTMLElement
globalThis.SVGElement = dom.window.SVGElement
globalThis.getComputedStyle = dom.window.getComputedStyle

const mermaid = (await import('mermaid')).default
mermaid.initialize({ startOnLoad: false, theme: 'dark' })

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      if (['node_modules', '.vitepress', '.git'].includes(entry.name)) return []
      return walk(full)
    }
    return entry.name.endsWith('.md') ? [full] : []
  })
}

const files = walk(root)
const block = /```mermaid\n([\s\S]*?)```/g
let total = 0
let failures = 0

for (const file of files) {
  const text = fs.readFileSync(file, 'utf8')
  let match
  while ((match = block.exec(text)) !== null) {
    total += 1
    try {
      await mermaid.parse(match[1])
    } catch (error) {
      failures += 1
      const firstLine = String(error?.message || error).split('\n')[0]
      console.error(`FAIL ${path.relative(root, file)}: ${firstLine}`)
    }
  }
}

console.log(`checked ${total} diagrams in ${files.length} pages, failures ${failures}`)
process.exit(failures === 0 ? 0 : 1)

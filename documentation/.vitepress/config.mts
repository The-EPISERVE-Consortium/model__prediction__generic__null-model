import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

const REPO = 'https://github.com/The-EPISERVE-Consortium/model__prediction__generic__null-model'

// Project pages are served from /<repo>/; local dev and custom domains use /.
const base = (process.env.DOCS_BASE || '/').replace(/\/?$/, '/')

export default withMermaid(
  defineConfig({
    lang: 'en-US',
    title: 'Null Model Wiki',
    description:
      'Documentation for model__prediction__generic__null-model — the EPISERVE forecast floor.',
    base,
    cleanUrls: true,
    publicDir: 'public',
    srcExclude: ['**/AGENTS.md', '**/CLAUDE.md', '**/_how-to-update.md', 'node_modules/**'],
    lastUpdated: true,

    head: [
      ['link', { rel: 'icon', href: '/favicon.svg', type: 'image/svg+xml' }],
      ['meta', { name: 'theme-color', content: '#0d1117' }],
    ],

    markdown: {
      lineNumbers: true,
      theme: { light: 'github-light', dark: 'github-dark' },
    },

    mermaid: {
      theme: 'dark',
      themeVariables: {
        darkMode: true,
        background: '#0d1117',
        primaryColor: '#2d333b',
        primaryTextColor: '#e6edf3',
        primaryBorderColor: '#6d5dfc',
        lineColor: '#8b949e',
        secondaryColor: '#161b22',
        tertiaryColor: '#161b22',
        fontSize: '14px',
      },
    },
    mermaidPlugin: {
      class: 'mermaid',
    },

    themeConfig: {
      logo: '/logo.svg',
      siteTitle: 'Null Model Wiki',

      nav: [
        { text: 'Getting Started', link: '/01-getting-started/overview' },
        { text: 'Deep Dive', link: '/02-architecture/execution-pipeline' },
        { text: 'Onboarding', link: '/onboarding/contributor-guide' },
        { text: 'Source', link: REPO },
      ],

      sidebar: [
        {
          text: 'Onboarding',
          collapsed: false,
          items: [
            { text: 'Contributor Guide', link: '/onboarding/contributor-guide' },
            { text: 'Staff Engineer Guide', link: '/onboarding/staff-engineer-guide' },
            { text: 'Executive Guide', link: '/onboarding/executive-guide' },
            { text: 'Product Manager Guide', link: '/onboarding/product-manager-guide' },
          ],
        },
        {
          text: 'Getting Started',
          collapsed: false,
          items: [
            { text: 'Overview', link: '/01-getting-started/overview' },
            { text: 'Container Contract', link: '/01-getting-started/container-contract' },
            { text: 'Configuration', link: '/01-getting-started/configuration' },
            { text: 'Local Development', link: '/01-getting-started/local-development' },
          ],
        },
        {
          text: 'Deep Dive',
          collapsed: false,
          items: [
            { text: 'Execution Pipeline', link: '/02-architecture/execution-pipeline' },
            { text: 'Time Axis & Target', link: '/02-architecture/series-handling' },
            { text: 'The Null Forecast', link: '/02-architecture/null-forecast' },
            { text: 'Model Card & Validation', link: '/02-architecture/model-card-and-validation' },
          ],
        },
      ],

      outline: { level: [2, 3], label: 'On this page' },

      socialLinks: [{ icon: 'github', link: REPO }],

      search: { provider: 'local' },

      editLink: {
        pattern: `${REPO}/edit/main/documentation/:path`,
        text: 'Edit this page',
      },

      footer: {
        message: 'Generated with Deep Wiki · EPISERVE Consortium',
        copyright: 'MIT licensed',
      },

      docFooter: { prev: 'Previous', next: 'Next' },
      darkModeSwitchLabel: 'Appearance',
      sidebarMenuLabel: 'Menu',
      returnToTopLabel: 'Return to top',
    },
  }),
)

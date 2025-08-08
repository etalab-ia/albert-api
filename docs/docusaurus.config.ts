import { themes as prismThemes } from 'prism-react-renderer';
import type { Config } from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const github_url = 'https://github.com/etalab-ia/OpenGateLLM';
const albert_api_url =  process.env.ALBERT_API_URL || 'https://albert.api.etalab.gouv.fr';

const baseUrl = process.env.DOCUSAURUS_BASE_URL || '/';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)
const { themes } = require('prism-react-renderer');
const config: Config = {
  title: 'OpenGateLLM',
  tagline: 'Opensource API Gateway for LLM',
  favicon: 'img/favicon.ico',

  // Future flags, see https://docusaurus.io/docs/api/docusaurus-config#future
  future: {
    v4: true, // Improve compatibility with the upcoming Docusaurus v4
  },

  // Set the production url of your site here
  url: albert_api_url,
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: baseUrl,

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'etalab-ia', // Usually your GitHub org/user name.
  projectName: 'OpenGateLLM', // Usually your repo name.

  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl:
            'https://github.com/facebook/docusaurus/tree/main/packages/create-docusaurus/templates/shared/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    metadata: [
      { name: 'algolia-site-verification', content: '766474FDFEC7E852' },
    ],
    // Replace with your project's social card
    image: 'img/android-chrome-512x512.png',
    navbar: {
      title: 'OpenGateLLM',
      hideOnScroll: true,
      logo: {
        alt: 'OpenGateLLM Logo',
        src: 'img/favicon.ico',
        href: baseUrl,
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'tutorialSidebar',
          label: 'Documentation',
          position: 'left',
        },
        {
          label: 'API Reference',
          href: albert_api_url + '/reference',
          position: 'left',
        },
        {
          type: 'search',
          position: 'right',
        },
        {
          label: 'Github',
          href: github_url,
          position: 'right',
        },
        {
          type: 'localeDropdown',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {
              label: 'Getting Started',
              to: 'docs/getting-started/configuration',
            }
          ],
        },
        {
          title: 'Community',
          items: [
            {
              label: 'GitHub Issues',
              href: github_url + '/issues',
            },
            {
              label: 'Discussions',
              href: github_url + '/discussions',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'Official instance',
              href: albert_api_url,
            },
            {
              label: 'API Reference',
              href: albert_api_url + '/reference',
            },
            {
              label: 'API Swagger',
              href: albert_api_url + '/swagger',
            },
            {
              label: 'Github',
              href: github_url,
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Etalab.`,
    },
    algolia: {
      // The application ID provided by Algolia
      appId: 'L16S9RBKXB',

      // Public API key: it is safe to commit it
      apiKey: 'beb495bea76be681f1a65d23a0afcb17',

      indexName: 'OpenGateLLM doc',
    },
    prism: {
      theme: themes.github,
      darkTheme: themes.dracula,
    },
  },
};

export default config;

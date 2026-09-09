import { defineConfig } from "vitepress";

export default defineConfig({
  title: "Opportunity Scout",
  description: "Local-first, evidence-led opportunity research for solo founders.",
  lang: "en-US",
  base: "/scout/",
  cleanUrls: true,
  head: [
    ["meta", { name: "theme-color", content: "#0f766e" }],
  ],
  themeConfig: {
    logo: { src: "/radar.svg", alt: "Opportunity Scout" },
    nav: [
      { text: "Guide", link: "/getting-started" },
      { text: "Concepts", link: "/concepts/evidence" },
      { text: "GitHub", link: "https://github.com/mdesmet/scout" },
    ],
    sidebar: [
      {
        text: "Start here",
        items: [
          { text: "Overview", link: "/" },
          { text: "Getting started", link: "/getting-started" },
        ],
      },
      {
        text: "Core concepts",
        items: [
          { text: "Evidence and traceability", link: "/concepts/evidence" },
          { text: "Scoring and qualification", link: "/concepts/scoring" },
        ],
      },
      {
        text: "Guides",
        items: [
          { text: "Investigate a weak score", link: "/guides/investigate" },
          { text: "Pause, redirect, and recover", link: "/guides/recovery" },
        ],
      },
      {
        text: "Reference",
        items: [
          { text: "Local API", link: "/reference/api" },
          { text: "Local data and privacy", link: "/reference/local-data" },
        ],
      },
      {
        text: "Contributing",
        items: [{ text: "Publish the docs", link: "/publishing" }],
      },
    ],
    socialLinks: [
      { icon: "github", link: "https://github.com/mdesmet/scout" },
    ],
    search: { provider: "local" },
    editLink: {
      pattern: "https://github.com/mdesmet/scout/edit/main/docs/:path",
      text: "Edit this page on GitHub",
    },
    footer: {
      message: "Evidence before ideas.",
      copyright: "Opportunity Scout",
    },
  },
});

# Bjarne Meyn's Blog

[![Live Site](https://img.shields.io/badge/Live%20Site-bmeyn.github.io%2Fblog-blue?style=for-the-badge&logo=github-pages)](https://bmeyn.github.io/blog)

[![Jekyll](https://img.shields.io/badge/Jekyll-4.4.1-red?logo=jekyll&logoColor=white)](https://jekyllrb.com/)
[![Chirpy Theme](https://img.shields.io/badge/Theme-Chirpy-brightgreen?logo=github)](https://github.com/cotes2020/jekyll-theme-chirpy/)
[![GitHub license](https://img.shields.io/github/license/cotes2020/chirpy-starter.svg?color=blue)][mit]
[![Build Status](https://github.com/BMeyn/blog/workflows/Build%20and%20Deploy/badge.svg)](https://github.com/BMeyn/blog/actions)

**🌐 Visit the live site: [bmeyn.github.io/blog](https://bmeyn.github.io/blog)**

A personal technical blog focused on software development, technology insights, and hands-on experiments. Featuring in-depth articles about modern development practices, DevOps, data engineering, and emerging technologies. Built with Jekyll and the modern Chirpy theme for optimal performance and SEO.

## ✨ Featured Content

Explore articles covering:
- **DevOps & CI/CD**: Databricks Asset Bundles, deployment automation, and best practices
- **Development Environments**: VSCode DevContainers, containerized development workflows
- **Software Engineering**: Modern development tools, frameworks, and methodologies
- **Technology Insights**: Hands-on experiments with emerging technologies

## 📝 Adding New Blog Posts

To add a new blog post to this blog:

1. Create a new Markdown file in the `_posts` directory with the naming convention:
   ```
   YYYY-MM-DD-title-with-hyphens.md
   ```

2. Add the required front matter at the top of your file:
   ```yaml
   ---
   title: "Your Post Title"
   date: YYYY-MM-DD HH:MM:SS +0000
   categories: [Category1, Category2]
   tags: [tag1, tag2, tag3]
   pin: false  # set to true to pin the post
   ---
   ```

3. Write your content using Markdown syntax below the front matter.

### Example Post Structure

```markdown
---
title: "My New Blog Post"
date: 2025-01-15 14:30:00 +0000
categories: [Development, Tools]
tags: [jekyll, blogging, markdown]
pin: false
---

## Introduction

Your blog content goes here...
```

## 🚀 Local Development

### Prerequisites

- **Ruby** (3.0 or higher) - Programming language runtime
- **Bundler** gem - Ruby dependency management
- **Git** - Version control and submodule support

### Quick Start

1. **Clone and setup** (first time only):
   ```bash
   git clone https://github.com/BMeyn/blog.git
   cd blog
   git submodule update --init --recursive
   ```

2. **Install dependencies**:
   ```bash
   bundle install
   ```

3. **Start the development server**:
   ```bash
   bash tools/run.sh --host 127.0.0.1
   ```
   
   Or use the Jekyll command directly:
   ```bash
   bundle exec jekyll serve --livereload --host 127.0.0.1
   ```

4. **View your site**: Open your browser and navigate to `http://127.0.0.1:4000/blog`

The site will automatically reload when you make changes to your posts or configuration, enabling efficient content development.

### 🧪 Testing

To test the blog for broken links and HTML validation:

```bash
bash tools/test.sh
```

This runs comprehensive checks including:
- Internal link validation
- HTML structure validation
- Asset reference verification
- SEO meta tag validation

### ⚡ Git Hooks

This repository includes git hooks that automatically process blog posts when you commit changes.

**Pre-commit Hook**: Automatically runs `translate.py` on staged markdown files in `_posts/` to convert Notion-style callouts to Jekyll-compatible format.

#### Installation

**For DevContainer users**: Hooks are installed automatically when the container is created.

**For manual setup**:
```bash
bash scripts/install-hooks.sh
```

#### How It Works

When you commit markdown files in `_posts/`, the pre-commit hook:
1. Detects which markdown files are staged
2. Runs `translate.py` to convert Notion callouts
3. Re-stages the converted files
4. Proceeds with the commit

```bash
# Example workflow
git add _posts/2026-01-05-my-post.md
git commit -m "Add new post"
# Hook runs automatically and processes the file
```

#### Bypassing Hooks

In rare cases where you need to skip the hook:
```bash
git commit --no-verify -m "Skip hooks for this commit"
```

For more details, see [scripts/hooks/README.md](scripts/hooks/README.md).

## 📁 Project Structure

```
.
├── _posts/          # 📄 Blog posts (Markdown files with front matter)
├── _tabs/           # 🗂️ Navigation tabs (About, Archives, Categories, Tags)
├── _config.yml      # ⚙️ Site configuration and settings
├── assets/          # 🎨 Images, stylesheets, and static assets
├── tools/           # 🔧 Build and test automation scripts
├── Gemfile          # 💎 Ruby dependencies and versions
└── README.md        # 📖 This documentation file
```

## 🎨 Technology Stack

This blog leverages modern web technologies for optimal performance and developer experience:

- **[Jekyll 4.4.1](https://jekyllrb.com/)** - Static site generator with liquid templating
- **[Chirpy Theme](https://github.com/cotes2020/jekyll-theme-chirpy/)** - Modern, responsive Jekyll theme
- **[GitHub Pages](https://pages.github.com/)** - Automated deployment and hosting
- **[GitHub Actions](https://github.com/features/actions)** - CI/CD pipeline for testing and deployment
- **[HTML Proofer](https://github.com/gjtorikian/html-proofer)** - Automated testing for links and HTML validity
- **[Sass](https://sass-lang.com/)** - CSS preprocessing for maintainable stylesheets

## ⚙️ Customization

For advanced theme customization and configuration options, check out the [Chirpy theme documentation][chirpy]. Key areas for customization include:

- **Theme Settings**: Color schemes, typography, and layout options
- **Social Integration**: GitHub, Twitter, LinkedIn profile links
- **Analytics**: Google Analytics, GoatCounter, and other tracking services
- **Comments**: Disqus, Utterances, or Giscus integration
- **SEO**: Meta tags, structured data, and social media previews

## 🤝 Contributing

Contributions are welcome! If you find issues or have suggestions:

1. **Report Issues**: [Create an issue](https://github.com/BMeyn/blog/issues/new) for bugs or enhancement requests
2. **Suggest Content**: Propose article topics or improvements via issues
3. **Technical Contributions**: Fork the repository, make changes, and submit a pull request

Please ensure all contributions maintain the blog's focus on technical content and professional quality.

## 📄 License

This work is published under [MIT][mit] License.

[chirpy]: https://github.com/cotes2020/jekyll-theme-chirpy/
[mit]: https://github.com/cotes2020/chirpy-starter/blob/master/LICENSE
# Jekyll Blog with Chirpy Theme

Personal blog built with Jekyll 4.4.1 using the Chirpy theme (~7.3), designed for sharing technical content, development insights, and experiences. The site is automatically deployed to GitHub Pages and includes development container support for consistent environments.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Setup

Run these commands to set up the development environment from a fresh clone:

1. **Install build tools (if not already available):**

   ```bash
   # Ubuntu/Debian systems:
   sudo apt-get update && sudo apt-get install -y build-essential

   # RHEL/CentOS/Fedora systems:
   sudo yum groupinstall -y "Development Tools"
   # OR: sudo dnf groupinstall -y "Development Tools"
   ```

   **CRITICAL**: Build tools (gcc, make, etc.) are required for native gem compilation. GitHub Actions runners and DevContainers include these by default.

2. **Configure Ruby environment and PATH:**

   ```bash
   export PATH="$HOME/.local/share/gem/ruby/3.2.0/bin:$PATH"
   ```

   **CRITICAL**: Always export this PATH in every terminal session. Ruby gems install to user directory to avoid permission issues.

3. **Install Bundler (one-time setup):**

   ```bash
   gem install bundler --user-install
   ```

4. **Configure Bundler to install gems locally:**

   ```bash
   bundle config set --local path 'vendor/bundle'
   ```

5. **Install dependencies:**

   ```bash
   bundle install
   ```

   Takes approximately 30 seconds. NEVER CANCEL. Set timeout to 120+ seconds.

6. **Initialize git submodules for Chirpy static assets:**
   ```bash
   git submodule update --init --recursive
   ```
   Required for proper theme functionality. Takes 5-10 seconds.

### Build and Test

- **Build the site:**

  ```bash
  bundle exec jekyll build
  ```

  Takes approximately 1.3 seconds. NEVER CANCEL. Set timeout to 30+ seconds.

- **Test the site with HTML validation:**

  ```bash
  bash tools/test.sh
  ```

  Takes approximately 2.4 seconds total (includes build + validation). NEVER CANCEL. Set timeout to 60+ seconds.

- **Production build (like CI):**
  ```bash
  JEKYLL_ENV=production bundle exec jekyll build -d "_site/blog"
  ```
  Takes approximately 1.3 seconds.

### Development Server

- **Start development server:**

  ```bash
  bundle exec jekyll serve --livereload --host 127.0.0.1
  ```

  Serves at http://127.0.0.1:4000/blog/ with live reload enabled.

- **Using the helper script:**

  ```bash
  bash tools/run.sh --host 127.0.0.1
  ```

  Alternative method using the provided script.

- **Production mode development:**
  ```bash
  bash tools/run.sh --production --host 127.0.0.1
  ```

## Validation

### Manual Testing Requirements

**CRITICAL**: After making any changes, ALWAYS validate with these scenarios:

1. **Build validation:**

   - Run `bundle exec jekyll build` and verify it completes without errors
   - Check `_site` directory is created with expected content

2. **Development server test:**

   - Start server with `bundle exec jekyll serve --host 127.0.0.1`
   - Verify site loads at http://127.0.0.1:4000/blog/
   - Confirm author name "Bjarne Meyn" appears correctly
   - Test at least one blog post renders properly

3. **HTML proofer validation:**

   - Run `bash tools/test.sh`
   - Verify all internal links work
   - Confirm no broken references or missing assets

4. **Live reload functionality:**

   - Start server with `--livereload` flag
   - Make a small change to any markdown file
   - Verify browser updates automatically

5. **Complete end-to-end user scenario:**
   - Navigate to http://127.0.0.1:4000/blog/
   - Verify author name "Bjarne Meyn" appears in page metadata
   - Click through to at least one blog post
   - Verify post content renders with proper styling
   - Check that navigation menu works (About, Archives, etc.)

### CI/CD Validation

Always validate changes match the GitHub Actions workflow:

- Build succeeds: `JEKYLL_ENV=production bundle exec jekyll build -d "_site/blog"`
- Tests pass: `bundle exec htmlproofer _site --disable-external --ignore-urls "/^http:\/\/127.0.0.1/,/^http:\/\/0.0.0.0/,/^http:\/\/localhost/"`

## Important File Locations

### Core Configuration

- `_config.yml` - Main Jekyll site configuration
- `Gemfile` - Ruby dependencies
- `.github/workflows/pages-deploy.yml` - CI/CD pipeline

### Content Areas

- `_posts/` - Blog posts (markdown files with front matter)
- `_tabs/` - Static pages (About, Archives, Categories, Tags)
- `assets/img/` - Images and media files
- `assets/lib/` - Chirpy theme static assets (git submodule)

### Development Tools

- `tools/run.sh` - Development server helper script
- `tools/test.sh` - Build and test script
- `.devcontainer/` - VS Code development container configuration
- `vendor/bundle/` - Local gem installation directory (auto-created)

### Generated Content

- `_site/` - Generated static site (auto-created during build)

## Common Tasks

### Adding New Blog Posts

1. Create new file in `_posts/` with format: `YYYY-MM-DD-title.md`
2. Include proper front matter with title, date, categories, and tags
3. Test with development server to verify rendering
4. Validate with `bash tools/test.sh`

### Modifying Theme Styles

- Custom styles go in `assets/css/`
- Theme modifications may require understanding Chirpy theme structure
- Always test both development and production builds

### Working with Images

- Place images in `assets/img/`
- Reference with relative paths: `/assets/img/filename.jpg`
- Optimize images for web before committing

## Timing Expectations and Timeouts

**CRITICAL TIMING INFORMATION**:

- Dependency installation: ~30 seconds - Set timeout to 120+ seconds
- Site build: ~1.3 seconds - Set timeout to 30+ seconds
- HTML validation: ~2.4 seconds total - Set timeout to 60+ seconds
- Development server startup: ~2-3 seconds - Set timeout to 30+ seconds
- Git submodule init: ~5-10 seconds - Set timeout to 30+ seconds

**NEVER CANCEL long-running operations**. Always wait for completion or use appropriate timeouts.

## Platform Requirements

### Ruby Environment

- Ruby 3.2.3+ (tested with 3.2.3)
- Bundler 2.7.1+
- Gems installed in user directory to avoid permission issues

### System Dependencies

- Ruby 3.2.3+ (tested with 3.2.3)
- Bundler 2.7.1+
- **Build tools** (gcc, make, etc.) - **CRITICAL** for native gem compilation
  - Usually available on GitHub Actions runners and DevContainers
  - Manual installation required on bare-metal systems
- Git (for submodules)
- curl (for testing)

### Known Issues and Workarounds

- **Build failures with native gems**: Install build-essential or Development Tools package for your system
  - Ubuntu/Debian: `sudo apt-get install -y build-essential`
  - RHEL/CentOS/Fedora: `sudo yum groupinstall -y "Development Tools"`
- **Permission denied during gem install**: Use `--user-install` flag and set PATH correctly
- **Missing bundler**: Install with `gem install bundler --user-install`
- **PATH issues**: Always export `PATH="$HOME/.local/share/gem/ruby/3.2.0/bin:$PATH"`
- **Submodule not initialized**: Run `git submodule update --init --recursive`
- **"command not found" for bundle**: Ensure PATH includes gem binary directory

## Troubleshooting

### Build Failures

1. **Install build tools if missing** (see Platform Requirements)
2. Verify Ruby/Bundler installation and PATH
3. Run `bundle install` to update dependencies
4. Initialize submodules if missing assets
5. Check `_config.yml` for syntax errors

### Development Server Issues

1. Ensure port 4000 is available
2. Check baseurl setting in `_config.yml` (should be "/blog")
3. Verify all dependencies are installed

### Test Failures

1. Build the site first with `bundle exec jekyll build`
2. Check for broken internal links
3. Verify all referenced images exist in `assets/img/`

## Quick Reference Commands

### Essential Development Workflow

```bash
# Set PATH (required for each session)
export PATH="$HOME/.local/share/gem/ruby/3.2.0/bin:$PATH"

# One-time setup
git submodule update --init --recursive
bundle config set --local path 'vendor/bundle'
bundle install

# Development cycle
bundle exec jekyll serve --livereload --host 127.0.0.1  # Start dev server
# Make changes...
bash tools/test.sh  # Validate changes
```

### Common File Operations

```bash
ls -la                          # Repository root
ls -la _posts/                  # Blog posts
ls -la _site/                   # Generated site
ls -la assets/img/              # Images
cat _config.yml                 # Site configuration
```

### Status and Information

```bash
bundle exec jekyll --version    # Jekyll version
ruby --version                  # Ruby version
bundle --version                # Bundler version
git submodule status            # Submodule status
```

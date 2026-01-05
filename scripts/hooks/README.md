# Git Hooks

This directory contains git hooks that are automatically installed for this repository.

## Pre-commit Hook

### Purpose
The pre-commit hook automatically runs `translate.py` on any staged markdown files in the `_posts/` directory before each commit. This ensures that Notion-style callouts are converted to Jekyll-compatible format consistently across all commits.

### How It Works

1. **Detects staged files**: When you run `git commit`, the hook checks which markdown files in `_posts/` are staged
2. **Validates environment**: Ensures `tools/translate.py` exists
3. **Processes files**: Runs `python3 tools/translate.py -i <file>` on each staged markdown file
4. **Re-stages changes**: Automatically adds the converted files back to the staging area
5. **Commits**: If all conversions succeed, the commit proceeds with the translated content

### Example Workflow

```bash
# Edit a markdown file
$ vim _posts/2026-01-05-my-post.md

# Stage the file
$ git add _posts/2026-01-05-my-post.md

# Commit (hook runs automatically)
$ git commit -m "Add new post"
Running Notion callout conversion on staged markdown files...
  Processing: _posts/2026-01-05-my-post.md
Re-staging converted files...
Conversion successful. Files staged and ready to commit.
[main abc1234] Add new post
 1 file changed, 50 insertions(+)
```

### What Gets Processed

The hook processes:
- ✅ Markdown files (`.md` extension)
- ✅ Located in `_posts/` directory
- ✅ That are staged for commit (`git add`)

The hook ignores:
- ❌ Non-markdown files
- ❌ Files outside `_posts/` directory
- ❌ Unstaged files
- ❌ Deleted files

### Error Handling

If the translation fails:
```bash
$ git commit -m "Add post"
Running Notion callout conversion on staged markdown files...
  Processing: _posts/2026-01-05-my-post.md
  ERROR: Failed to process _posts/2026-01-05-my-post.md

Error: Translation failed for one or more files.
Please fix the errors above and try committing again.
```

The commit will be **aborted** and you'll need to fix the issue before trying again.

### Bypassing the Hook

In rare cases, you may need to bypass the hook (e.g., emergency fixes, WIP commits):

```bash
# Skip all git hooks (use sparingly!)
$ git commit --no-verify -m "Emergency fix"
```

**Note**: Bypassing the hook means your markdown files won't be processed. Use this only when absolutely necessary.

### Testing the Hook Manually

You can test the hook without making a commit:

```bash
# Stage some markdown files
$ git add _posts/*.md

# Run the hook directly
$ bash scripts/hooks/pre-commit

# Unstage if you don't want to commit
$ git reset
```

### Troubleshooting

**Hook not running:**
- Check if the hook is installed: `ls -la .git/hooks/pre-commit`
- Reinstall hooks: `bash scripts/install-hooks.sh`

**Permission denied:**
- Make sure the hook is executable: `chmod +x scripts/hooks/pre-commit`
- Reinstall hooks: `bash scripts/install-hooks.sh`

**translate.py not found:**
- Verify the script exists: `ls -la tools/translate.py`
- Check your working directory: `pwd` (should be repo root)

**Python errors:**
- Ensure Python 3 is installed: `python3 --version`
- Check translate.py syntax: `python3 tools/translate.py --help`

### Modifying the Hook

The hook script is located at `scripts/hooks/pre-commit` and is version-controlled. To modify:

1. Edit `scripts/hooks/pre-commit`
2. Test your changes: `bash scripts/hooks/pre-commit`
3. Commit the updated hook script
4. All team members will get the update automatically

No need to reinstall - the hook is a symlink that points to this file.

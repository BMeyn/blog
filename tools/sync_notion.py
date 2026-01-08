#!/usr/bin/env python3

"""
Notion to Jekyll Blog Sync Script

Syncs published blog posts from a Notion database directly to Jekyll.
Downloads images, converts content to Markdown, and generates Jekyll front matter.
Converts Notion callout blocks to Jekyll blockquote format.
Upgrades HTTP links to HTTPS.
Deletes posts that are no longer in Notion with status "Posted".

Usage: python3 tools/sync_notion.py

Migration Note:
  - Posts synced with this script will have a 'notion_id' field in their front matter
  - Only posts with 'notion_id' will be managed (updated/deleted) by this script
  - Posts without 'notion_id' are ignored and won't be deleted
  - This allows manual posts to coexist with Notion-synced posts
"""

import os
import sys
import argparse
import requests
import yaml
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from notion_client import Client
from slugify import slugify
import re

# Load environment variables
load_dotenv()
NOTION_TOKEN = os.getenv('NOTION_API_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_POSTS_DATABASE_ID')

# Constants
ASSETS_IMG_PATH = '/assets/img/'

# Detect repository root (supports both devcontainer and GitHub Actions)
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent

def init_notion_client():
    """Initialize Notion API client"""
    if not NOTION_TOKEN:
        print("Error: NOTION_API_TOKEN not found in .env file")
        sys.exit(1)
    if not NOTION_DATABASE_ID:
        print("Error: NOTION_POSTS_DATABASE_ID not found in .env file")
        sys.exit(1)

    notion = Client(auth=NOTION_TOKEN)
    return notion

def get_published_posts(notion):
    """Query all published posts from database"""
    try:
        results = notion.data_sources.query(
            data_source_id=NOTION_DATABASE_ID,
            filter={
                "property": "Status",
                "status": {
                    "equals": "Posted"
                }
            }
        )
        return results['results']
    except Exception as e:
        print(f"Error querying Notion database: {e}")
        sys.exit(1)

# Helper functions for property types
def get_title(prop):
    """Extract title text"""
    if not prop or 'title' not in prop:
        return ''
    return prop['title'][0]['plain_text'] if prop['title'] else ''

def get_select(prop):
    """Extract select value"""
    if not prop or 'select' not in prop:
        return ''
    return prop['select']['name'] if prop['select'] else ''

def get_multi_select(prop):
    """Extract multi-select values"""
    if not prop or 'multi_select' not in prop:
        return []
    return [item['name'] for item in prop['multi_select']]

def get_date(prop):
    """Extract date value"""
    if not prop or 'date' not in prop:
        return None
    return prop['date']['start'] if prop['date'] else None

def get_file_url(prop):
    """Extract file URL"""
    if not prop or 'files' not in prop:
        return None
    if prop['files']:
        file_info = prop['files'][0]
        if 'file' in file_info:
            return file_info['file']['url']  # Notion-hosted
        elif 'external' in file_info:
            return file_info['external']['url']  # External
    return None

def extract_metadata(page):
    """Extract metadata from Notion page properties"""
    props = page['properties']

    # Try to find title property (could be 'Title' or 'Name')
    title_prop = props.get('Title') or props.get('Name') or {}

    metadata = {
        'id': page['id'],
        'title': get_title(title_prop),
        'status': get_select(props.get('Status', {})),
        'categories': get_multi_select(props.get('Category', {})),
        'tags': get_multi_select(props.get('Tags', {})),
        'published_date': get_date(props.get('Date', {})) or get_date(props.get('Published Date', {})),
        'cover_image_url': get_file_url(props.get('Image', {})),
        'last_edited': page['last_edited_time']
    }

    return metadata

def get_page_content(notion, page_id):
    """Retrieve all blocks (content) from a Notion page"""
    blocks = []
    has_more = True
    start_cursor = None

    while has_more:
        response = notion.blocks.children.list(
            block_id=page_id,
            start_cursor=start_cursor,
            page_size=100
        )
        blocks.extend(response['results'])
        has_more = response['has_more']
        start_cursor = response.get('next_cursor')

    return blocks

def get_block_children(notion, block_id):
    """Retrieve child blocks of a block"""
    children = []
    has_more = True
    start_cursor = None

    while has_more:
        response = notion.blocks.children.list(
            block_id=block_id,
            start_cursor=start_cursor,
            page_size=100
        )
        children.extend(response['results'])
        has_more = response['has_more']
        start_cursor = response.get('next_cursor')

    return children

def rich_text_to_markdown(rich_text_array):
    """Convert Notion rich text to Markdown"""
    if not rich_text_array:
        return ''

    result = []
    for text_obj in rich_text_array:
        text = text_obj['plain_text']
        annotations = text_obj['annotations']

        # Apply formatting
        if annotations['bold']:
            text = f'**{text}**'
        if annotations['italic']:
            text = f'*{text}*'
        if annotations['code']:
            text = f'`{text}`'
        if annotations['strikethrough']:
            text = f'~~{text}~~'

        # Handle links
        if text_obj.get('href'):
            text = f'[{text}]({text_obj["href"]})'

        result.append(text)

    return ''.join(result)

def rich_text_to_plain_text(rich_text_array):
    """Convert Notion rich text to plain text"""
    if not rich_text_array:
        return ''
    return ''.join([text_obj['plain_text'] for text_obj in rich_text_array])

def blocks_to_markdown(blocks, notion=None):
    """Convert Notion blocks to Markdown format"""
    markdown_lines = []

    for block in blocks:
        block_type = block['type']

        if block_type == 'paragraph':
            text = rich_text_to_markdown(block['paragraph']['rich_text'])
            markdown_lines.append(text)
            markdown_lines.append('')  # Blank line

        elif block_type == 'heading_1':
            text = rich_text_to_markdown(block['heading_1']['rich_text'])
            markdown_lines.append(f'# {text}')
            markdown_lines.append('')

        elif block_type == 'heading_2':
            text = rich_text_to_markdown(block['heading_2']['rich_text'])
            markdown_lines.append(f'## {text}')
            markdown_lines.append('')

        elif block_type == 'heading_3':
            text = rich_text_to_markdown(block['heading_3']['rich_text'])
            markdown_lines.append(f'### {text}')
            markdown_lines.append('')

        elif block_type == 'bulleted_list_item':
            text = rich_text_to_markdown(block['bulleted_list_item']['rich_text'])
            markdown_lines.append(f'- {text}')

        elif block_type == 'numbered_list_item':
            text = rich_text_to_markdown(block['numbered_list_item']['rich_text'])
            markdown_lines.append(f'1. {text}')

        elif block_type == 'code':
            code = rich_text_to_plain_text(block['code']['rich_text'])
            language = block['code']['language']
            markdown_lines.append(f'```{language}')
            markdown_lines.append(code)
            markdown_lines.append('```')
            markdown_lines.append('')

        elif block_type == 'image':
            if 'file' in block['image']:
                url = block['image']['file']['url']
            else:
                url = block['image']['external']['url']
            caption = rich_text_to_plain_text(block['image'].get('caption', []))
            markdown_lines.append(f'![{caption}]({url})')
            markdown_lines.append('')

        elif block_type == 'callout':
            # Keep as HTML for convert_callouts() to process
            text = rich_text_to_markdown(block['callout']['rich_text'])
            color = block['callout'].get('color', 'blue')

            # Create HTML aside (emoji icon is used for type detection but not included in output)
            class_name = f'{color}_background' if '_background' in color else f'{color}_bg'
            markdown_lines.append(f'<aside class="{class_name}">')
            markdown_lines.append(f'{text}')

            # Handle nested children (bullet points, etc.)
            if block.get('has_children') and notion:
                children = get_block_children(notion, block['id'])
                # Process children recursively
                for child in children:
                    child_type = child['type']
                    if child_type == 'bulleted_list_item':
                        child_text = rich_text_to_markdown(child['bulleted_list_item']['rich_text'])
                        markdown_lines.append(f'- {child_text}')
                    elif child_type == 'numbered_list_item':
                        child_text = rich_text_to_markdown(child['numbered_list_item']['rich_text'])
                        markdown_lines.append(f'1. {child_text}')
                    elif child_type == 'paragraph':
                        child_text = rich_text_to_markdown(child['paragraph']['rich_text'])
                        markdown_lines.append(child_text)

            markdown_lines.append('</aside>')
            markdown_lines.append('')

        elif block_type == 'quote':
            text = rich_text_to_markdown(block['quote']['rich_text'])
            markdown_lines.append(f'> {text}')
            markdown_lines.append('')

        elif block_type == 'divider':
            markdown_lines.append('---')
            markdown_lines.append('')

        elif block_type == 'table_of_contents':
            # Skip table of contents (Jekyll will generate its own)
            pass

    return '\n'.join(markdown_lines)

def download_image(url, slug, image_type='cover'):
    """Download image from Notion and save to assets"""
    if not url:
        return None

    try:
        # Notion URLs expire, so download immediately
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Determine file extension
        content_type = response.headers.get('content-type', '')
        if 'png' in content_type:
            ext = 'png'
        elif 'jpeg' in content_type or 'jpg' in content_type:
            ext = 'jpeg'
        else:
            ext = 'png'  # default

        # Save to assets folder
        if image_type == 'cover':
            filename = f'{slug}-cover.{ext}'
        else:
            filename = f'{slug}-{image_type}.{ext}'

        filepath = REPO_ROOT / 'assets' / 'img' / 'posts' / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'wb') as f:
            f.write(response.content)

        return f'/assets/img/posts/{filename}'

    except Exception as e:
        print(f"  ⚠ Warning: Failed to download image: {e}")
        return None

def extract_image_urls(blocks):
    """Find all image URLs in content blocks"""
    image_urls = []
    for block in blocks:
        if block['type'] == 'image':
            if 'file' in block['image']:
                url = block['image']['file']['url']
            else:
                url = block['image']['external']['url']
            caption = rich_text_to_plain_text(block['image'].get('caption', []))
            image_urls.append({'url': url, 'caption': caption})
    return image_urls

def download_content_images(image_urls, slug):
    """Download all content images and return mapping"""
    image_mapping = {}
    for i, img in enumerate(image_urls, start=1):
        url = img['url']
        local_path = download_image(url, slug, image_type=str(i))

        if local_path:
            image_mapping[url] = local_path

    return image_mapping

def update_image_paths(markdown, image_mapping):
    """Replace Notion image URLs with local paths"""
    for old_url, new_path in image_mapping.items():
        markdown = markdown.replace(old_url, new_path)
    return markdown

def convert_http_to_https(content):
    """Convert all HTTP links to HTTPS in markdown format"""

    # Pattern to find all markdown links with http://
    # Captures: [link text](http://url)
    pattern = r'\[([^\]]+)\]\(http://([^)]+)\)'

    # Replace all http:// with https:// in markdown links
    def replace_url(match):
        link_text = match.group(1)
        url = match.group(2)
        return f'[{link_text}](https://{url})'

    return re.sub(pattern, replace_url, content)

def convert_callouts(content):
    """Convert Notion aside blocks to Jekyll prompt format"""
    # More flexible pattern to handle various whitespace and formatting
    pattern = r'<aside(?:\s+class="([^"]*)")?\s*>(.*?)</aside>'

    def replace_aside(match):
        aside_class = match.group(1) if match.group(1) else ''
        aside_content = match.group(2)

        # First, check for emoji-based mapping
        prompt_class = 'prompt-info'  # default

        # Look for emoji in the first few lines to determine type
        first_lines = aside_content.split('\n')[:3]
        content_text = '\n'.join(first_lines)

        if '⚠️' in content_text:
            prompt_class = 'prompt-warning'
        elif '✅' in content_text or '🎯' in content_text:
            prompt_class = 'prompt-tip'
        elif '❗' in content_text or '🚫' in content_text:
            prompt_class = 'prompt-danger'
        elif '💡' in content_text or '🔍' in content_text:
            prompt_class = 'prompt-info'

        # Override with class-based mapping if class exists
        if aside_class:
            if 'blue_bg' in aside_class or 'blue_background' in aside_class:
                prompt_class = 'prompt-info'
            elif 'yellow_bg' in aside_class or 'yellow_background' in aside_class:
                prompt_class = 'prompt-warning'
            elif 'green_bg' in aside_class or 'green_background' in aside_class:
                prompt_class = 'prompt-tip'
            elif 'red_bg' in aside_class or 'red_background' in aside_class:
                prompt_class = 'prompt-danger'

        # Clean up the content
        lines = aside_content.split('\n')
        clean_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Skip lines that are just emojis or symbols
            # Improved emoji detection
            if re.match(r'^[\U0001F000-\U0001F9FF\u2600-\u26FF\u2700-\u27BF\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\u2B00-\u2BFF\u25A0-\u25FF\u2190-\u21FF\u2900-\u297F]+\s*$', stripped):
                continue

            # Skip warning emoji specifically
            if stripped in ['⚠️', '💡', '🔍', '✅', '❌', '🚀', '📝', '🔧', '🎯', '❗']:
                continue

            clean_lines.append(stripped)

        if not clean_lines:
            return ''

        # First line should be the title
        title_line = clean_lines[0]
        remaining_lines = clean_lines[1:] if len(clean_lines) > 1 else []

        # Build the output
        result = f'> {title_line}'
        if remaining_lines:
            result += '\n>\n'  # Blank line within blockquote
            result += '\n'.join(f'> {line}' for line in remaining_lines)
        result += f'\n{{: .{prompt_class} }}'

        return result

    # Apply the replacement with DOTALL flag to match across newlines
    return re.sub(pattern, replace_aside, content, flags=re.DOTALL)

def generate_frontmatter(metadata, cover_image_path):
    """Generate Jekyll front matter from Notion metadata"""
    # Format date
    if metadata['published_date']:
        # Remove timezone info and add UTC
        date_str = metadata['published_date'].replace('T', ' ').split('.')[0].split('+')[0].strip() + ' +0000'
    else:
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S +0000')

    # Format categories (keep original capitalization)
    categories = metadata['categories']

    # Format tags (lowercase with hyphens)
    tags = [slugify(tag, separator='-').lower() for tag in metadata['tags']]

    # Build front matter
    frontmatter = f"""---
title: "{metadata['title']}"
date: {date_str}
categories: [{', '.join(categories)}]
tags: [{', '.join(tags)}]
notion_id: {metadata['id']}
"""

    if cover_image_path:
        frontmatter += f"""image:
  path: {cover_image_path}
"""

    frontmatter += """pin: false
---
"""

    return frontmatter

def generate_post_filename(metadata):
    """Generate Jekyll post filename"""
    if metadata['published_date']:
        date = metadata['published_date'].split('T')[0]
    else:
        date = datetime.now().strftime('%Y-%m-%d')

    slug = slugify(metadata['title'])
    return f'{date}-{slug}.md'

def write_post(filename, frontmatter, markdown):
    """Write complete post to _posts folder"""
    filepath = REPO_ROOT / '_posts' / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)
        f.write('\n')
        f.write(markdown)

    return filepath

def parse_front_matter(content):
    """Parse YAML front matter from markdown content
    
    Args:
        content: Raw markdown content with front matter
        
    Returns:
        tuple: (front_matter_dict or None, markdown_body or None)
    """
    # Strip leading whitespace and check for front matter
    content = content.lstrip()
    if not content.startswith('---'):
        return None, None
    
    # Extract front matter (between first and second ---)
    parts = content.split('---', 2)
    if len(parts) < 3:
        return None, None
    
    front_matter_str = parts[1]
    markdown_body = parts[2]
    
    # Parse YAML safely
    try:
        front_matter = yaml.safe_load(front_matter_str)
        if front_matter and isinstance(front_matter, dict):
            return front_matter, markdown_body
    except yaml.YAMLError:
        return None, None
    
    return None, None

def get_existing_posts_with_notion_id():
    """Find all existing posts that have a Notion ID in their front matter"""
    posts_dir = REPO_ROOT / '_posts'
    notion_posts = {}  # notion_id -> filepath
    
    if not posts_dir.exists():
        return notion_posts
    
    for filepath in posts_dir.glob('*.md'):
        if filepath.name == '.placeholder':
            continue
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse front matter using shared helper
            front_matter, _ = parse_front_matter(content)
            
            if front_matter:
                notion_id = front_matter.get('notion_id')
                if notion_id:
                    notion_posts[str(notion_id)] = filepath
                
        except Exception as e:
            print(f"  ⚠ Warning: Could not read {filepath}: {e}")
            
    return notion_posts

def extract_image_paths_from_post(filepath):
    """Extract all image paths from a post file"""
    image_paths = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse front matter using shared helper
        front_matter, markdown_body = parse_front_matter(content)
        
        if front_matter:
            # Extract image path from front matter
            if 'image' in front_matter and isinstance(front_matter['image'], dict):
                img_path = front_matter['image'].get('path')
                if img_path and ASSETS_IMG_PATH in img_path:
                    image_paths.append(img_path)
        
        # Find image paths in markdown content ![alt](/assets/img/...)
        if markdown_body:
            for match in re.finditer(rf'!\[.*?\]\(({re.escape(ASSETS_IMG_PATH)}[^)]+)\)', markdown_body):
                image_paths.append(match.group(1))
            
    except Exception as e:
        print(f"  ⚠ Warning: Could not extract images from {filepath}: {e}")
        
    return image_paths

def delete_post_and_images(filepath):
    """Delete a post file and its associated images
    
    Returns:
        tuple: (success: bool, deleted_images: int)
    """
    print(f"  🗑 Deleting post: {filepath.name}")
    
    # Extract image paths first (before deleting the post)
    image_paths = extract_image_paths_from_post(filepath)
    deleted_images = 0
    
    # Delete associated images with path validation
    for img_path in image_paths:
        try:
            # Remove leading slash and construct full path
            img_file = REPO_ROOT / img_path.lstrip('/')
            
            # Validate the path is within the repository
            # resolve() resolves symlinks and .. sequences
            resolved_img = img_file.resolve()
            resolved_repo = REPO_ROOT.resolve()
            
            # Check if the resolved path is inside the repository
            try:
                resolved_img.relative_to(resolved_repo)
            except ValueError:
                print(f"    ⚠ Skipping image outside repository: {img_path}")
                continue
            
            # Delete the image if it exists
            if resolved_img.exists() and resolved_img.is_file():
                resolved_img.unlink()
                print(f"    🗑 Deleted image: {img_path}")
                deleted_images += 1
            else:
                print(f"    ℹ Image not found: {img_path}")
                
        except Exception as e:
            print(f"    ⚠ Error deleting image {img_path}: {e}")
    
    # Delete the post file after images
    try:
        filepath.unlink()
        print(f"  ✓ Deleted post and {deleted_images} associated image(s)")
        return True, deleted_images
    except Exception as e:
        print(f"  ✗ Error deleting post file: {e}")
        return False, deleted_images

def cleanup_orphaned_posts(notion_post_ids, dry_run=False):
    """Delete posts that are no longer in Notion with status 'Posted'"""
    existing_posts = get_existing_posts_with_notion_id()
    deleted_count = 0
    
    if not existing_posts:
        print("  ℹ No posts with Notion IDs found - nothing to clean up")
        return deleted_count
    
    print(f"\n🔍 Checking for posts to delete...")
    print(f"  Found {len(existing_posts)} posts with Notion IDs")
    print(f"  Found {len(notion_post_ids)} published posts in Notion")
    
    for notion_id, filepath in existing_posts.items():
        if notion_id not in notion_post_ids:
            print(f"\n  ⚠ Post no longer in Notion: {filepath.name}")
            print(f"    Notion ID: {notion_id}")
            
            if not dry_run:
                delete_post_and_images(filepath)
                deleted_count += 1
            else:
                print(f"    ✓ Would delete: {filepath}")
                print(f"    ✓ Would delete associated images")
                deleted_count += 1
    
    if deleted_count == 0:
        print("  ✓ No orphaned posts found - all posts are in sync")
    
    return deleted_count

def sync_notion_posts(dry_run=False):
    """Main function to sync all published posts from Notion"""
    print("Initializing Notion client...")
    notion = init_notion_client()

    print("Fetching published posts from Notion database...")
    posts = get_published_posts(notion)
    print(f"Found {len(posts)} published posts\n")

    # Track Notion IDs of all published posts
    notion_post_ids = set()

    for i, page in enumerate(posts, start=1):
        try:
            # Try to get title from various possible property names
            title_prop = page['properties'].get('Title') or page['properties'].get('Name')
            if title_prop and title_prop.get('title'):
                title = title_prop['title'][0]['plain_text'] if title_prop['title'] else 'Untitled'
            else:
                title = 'Untitled'
            print(f"[{i}/{len(posts)}] Processing: {title}")

            # Extract metadata
            metadata = extract_metadata(page)
            notion_post_ids.add(metadata['id'])  # Track this Notion ID
            print(f"  ✓ Extracted metadata")

            # Get content blocks
            blocks = get_page_content(notion, page['id'])
            print(f"  ✓ Retrieved {len(blocks)} content blocks")

            # Convert to markdown
            markdown = blocks_to_markdown(blocks, notion)
            print(f"  ✓ Converted to markdown")

            # Generate slug
            slug = slugify(metadata['title'])

            # Download cover image
            cover_image_path = None
            if metadata['cover_image_url']:
                cover_image_path = download_image(metadata['cover_image_url'], slug, 'cover')
                if cover_image_path:
                    print(f"  ✓ Downloaded cover image: {cover_image_path}")

            # Download content images
            image_urls = extract_image_urls(blocks)
            if image_urls:
                image_mapping = download_content_images(image_urls, slug)
                markdown = update_image_paths(markdown, image_mapping)
                print(f"  ✓ Downloaded {len(image_urls)} content images")

            # Convert HTTP to HTTPS
            markdown = convert_http_to_https(markdown)
            print(f"  ✓ Converted HTTP links to HTTPS")

            # Convert callouts to Jekyll format
            markdown = convert_callouts(markdown)
            print(f"  ✓ Converted callouts to Jekyll format")

            # Generate front matter
            frontmatter = generate_frontmatter(metadata, cover_image_path)

            # Write post file
            filename = generate_post_filename(metadata)

            if not dry_run:
                filepath = write_post(filename, frontmatter, markdown)
                print(f"  ✓ Created post: {filepath}\n")
            else:
                print(f"  ✓ Would create: _posts/{filename}\n")

        except Exception as e:
            print(f"  ✗ Error processing post: {e}")
            print(f"  Available properties: {list(page['properties'].keys())}\n")
            continue

    print(f"✓ Synced {len(posts)} posts successfully!")

    # Clean up posts that are no longer in Notion
    deleted_count = cleanup_orphaned_posts(notion_post_ids, dry_run)
    
    if deleted_count > 0:
        print(f"\n✓ Cleaned up {deleted_count} orphaned post(s)")

    if not dry_run:
        print("\nNext steps:")
        print("  1. Review the generated posts in _posts/")
        print("  2. Posts are in final Jekyll format - ready to commit")
        print("  3. Test locally with: bash tools/run.sh")

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Sync published posts from Notion to Jekyll',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 tools/sync_notion.py                    # Sync all published posts
  python3 tools/sync_notion.py --dry-run          # Preview without writing files

Environment Variables (from .env file):
  NOTION_API_TOKEN           Your Notion integration token
  NOTION_POSTS_DATABASE_ID   Your Notion database ID
        """
    )
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing files')

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN MODE - No files will be written\n")

    try:
        sync_notion_posts(dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n\nSync cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

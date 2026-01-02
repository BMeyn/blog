#!/usr/bin/env python3

"""
Script to convert Notion callout format to blog post format
Usage: python3 translate.py -i input.md [-o output.md]
"""

import argparse
import sys
import re

def convert_callouts(content):
    """Convert Notion aside blocks to blog prompt format"""
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

        if '⚠️' in content_text in content_text:
            prompt_class = 'prompt-warning'
        elif '✅' in content_text or '🎯' in content_text:
            prompt_class = 'prompt-tip'
        elif '❗' in content_text or '🚫' in content_text:
            prompt_class = 'prompt-danger'
        elif '💡' in content_text or '🔍' in content_text:
            prompt_class = 'prompt-info'

        # Override with class-based mapping if class exists
        if aside_class:
            if 'blue_bg' in aside_class:
                prompt_class = 'prompt-info'
            elif 'yellow_bg' in aside_class:
                prompt_class = 'prompt-warning'
            elif 'green_bg' in aside_class:
                prompt_class = 'prompt-tip'
            elif 'red_bg' in aside_class:
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
            result += '\n\n' + '\n'.join(remaining_lines)
        result += f'\n{{: .{prompt_class} }}'

        return result

    # Apply the replacement with DOTALL flag to match across newlines
    return re.sub(pattern, replace_aside, content, flags=re.DOTALL)

def main():
    parser = argparse.ArgumentParser(
        description='Convert Notion callout format to blog post format'
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input markdown file'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output markdown file (if not specified, input file will be replaced)'
    )

    args = parser.parse_args()

    input_file = args.input
    output_file = args.output if args.output else args.input

    try:
        # Read input file
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Convert callouts
        converted = convert_callouts(content)

        # Write output file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(converted)

        if args.output:
            print(f'Conversion completed: {input_file} -> {output_file}')
        else:
            print(f'File converted in place: {input_file}')

    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

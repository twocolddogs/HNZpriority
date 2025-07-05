#!/usr/bin/env python3
"""
Extract all glyph names from Nerd Fonts for documentation purposes
"""

from fontTools.ttLib import TTFont
import sys
import os

def extract_glyph_names(font_path):
    """Extract all glyph names from a font file"""
    try:
        font = TTFont(font_path)
        
        # Get the character map (cmap)
        cmap = font.getBestCmap()
        
        # Get glyph names
        glyph_names = []
        if hasattr(font, 'getGlyphSet'):
            glyph_set = font.getGlyphSet()
            glyph_names = list(glyph_set.keys())
        
        # Also get mapped character names
        mapped_glyphs = []
        if cmap:
            for unicode_val, glyph_name in cmap.items():
                char = chr(unicode_val)
                mapped_glyphs.append({
                    'unicode': f'U+{unicode_val:04X}',
                    'char': char,
                    'glyph_name': glyph_name
                })
        
        font.close()
        
        return {
            'glyph_names': glyph_names,
            'mapped_glyphs': mapped_glyphs
        }
        
    except Exception as e:
        print(f"Error processing font {font_path}: {e}")
        return None

def main():
    # Find Nerd Font files
    font_paths = [
        "/Users/alrumballsmith/Library/Fonts/SymbolsNerdFont-Regular.ttf"
    ]
    
    # Look for additional Nerd Fonts
    search_paths = [
        os.path.expanduser("~/Library/Fonts"),
        "/System/Library/Fonts",
        "/Library/Fonts"
    ]
    
    for search_path in search_paths:
        if os.path.exists(search_path):
            for filename in os.listdir(search_path):
                if 'nerd' in filename.lower() or 'symbols' in filename.lower():
                    full_path = os.path.join(search_path, filename)
                    if full_path not in font_paths and full_path.endswith('.ttf'):
                        font_paths.append(full_path)
    
    all_icons = {}
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            print(f"Processing {font_path}...")
            result = extract_glyph_names(font_path)
            
            if result:
                font_name = os.path.basename(font_path)
                all_icons[font_name] = result
    
    # Generate markdown output
    markdown_output = []
    markdown_output.append("# Nerd Font Icons Available\n")
    
    for font_name, data in all_icons.items():
        markdown_output.append(f"## {font_name}\n")
        
        # Show some sample mapped glyphs (first 50 to avoid overwhelming)
        if data['mapped_glyphs']:
            markdown_output.append("### Sample Icons")
            markdown_output.append("| Unicode | Character | Glyph Name |")
            markdown_output.append("|---------|-----------|------------|")
            
            # Filter for interesting icons (skip basic ASCII)
            interesting_glyphs = [g for g in data['mapped_glyphs'] 
                                if int(g['unicode'].replace('U+', ''), 16) > 127][:50]
            
            for glyph in interesting_glyphs:
                char_display = glyph['char'] if ord(glyph['char']) > 31 else '(control)'
                markdown_output.append(f"| {glyph['unicode']} | {char_display} | {glyph['glyph_name']} |")
        
        markdown_output.append(f"\n**Total glyphs:** {len(data['glyph_names'])}\n")
    
    return '\n'.join(markdown_output)

if __name__ == "__main__":
    output = main()
    print("\n" + "="*50)
    print("MARKDOWN OUTPUT:")
    print("="*50)
    print(output)
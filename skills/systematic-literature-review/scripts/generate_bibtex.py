#!/usr/bin/env python3
"""
Generate BibTeX file from markdown references section.

Extracts references from a systematic literature review markdown file
and converts them to properly formatted BibTeX entries.

Usage:
    python generate_bibtex.py input.md [output.bib]

The script parses the References section of the markdown file and
generates BibTeX entries with:
- Unique citation keys (firstauthorlastnameyearkeyword format)
- DOI and URL fields
- Standard BibTeX entry types (article, inproceedings, etc.)
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string for safe filename usage.
    - Replace spaces with hyphens
    - Remove unsafe characters: /\\:*?"<>|
    - Limit length to 60 characters
    """
    name = re.sub(r'[\s\u3000]+', '-', name)
    name = re.sub(r'-+', '-', name)
    name = re.sub(r'[\\/:"*?<>|]', '', name)
    name = name.strip('- ')
    if len(name) > 60:
        name = name[:60].strip('-')
    return name


def generate_bibtex_key(
    first_author: str,
    year: str,
    title: str = "",
    max_key_length: int = 40
) -> str:
    """
    Generate a unique BibTeX citation key.

    Format: firstauthorlastnameyear (with optional keyword disambiguation)

    Args:
        first_author: First author's name (e.g., "Cong, L." or "Le Cong")
        year: Publication year (e.g., "2013")
        title: Paper title (for disambiguation if needed)
        max_key_length: Maximum key length

    Returns:
        BibTeX key (e.g., "cong2013multiplexed")
    """
    # Extract last name from first author
    # Handle "Last, First" and "First Last" formats
    if ',' in first_author:
        last_name = first_author.split(',')[0].strip()
    else:
        # Split by spaces and take the last part as last name
        parts = first_author.strip().split()
        last_name = parts[-1] if parts else "author"

    # Remove dots and special characters from last name
    last_name = re.sub(r'[^\w]', '', last_name.lower())

    # Clean year
    year = re.sub(r'[^\d]', '', year)

    # Base key
    base_key = f"{last_name}{year}"

    # If title is provided, add a keyword for disambiguation
    if title and len(base_key) < 20:
        # Extract first meaningful word from title
        title_words = re.findall(r'\b[a-zA-Z]{3,}\b', title)
        if title_words:
            keyword = title_words[0].lower()
            # Avoid common words
            common_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'has', 'have'}
            if keyword not in common_words:
                extended_key = f"{base_key}{keyword}"
                if len(extended_key) <= max_key_length:
                    return extended_key

    return base_key


def parse_markdown_references(md_content: str) -> list[dict]:
    """
    Parse references from markdown References section.

    Supports multiple formats:
    1. Numbered list: "1. Author et al. Year. Title. Journal..."
    2. With links: "[Author et al. Year](url)" or "<sup>[...](url)</sup>"
    3. Indented metadata

    Args:
        md_content: Full markdown file content

    Returns:
        List of reference dicts with keys: author, year, title, journal, etc.
    """
    lines = md_content.split('\n')

    # Find References section
    in_refs = False
    ref_lines = []
    for line in lines:
        if line.strip() == '## References':
            in_refs = True
            continue
        if in_refs:
            if line.strip().startswith('## ') and line.strip() != '## References':
                break
            ref_lines.append(line)

    # Parse each reference
    references = []
    for line in ref_lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Extract link if present: [text](url) or <sup>[text](url)</sup>
        url = None
        link_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line)
        if link_match:
            url = link_match.group(2)

        # Remove markdown links and superscript tags for parsing
        clean_line = re.sub(r'<sup>.*?</sup>', '', line)
        clean_line = re.sub(r'\[[^\]]+\]\([^)]+\)', '', clean_line)
        clean_line = re.sub(r'^\d+\.\s*', '', clean_line)  # Remove numbering
        clean_line = clean_line.strip()

        # Try to parse: Author et al. Year. Title. Journal...
        # Pattern: "Author et al. Year. Title. Journal vol(issue):pages."
        ref = parse_reference_line(clean_line, url)
        if ref:
            references.append(ref)

    return references


def parse_reference_line(line: str, url: Optional[str] = None) -> Optional[dict]:
    """
    Parse a single reference line into structured data.

    Args:
        line: Reference text (e.g., "Cong L, Ran FA, Cox D, et al. Multiplex genome engineering using CRISPR/Cas systems. Science. 2013;339(6121):819-823.")
        url: URL/DOI if present

    Returns:
        Dict with reference metadata or None if parsing fails
    """
    # Full format: "Authors. Title. Journal. Year;Volume(Issue):Pages. doi:..."
    # Example: "Cong L, Ran FA, Cox D, et al. Multiplex genome engineering using CRISPR/Cas systems. Science. 2013;339(6121):819-823. doi:10.1126/science.1231143"

    # Extract DOI first
    doi_match = re.search(r'doi:(10\.\d{4,}/[^\s]+)', line, re.IGNORECASE)
    doi = doi_match.group(1) if doi_match else (url if url and 'doi.org' in url else '')

    # Remove DOI from line for easier parsing
    clean_line = re.sub(r'\s*doi:10\.\d{4,}/[^\s]+', '', line, flags=re.IGNORECASE)

    # Extract year
    year_match = re.search(r'\b(19|20)\d{2}\b', clean_line)
    year = year_match.group(0) if year_match else ""

    if not year:
        return None

    # Split by year
    parts = clean_line.split(year, 1)
    if len(parts) != 2:
        return None

    before_year = parts[0].strip()  # "Authors. Title. Journal."
    after_year = parts[1].strip().lstrip('.;')  # "Volume(Issue):Pages."

    # Parse before_year: "Authors. Title. Journal."
    # Find "et al" to separate authors from the rest
    et_al_pos = before_year.lower().find(' et al')
    if et_al_pos > 0:
        # Find period after "et al"
        period_after_et_al = before_year.find('.', et_al_pos)
        if period_after_et_al > 0:
            authors = before_year[:period_after_et_al].strip()
            rest = before_year[period_after_et_al + 1:].strip()  # "Title. Journal."
        else:
            return None
    else:
        # No "et al", try different approach
        # Assume authors end at first period that's followed by more content
        first_period = before_year.find('. ')
        if first_period > 5:
            authors = before_year[:first_period].strip()
            rest = before_year[first_period + 1:].strip()
        else:
            return None

    # Clean up authors
    authors = re.sub(r'\s+', ' ', authors)

    # Parse rest: "Title. Journal."
    # The journal is the last segment after the final period
    # Example: "Multiplex genome engineering using CRISPR/Cas systems. Science."
    # -> title="Multiplex genome engineering using CRISPR/Cas systems", journal="Science"
    # But note: rest might still have a trailing period from the original format
    # So it's actually "Multiplex genome engineering using CRISPR/Cas systems. Science" (no trailing period)
    # or "Multiplex genome engineering using CRISPR/Cas systems. Science." (with trailing period)

    # Remove trailing period if present
    rest_clean = rest.rstrip('.')

    # Now find the last period to separate title from journal
    last_period = rest_clean.rfind('.')
    if last_period > 10:
        title = rest_clean[:last_period].strip()
        journal = rest_clean[last_period + 1:].strip()
    else:
        # No clear separation, use heuristics
        # If the rest is short, it might just be the title
        if len(rest_clean) < 50:
            title = rest_clean
            journal = ""
        else:
            # Try to find a known journal pattern
            # Common journal names that are short: Science, Nature, Cell, etc.
            words = rest_clean.split()
            if len(words) > 3 and words[-1] in ['Science', 'Nature', 'Cell', 'Lancet', 'JAMA', 'BMJ']:
                journal = words[-1]
                title = ' '.join(words[:-1])
            else:
                title = rest_clean
                journal = ""

    # Parse after_year: "Volume(Issue):Pages."
    volume = ""
    pages = ""

    # Extract volume
    vol_match = re.search(r'^(\d+)\(', after_year)
    if vol_match:
        volume = vol_match.group(1)
    else:
        vol_match = re.search(r'^(\d+)', after_year)
        if vol_match:
            volume = vol_match.group(1)

    # Extract pages
    pages_match = re.search(r':(\d+-\d+)', after_year)
    if pages_match:
        pages = pages_match.group(1)

    # Determine entry type
    entry_type = "article"
    if journal:
        journal_lower = journal.lower()
        if any(x in journal_lower for x in ['conference', 'proc', 'symposium', 'workshop']):
            entry_type = "inproceedings"

    return {
        'author': authors,
        'year': year,
        'title': title,
        'journal': journal,
        'volume': volume,
        'pages': pages,
        'doi': doi,
        'url': url if url and not doi else '',
        'entry_type': entry_type
    }


def reference_to_bibtex(ref: dict, existing_keys: set) -> tuple[str, str]:
    """
    Convert a reference dict to BibTeX format.

    Args:
        ref: Reference dict with author, year, title, etc.
        existing_keys: Set of existing keys to avoid duplicates

    Returns:
        Tuple of (key, bibtex_entry)
    """
    # Generate unique key
    base_key = generate_bibtex_key(
        ref.get('author', '').split()[0] if ref.get('author') else 'author',
        ref.get('year', ''),
        ref.get('title', '')
    )

    # Handle duplicates
    key = base_key
    counter = 1
    while key in existing_keys:
        key = f"{base_key}_{counter}"
        counter += 1

    existing_keys.add(key)

    # Build BibTeX entry
    entry_type = ref.get('entry_type', 'article')

    bibtex = f"@{entry_type}{{{key},\n"
    bibtex += f"  title={{{ref.get('title', '')}}},\n"

    # Format authors
    authors = ref.get('author', '')
    if authors:
        bibtex += f"  author={{{authors}}},\n"

    # Year
    if ref.get('year'):
        bibtex += f"  year={{{ref['year']}}},\n"

    # Journal/Booktitle
    if entry_type == "inproceedings":
        bibtex += f"  booktitle={{{ref.get('journal', '')}}},\n"
    elif ref.get('journal'):
        bibtex += f"  journal={{{ref['journal']}}},\n"

    # Volume
    if ref.get('volume'):
        bibtex += f"  volume={{{ref['volume']}}},\n"

    # Pages
    if ref.get('pages'):
        bibtex += f"  pages={{{ref['pages']}}},\n"

    # DOI
    if ref.get('doi'):
        bibtex += f"  doi={{{ref['doi']}}},\n"

    # URL (if no DOI)
    if ref.get('url') and not ref.get('doi'):
        bibtex += f"  url={{{ref['url']}}},\n"

    # Remove trailing comma and close
    bibtex = bibtex.rstrip(',\n') + "\n}\n"

    return key, bibtex


def generate_bibtex(
    md_file: Path,
    bib_file: Path,
    validate: bool = True
):
    """
    Generate BibTeX file from markdown references.

    Args:
        md_file: Input markdown file
        bib_file: Output BibTeX file
        validate: Whether to validate generated entries
    """
    if not md_file.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_file}")

    # Read markdown content
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Parse references
    references = parse_markdown_references(md_content)

    if not references:
        print("Warning: No references found in markdown file", file=sys.stderr)
        return

    print(f"Found {len(references)} references")

    # Generate BibTeX entries
    existing_keys = set()
    bibtex_entries = []

    for ref in references:
        key, bibtex = reference_to_bibtex(ref, existing_keys)
        bibtex_entries.append((key, bibtex))

    # Write BibTeX file
    with open(bib_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write(f"% BibTeX file generated from {md_file.name}\n")
        f.write(f"% Total entries: {len(bibtex_entries)}\n\n")

        # Write entries (sorted by key)
        for key, bibtex in sorted(bibtex_entries, key=lambda x: x[0]):
            f.write(bibtex)

    print(f"BibTeX file generated: {bib_file}")
    print(f"  Total entries: {len(bibtex_entries)}")

    # Validate if requested
    if validate:
        validate_bibtex(bib_file)


def validate_bibtex(bib_file: Path):
    """
    Basic validation of generated BibTeX file.

    Args:
        bib_file: BibTeX file to validate
    """
    with open(bib_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for balanced braces
    brace_count = content.count('{') - content.count('}')
    if brace_count != 0:
        print(f"  Warning: Unbalanced braces detected ({brace_count})", file=sys.stderr)

    # Check for required fields in @article entries
    articles = re.findall(r'@article\{[^}]+,\n(?:[^}]*?\n)*?\}', content, re.DOTALL)
    for i, article in enumerate(articles[:5]):  # Check first 5
        if not all(field in article for field in ['title=', 'author=', 'year=', 'journal=']):
            print(f"  Warning: Article {i+1} may be missing required fields", file=sys.stderr)

    print("  Validation complete")


def main():
    parser = argparse.ArgumentParser(
        description="Generate BibTeX file from markdown references section",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate BibTeX from review markdown
    python generate_bibtex.py CRISPR_review.md

    # Specify output file
    python generate_bibtex.py review.md references.bib

    # Skip validation
    python generate_bibtex.py review.md --no-validate
        """
    )
    parser.add_argument(
        "markdown_file",
        help="Input markdown file with References section"
    )
    parser.add_argument(
        "output_bib",
        nargs='?',
        help="Output BibTeX file (default: same as input with .bib extension)"
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip validation of generated BibTeX"
    )

    args = parser.parse_args()

    md_path = Path(args.markdown_file).resolve()

    # Default output path
    if args.output_bib:
        bib_path = Path(args.output_bib)
    else:
        bib_path = md_path.with_suffix('.bib')

    try:
        generate_bibtex(
            md_path,
            bib_path,
            validate=not args.no_validate
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

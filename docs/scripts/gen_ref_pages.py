"""Generate the code reference pages.

See: https://mkdocstrings.github.io/recipes/
"""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

for path in sorted(Path("src").rglob("*.py")):
    # Skip test files - they don't need API documentation
    if "tests" in path.parts or path.name.startswith("test_"):
        continue

    module_path = path.relative_to("src").with_suffix("")
    doc_path = path.relative_to("src").with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    parts = list(module_path.parts)

    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    elif parts[-1] == "__main__":
        continue

    nav[parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        identifier = ".".join(parts)

        # Add YAML frontmatter with proper title for browser tab and navigation
        # For __init__.py modules, extract a nice title from parent directory
        if parts and parts[-1] == "__init__":
            title = parts[-2] if len(parts) > 1 else "Reference"
        else:
            title = parts[-1].replace("_", " ").title() if parts else "Reference"

        fd.write(f"---\ntitle: {title}\nsearch:\n  exclude: true\n---\n\n")

        print("::: " + identifier, file=fd)

    mkdocs_gen_files.set_edit_path(full_doc_path, path)

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())

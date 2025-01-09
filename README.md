# path2md

**Version**: 0.4.0  
**Author**: [bitnom](https://github.com/bitnom)  
**License**: Apache License 2.0  

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
  - [Install via uv (Recommended)](#install-via-uv-recommended)
  - [Install via pip](#install-via-pip)
  - [Install via Poetry](#install-via-poetry)
- [Usage](#usage)
  - [Basic Example](#basic-example)
  - [Specifying File Extensions](#specifying-file-extensions)
  - [Omitting Files or Directories](#omitting-files-or-directories)
  - [Truncating Lines or Strings](#truncating-lines-or-strings)
  - [Removing Comments](#removing-comments)
  - [Limiting Recursion Depth](#limiting-recursion-depth)
  - [Whitelisting Files or Directories](#whitelisting-files-or-directories)
  - [Using Gitignore](#using-gitignore)
  - [Output Options](#output-options)
  - [File Size Limit and Binary Files](#file-size-limit-and-binary-files)
- [How It Works](#how-it-works)
- [Known Limitations and Caveats](#known-limitations-and-caveats)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

`path2md` is a command-line tool designed to collect files from a given directory (and its subdirectories) and wrap each file’s content in Markdown code fences. This lets you quickly generate documentation or share your code snippets in a Markdown-friendly format. You can:

- Restrict which files to include (by file extension, whitelists, or `.gitignore`).  
- **Parse all file extensions by default** (unless you explicitly provide `--extensions`).  
- Omit files by extension or filename but still note their presence in the output.  
- Optionally strip comments to reduce clutter.  
- Truncate lines and/or strings to limit overly long content.  
- Limit consecutive empty lines to make the output more compact.  
- **Skip files larger than a specified maximum size** (`--max-size`, default 100 KB).  
- **Always skip binary files** automatically.  
- Produce either a single Markdown file or multiple Markdown files (one per source file).

This tool is especially helpful if you want to share or document multiple files (e.g., sample code, config files) without manually copying and pasting them into code blocks.

---

## Installation

### Install via uv (Recommended)

If you haven’t used **uv** before, it’s a lightweight Python project management tool that helps isolate dependencies. You can install **uv** system-wide with:

```bash
pip install uv
```

Then follow these steps:

1. **Clone** or **download** this repository.
2. In the project directory (where your `pyproject.toml` is located), run:

   ```bash
   uv install
   ```

3. Once installed, you can run:

   ```bash
   uv run path2md --help
   ```

   Or simply:

   ```bash
   uv path2md --help
   ```

   depending on your uv version/configuration.

### Install via pip

1. **Clone** or **download** this repository.
2. From the top-level directory (with the `pyproject.toml`), run:

   ```bash
   pip install .
   ```

   This will build and install the package into your current Python environment.
3. Once installed, you can run:

   ```bash
   path2md --help
   ```

> **Note:** If you want to install in “editable”/dev mode, use:
> ```bash
> pip install -e .
> ```
> Then any local changes to the code reflect immediately.

### Install via Poetry

1. **Clone** or **download** this repository.
2. In the project directory, run:

   ```bash
   poetry install
   ```

3. Once installed, you can:
   - Use it directly via:
     ```bash
     poetry run path2md --help
     ```
   - Or activate the virtual environment (`poetry shell`) and then run:
     ```bash
     path2md --help
     ```

---

## Usage

After installation (via uv, pip, or Poetry), you’ll have a `path2md` CLI command in your PATH. Run:

```bash
path2md <directory> [options]
```

Below is a summary of all the available options:

```txt
positional arguments:
  directory             Directory containing files to process.

optional arguments:
  --output-file OUTPUT_FILE
                        Output markdown file path.
  --output-dir OUTPUT_DIR
                        Output directory for individual markdown files.
  --extensions EXTENSIONS
                        Comma-separated list of file extensions to process.
                        If not provided, ALL file extensions are processed
                        (excluding binary files).
  --omit OMIT
                        Comma-separated list of file extensions to omit
                        (source omitted but file is noted).
  --omit-files OMIT_FILES
                        Comma-separated list of filenames to omit (source
                        omitted but file is noted).
  --omit-dirs OMIT_DIRS
                        Comma-separated list of directory names to omit
                        from traversal entirely.
  --truncln TRUNCLN
                        Truncate lines longer than this many characters.
  --truncstr TRUNCSTR
                        Truncate strings longer than this many characters.
  --nocom
                        Omit all line/block comments from the output.
  --maxlnspace MAXLNSPACE
                        Maximum number of consecutive empty lines allowed.
  --depth DEPTH
                        Limit directory recursion depth.
  --whitelist-files WHITELIST_FILES
                        Comma-separated list of files to parse.
  --whitelist-dirs WHITELIST_DIRS
                        Comma-separated list of directory names to traverse.
  --whitelist WHITELIST
                        Comma-separated list of files/dirs to process.
  --gitignore GITIGNORE
                        Path to a .gitignore file (global).
  --obey-gitignores
                        Obey .gitignore files found in traversed directories.
  --max-size MAX_SIZE
                        Maximum file size in bytes to process (default: 100 KB).
  --version
                        Show program's version number and exit.
```

### Basic Example

```bash
path2md my_project --output-file project_snippets.md
```

- Traverses `my_project/` looking for **all file extensions** by default (skipping binary files and those over 100 KB).  
- Outputs all discovered (non-binary) files into a single Markdown file named `project_snippets.md`.

### Specifying File Extensions

To only include certain extensions:

```bash
path2md my_project --extensions py,js,json
```

This processes **only** `.py`, `.js`, and `.json` files (still skipping binary files and those over 100 KB).

### Omitting Files or Directories

You can omit files by extension or by exact filename:

```bash
# Omit .env and .lock files, but still note them in the output
path2md my_project --omit env,lock
```

To **completely skip** a directory, use `--omit-dirs`:

```bash
path2md my_project --omit-dirs node_modules,build
```

Any directory named `node_modules` or `build` will not be entered during traversal.

### Truncating Lines or Strings

- `--truncln` truncates individual lines if they exceed a certain length.
- `--truncstr` truncates string literals (e.g., `"..."`, `'...'`, triple quotes, backticks).

Example:

```bash
path2md my_project --truncln 120 --truncstr 200
```

Lines over 120 characters will be shortened, and string literals over 200 characters will be truncated.

### Removing Comments

Use `--nocom` to strip out comments:

```bash
path2md my_project --nocom
```

Currently, this removes:
- `# ...` lines in Python.
- `// ...` lines and `/* ... */` blocks in JS/TS/CSS/HTML.

It is a naive removal (simple regex-based) and won’t handle advanced edge cases (like `#` in a string).

### Limiting Recursion Depth

If you only want to scan subdirectories up to a certain depth from the initial directory:

```bash
path2md my_project --depth 2
```

- `depth=0` means only the directory itself.  
- `depth=1` means the directory and its immediate subdirectories.  

### Whitelisting Files or Directories

If you only want to process specific files or directories:

```bash
path2md my_project --whitelist-files main.py,settings.py
```

This will only process `main.py` and `settings.py` (within the given directory). Similarly, `--whitelist-dirs` only traverses directories whose names match the whitelist. The more general `--whitelist` applies to both file and directory names.

### Using Gitignore

You can specify a global `.gitignore` to skip certain files:

```bash
path2md my_project --gitignore /path/to/.gitignore
```

Or, if you want the script to obey any `.gitignore` found inside subdirectories:

```bash
path2md my_project --obey-gitignores
```

This means each subdirectory’s `.gitignore` rules are also applied.

### Output Options

1. **Output to a single Markdown file**:

   ```bash
   path2md my_project --output-file output.md
   ```

2. **Output to multiple Markdown files (one per source file)**:

   ```bash
   path2md my_project --output-dir output_folder
   ```

   This creates `output_folder/` if it doesn’t exist, then places individual `.md` files for each source file. The filenames are based on the relative paths of the source files but sanitized for filesystem safety.

3. **Output to STDOUT** (default if neither `--output-file` nor `--output-dir` is specified):

   ```bash
   path2md my_project
   ```

### File Size Limit and Binary Files

- By default, files larger than **100 KB** are skipped. You can customize this limit with `--max-size <BYTES>`.
- The script **always skips binary files**. Any file containing a null byte (`\0`) in the first 1024 bytes is treated as binary, and it won’t be included in the output.

---

## How It Works

1. **Argument Parsing**  
   The script reads all CLI options and determines which files/directories to traverse or skip.

2. **File Collection**  
   - Uses `os.walk()` to scan the specified directory.  
   - Checks optional recursion depth, directory whitelists/omits, `.gitignore` rules, and maximum file size to filter out unwanted paths.  
   - Automatically **skips binary files**.  
   - By default, if `--extensions` is **not** provided, **all** non-binary files under the `max-size` limit are processed.

3. **Fencing Content**  
   For each file that passes the filters:
   - If its extension or filename is in the “omit” lists, it’s only *referenced* (with a note that content is omitted).  
   - Otherwise, the script reads the file content, optionally removes comments, truncates lines/strings, and limits consecutive empty lines.  
   - Wraps the processed text in Markdown fences.

4. **Output**  
   - All fenced content is joined into a single string or separated into multiple Markdown files as requested.  
   - If splitting into multiple files, the script uses a simple split logic on the combined string and writes each chunk to an individual `.md` file.

---

## Known Limitations and Caveats

1. **Naive Regex for Comments and Strings**  
   - The regex approach may remove content that merely *resembles* a comment (e.g., `//` in a string).  
   - Similarly, string truncation might behave unexpectedly with nested quotes or escaped characters.

2. **Splitting Output in `--output-dir` Mode**  
   - The script splits combined content on `\n**`, which might conflict if your files legitimately contain that exact sequence in code. This is unlikely but worth noting.  

3. **Overwriting Files**  
   - If two different source files sanitize to the same name, the second will overwrite the first in the output directory. (For example, `foo/bar.py` and `foo:bar.py` both becoming `foo_bar_py.md`.)

4. **Case Sensitivity**  
   - On some filesystems (e.g., Windows), filename case might cause collisions in `--output-dir` mode.

If these caveats don’t affect your typical use, the script should work fine.

---

## Contributing

Contributions, bug reports, and feature requests are welcome. Please open an issue or submit a pull request on the [GitHub repository](https://github.com/bitnom/path2md) (or wherever the project is hosted).

When submitting code changes, please ensure you:

1. Write clear commit messages.  
2. Include testing or sample usage if you introduce new features.  
3. Adhere to Pythonic style (PEP 8).

---

## License

This project is under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0). Feel free to modify or distribute under the terms of that license, or use a different license if you prefer.
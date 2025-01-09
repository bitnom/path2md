#!/home/zensin/.pyenv/shims/python3

import argparse
import os
import re
from gitignore_parser import parse_gitignore
from pathlib import Path

__version__ = "0.4.0"


def parse_arguments():
    parser = argparse.ArgumentParser(description="Wrap file contents in markdown code fences.")
    parser.add_argument("directory", type=str, help="Directory containing files to process.")

    # Mutually exclusive group for output-file vs. output-dir
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--output-file",
        type=str,
        help="Output markdown file path. If not provided, output will be printed to console."
    )
    output_group.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for individual markdown files."
    )

    # By default, parse all extensions unless --extensions is specified
    parser.add_argument(
        "--extensions",
        type=lambda s: s.split(','),
        default=None,
        help=(
            "Comma-separated list of file extensions to process. "
            "By default, all file extensions are processed unless this is provided."
        ),
    )

    parser.add_argument(
        "--omit",
        type=lambda s: s.split(','),
        default=[],
        help="Comma-separated list of file extensions to omit but still reference in the output."
    )
    parser.add_argument(
        "--omit-files",
        type=lambda s: s.split(','),
        default=[],
        help="Comma-separated list of filenames to omit but still reference in the output."
    )
    parser.add_argument(
        "--omit-dirs",
        type=lambda s: s.split(','),
        default=[],
        help="Comma-separated list of directory names to omit from traversal."
    )
    parser.add_argument(
        "--truncln",
        type=int,
        default=None,
        help="Truncate lines longer than this number of characters. Default: None"
    )
    parser.add_argument(
        "--truncstr",
        type=int,
        default=None,
        help="Truncate strings longer than this number of characters. Default: None"
    )
    parser.add_argument(
        "--nocom",
        action='store_true',
        help="Omit all line and block comments from the output."
    )
    parser.add_argument(
        "--maxlnspace",
        type=int,
        default=None,
        help="Maximum number of consecutive empty lines allowed in the output. Default: None"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=None,
        help="Limit the directory recursion depth. Default: None"
    )
    parser.add_argument(
        "--whitelist-files",
        type=lambda s: s.split(','),
        default=[],
        help=(
            "Comma-separated list of files to parse. If specified, only these files will be parsed."
        ),
    )
    parser.add_argument(
        "--whitelist-dirs",
        type=lambda s: s.split(','),
        default=[],
        help=(
            "Comma-separated list of directory names to traverse. "
            "If specified, only these directories will be traversed."
        ),
    )
    parser.add_argument(
        "--whitelist",
        type=lambda s: s.split(','),
        default=[],
        help=(
            "Comma-separated list of directory names and/or file names to traverse/parse. "
            "If specified, only these will be processed."
        ),
    )
    parser.add_argument(
        "--gitignore",
        type=str,
        default=None,
        help="Path to .gitignore file. If provided, files and directories matching the gitignore patterns will be skipped."
    )
    parser.add_argument(
        "--obey-gitignores",
        action='store_true',
        help="Obey .gitignore files found in traversed directories."
    )

    # New option: skip files larger than max-size (default: 100 KB)
    parser.add_argument(
        "--max-size",
        type=int,
        default=100 * 1024,  # 100 KB
        help="Maximum file size in bytes to process. Default: 100 KB"
    )

    # Version argument
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    return parser.parse_args()


def load_gitignore(directory):
    """
    Load and return a gitignore matcher for the given directory,
    if a .gitignore file is found there.
    """
    gitignore_path = os.path.join(directory, '.gitignore')
    if os.path.exists(gitignore_path):
        return parse_gitignore(gitignore_path)
    return None


def is_binary_file(file_path, block_size=1024):
    """
    Read the first `block_size` bytes of the file in binary mode.
    If it contains a null byte, treat as binary.
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(block_size)
        return b'\0' in chunk
    except Exception:
        # If we can't read the file, skip it safely
        return True


def list_files(
    directory,
    extensions,
    max_depth=None,
    omit_dirs=None,
    whitelist_files=None,
    whitelist_dirs=None,
    whitelist=None,
    global_gitignore_matcher=None,
    obey_gitignores=False,
    max_size=100*1024
):
    """
    Traverse the directory tree and return a list of file paths that match
    the provided conditions, while obeying whitelists, omit lists, file size,
    binary-file checks, and gitignores.
    """
    if omit_dirs is None:
        omit_dirs = []
    if whitelist_files is None:
        whitelist_files = []
    if whitelist_dirs is None:
        whitelist_dirs = []
    if whitelist is None:
        whitelist = []

    file_list = []
    start_depth = directory.count(os.sep)

    # Start a stack for .gitignore matchers. If a global gitignore was provided, push it.
    gitignore_stack = []
    if global_gitignore_matcher:
        gitignore_stack.append(global_gitignore_matcher)

    for root, dirs, files in os.walk(directory):
        current_depth = root.count(os.sep) - start_depth
        if max_depth is not None and current_depth >= max_depth:
            # Do not walk deeper
            dirs[:] = []
            continue

        # Remember how many matchers are on the stack before checking local .gitignore
        stack_len_before = len(gitignore_stack)

        if obey_gitignores:
            # Load the local .gitignore for the current directory
            local_gitignore = load_gitignore(root)
            if local_gitignore:
                gitignore_stack.append(local_gitignore)

        # The "active" ignore is the top of the stack (if any)
        current_gitignore = gitignore_stack[-1] if gitignore_stack else None

        # Handle whitelisted vs omitted directories
        if whitelist_dirs:
            dirs[:] = [d for d in dirs if d in whitelist_dirs]
        elif whitelist:
            # If a general whitelist is provided (files + dirs), skip directories not in it
            dirs[:] = [d for d in dirs if d in whitelist]
        else:
            # Omit directories explicitly listed
            dirs[:] = [d for d in dirs if d not in omit_dirs]

        # If there's a gitignore, filter out directories it matches
        if current_gitignore:
            dirs[:] = [d for d in dirs if not current_gitignore(os.path.join(root, d))]

        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, directory)

            # Check whitelist files
            if whitelist_files and file not in whitelist_files:
                continue
            # Or a general whitelist
            if whitelist and (relative_path not in whitelist and file not in whitelist):
                continue
            # Check gitignore
            if current_gitignore and current_gitignore(file_path):
                continue
            # Skip if file is too large
            if os.path.getsize(file_path) > max_size:
                continue
            # Skip binary files
            if is_binary_file(file_path):
                continue

            # If --extensions was provided, check extension
            if extensions is not None:
                if os.path.splitext(file)[1][1:] in extensions:
                    file_list.append(file_path)
            else:
                # By default (extensions=None), parse everything (non-binary, size OK, not ignored)
                file_list.append(file_path)

        # After processing the current directory, pop any local .gitignore we added
        if obey_gitignores:
            while len(gitignore_stack) > stack_len_before:
                gitignore_stack.pop()

    return file_list


def remove_comments(content, extension):
    """
    REMAIN UNCHANGED (per your request):
    Naive removal of # lines in Python or // and /* */ in JS/TS/CSS/HTML.
    """
    if extension in ['py']:
        content = re.sub(r'#.*', '', content)
    elif extension in ['js', 'ts', 'mjs', 'tsx', 'css', 'html']:
        content = re.sub(r'//.*', '', content)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    return content


def truncate_strings(content, truncstr):
    string_patterns = [
        r'\'[^\']*\'',
        r'\"[^\"]*\"',
        r'\'\'\'(.*?)\'\'\'',
        r'\"\"\"(.*?)\"\"\"',
        r'\`[^\`]*\`'
    ]

    def truncate_match(match):
        string = match.group(0)
        if len(string) > truncstr:
            if string.startswith("'''") or string.startswith('"""'):
                return string[:truncstr] + '... (String truncated) ' + string[:3]
            else:
                return string[:truncstr] + '... (String truncated)' + string[-1]
        return string

    for pattern in string_patterns:
        content = re.sub(pattern, truncate_match, content, flags=re.DOTALL)
    return content


def truncate_line(line, truncln):
    if len(line) <= truncln:
        return line
    if line[truncln - 1] in ['\'', '\"', '`']:
        return line[:truncln] + " // (Line truncated to save space)"
    return line[:truncln] + " // (Line truncated to save space)" + line[-1]


def limit_consecutive_empty_lines(content, maxlnspace):
    if maxlnspace is None:
        return content
    lines = content.splitlines()
    new_lines = []
    empty_line_count = 0
    for line in lines:
        if line.strip() == "":
            empty_line_count += 1
        else:
            empty_line_count = 0
        if empty_line_count <= maxlnspace:
            new_lines.append(line)
    return "\n".join(new_lines)


def read_and_fence(file_path, base_directory, omit_extensions, omit_files, truncln, truncstr, nocom, maxlnspace):
    extension = os.path.splitext(file_path)[1][1:]
    relative_path = os.path.relpath(file_path, base_directory)
    filename = os.path.basename(file_path)

    # If extension or file is in omit list, only note it, don’t print code
    if extension in omit_extensions or filename in omit_files:
        return f"**{relative_path}** (Source omitted to save space)\n"

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        if nocom:
            content = remove_comments(content, extension)

        if truncstr:
            content = truncate_strings(content, truncstr)

        if truncln:
            content = '\n'.join(truncate_line(line, truncln) for line in content.splitlines())

        if maxlnspace is not None:
            content = limit_consecutive_empty_lines(content, maxlnspace)

        return f"**{relative_path}**\n```{extension}\n{content}\n```\n"
    except Exception as e:
        return f"**{relative_path}** (Error reading file: {e})\n"


def concatenate_markdown(files, base_directory, omit_extensions, omit_files, truncln, truncstr, nocom, maxlnspace):
    """
    Read and fence all files in the list, then concatenate into a single string.
    """
    return "\n".join(
        read_and_fence(
            file,
            base_directory,
            omit_extensions,
            omit_files,
            truncln,
            truncstr,
            nocom,
            maxlnspace
        )
        for file in files
    )


def sanitize_filename(filename):
    """
    Replaces characters that are invalid on common filesystems.
    """
    return re.sub(r'[<>:"/\\|?*]', '_', str(filename))


def write_to_file(content, output_file, output_dir):
    """
    Write 'content' to a single file if output_file is specified;
    write each file's fenced content separately if output_dir is specified;
    otherwise print to stdout.
    """
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Each file's content starts with "**{relative_path}**"
        # So we split on '\n**' to chunk them.
        chunks = content.split('\n**')
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            # Attempt to split the leading file path from the rest
            try:
                file_path, file_body = chunk.split('**\n', 1)
            except ValueError:
                # If there's no '**\n', skip
                continue
            file_path = file_path.strip()
            sanitized_path = sanitize_filename(file_path)
            # Each chunk goes to its own .md
            out_file = output_path / f"{sanitized_path}.md"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with out_file.open('w', encoding='utf-8') as f:
                f.write(f"**{file_path}**\n{file_body}")

    elif output_file:
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(content)
    else:
        print(content)


def main():
    args = parse_arguments()

    # Load a global gitignore if specified
    global_gitignore_matcher = None
    if args.gitignore:
        global_gitignore_matcher = parse_gitignore(args.gitignore)

    abs_directory = os.path.abspath(args.directory)

    files = list_files(
        abs_directory,
        args.extensions,
        args.depth,
        args.omit_dirs,
        args.whitelist_files,
        args.whitelist_dirs,
        args.whitelist,
        global_gitignore_matcher,
        args.obey_gitignores,
        max_size=args.max_size
    )

    markdown_content = concatenate_markdown(
        files,
        abs_directory,
        args.omit,
        args.omit_files,
        args.truncln,
        args.truncstr,
        args.nocom,
        args.maxlnspace
    )

    write_to_file(markdown_content, args.output_file, args.output_dir)


if __name__ == "__main__":
    main()

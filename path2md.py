# path2md.py

import argparse
import os
import re
import sys
from gitignore_parser import parse_gitignore

__version__ = "0.2.2"

def parse_arguments():
    parser = argparse.ArgumentParser(description="Wrap file contents in markdown code fences.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input-directory", type=str, help="Directory containing files to process.")
    input_group.add_argument("--input-paths-file", type=str, help="Path to a file containing a list of paths to process.")
    parser.add_argument("--output-file", type=str, help="Output markdown file path. If not provided, output will be printed to console.")
    parser.add_argument("--extensions", type=lambda s: s.split(','), default="py,ts,js,mjs,toml,json,tsx,css,html",
                        help="Comma-separated list of file extensions to process. Default: py,ts,js,mjs,toml,json,tsx,css,html")
    parser.add_argument("--omit", type=lambda s: s.split(','), default="",
                        help="Comma-separated list of file extensions to omit but still reference in the output.")
    parser.add_argument("--omit-files", type=lambda s: s.split(','), default="",
                        help="Comma-separated list of filenames to omit but still reference in the output.")
    parser.add_argument("--omit-dirs", type=lambda s: s.split(','), default="",
                        help="Comma-separated list of directory names to omit from traversal.")
    parser.add_argument("--truncln", type=int, default=None,
                        help="Truncate lines longer than this number of characters. Default: None")
    parser.add_argument("--truncstr", type=int, default=None,
                        help="Truncate strings longer than this number of characters. Default: None")
    parser.add_argument("--nocom", action='store_true',
                        help="Omit all line and block comments from the output.")
    parser.add_argument("--maxlnspace", type=int, default=None,
                        help="Maximum number of consecutive empty lines allowed in the output. Default: None")
    parser.add_argument("--depth", type=int, default=None,
                        help="Limit the directory recursion depth. Default: None")
    parser.add_argument("--whitelist-files", type=lambda s: s.split(','), default=None,
                        help="Comma-separated list of files to parse. If specified, only these files will be parsed.")
    parser.add_argument("--whitelist-dirs", type=lambda s: s.split(','), default=None,
                        help="Comma-separated list of directory names to traverse. If specified, only these directories will be traversed.")
    parser.add_argument("--whitelist", type=lambda s: s.split(','), default=None,
                        help="Comma-separated list of directory names and/or file names to traverse and/or parse. If specified, only these will be processed.")
    parser.add_argument("--gitignore", type=str, default=None,
                        help="Path to .gitignore file. If provided, files and directories matching the gitignore patterns will be skipped.")
    parser.add_argument("--obey-gitignores", action='store_true',
                        help="Obey .gitignore files found in traversed directories.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args()

def load_gitignore(directory):
    gitignore_path = os.path.join(directory, '.gitignore')
    if os.path.exists(gitignore_path):
        return parse_gitignore(gitignore_path)
    return None

def list_files(directory, extensions, max_depth=None, omit_dirs=[], whitelist_files=None, whitelist_dirs=None, whitelist=None, global_gitignore_matcher=None, obey_gitignores=False):
    file_list = []
    start_depth = directory.count(os.sep)
    gitignore_stack = [global_gitignore_matcher] if global_gitignore_matcher else []

    for root, dirs, files in os.walk(directory):
        current_depth = root.count(os.sep) - start_depth
        if max_depth is not None and current_depth >= max_depth:
            dirs[:] = []
            continue

        if obey_gitignores:
            local_gitignore = load_gitignore(root)
            if local_gitignore:
                gitignore_stack.append(local_gitignore)
            elif gitignore_stack:
                parent_dir = os.path.dirname(root)
                if os.path.exists(os.path.join(parent_dir, '.gitignore')):
                    gitignore_stack.pop()

        current_gitignore = gitignore_stack[-1] if gitignore_stack else None

        if whitelist_dirs:
            dirs[:] = [d for d in dirs if d in whitelist_dirs]
        elif whitelist:
            dirs[:] = [d for d in dirs if d in whitelist]
        else:
            dirs[:] = [d for d in dirs if d not in omit_dirs]

        if current_gitignore:
            dirs[:] = [d for d in dirs if not current_gitignore(os.path.join(root, d))]

        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, directory)

            if whitelist_files and file not in whitelist_files:
                continue
            if whitelist and relative_path not in whitelist and file not in whitelist:
                continue

            if current_gitignore and current_gitignore(file_path):
                continue

            if os.path.splitext(file)[1][1:] in extensions:
                file_list.append(file_path)

    return file_list

def remove_comments(content, extension):
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
    if line[truncln-1] in ['\'', '\"', '`']:
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
    if extension in omit_extensions or filename in omit_files:
        return f"**{relative_path}** (Source omitted to save space)\n"
    try:
        with open(file_path, 'r') as file:
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
    return "\n".join(read_and_fence(file, base_directory, omit_extensions, omit_files, truncln, truncstr, nocom, maxlnspace) for file in files)

def write_to_file(content, output_file):
    if output_file:
        with open(output_file, 'w') as file:
            file.write(content)
    else:
        print(content)

def read_input_paths(input_paths_file):
    with open(input_paths_file, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def main():
    args = parse_arguments()

    global_gitignore_matcher = None
    if args.gitignore:
        global_gitignore_matcher = parse_gitignore(args.gitignore)

    if args.input_directory:
        abs_directory = os.path.abspath(args.input_directory)
        files = list_files(abs_directory, args.extensions, args.depth, args.omit_dirs,
                           args.whitelist_files, args.whitelist_dirs, args.whitelist,
                           global_gitignore_matcher, args.obey_gitignores)
    elif args.input_paths_file:
        input_paths = read_input_paths(args.input_paths_file)
        files = []
        for path in input_paths:
            abs_path = os.path.abspath(path)
            if os.path.isdir(abs_path):
                files.extend(list_files(abs_path, args.extensions, args.depth, args.omit_dirs,
                                        args.whitelist_files, args.whitelist_dirs, args.whitelist,
                                        global_gitignore_matcher, args.obey_gitignores))
            elif os.path.isfile(abs_path):
                files.append(abs_path)

    base_directory = os.path.commonpath(files) if files else ""
    markdown_content = concatenate_markdown(files, base_directory, args.omit, args.omit_files,
                                            args.truncln, args.truncstr, args.nocom, args.maxlnspace)
    write_to_file(markdown_content, args.output_file)

if __name__ == "__main__":
    main()

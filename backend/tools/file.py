import os


def read_file(path: str) -> str:
    """Read contents of a file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Successfully wrote to {path}"

def edit_file(path: str, old_string: str, new_string: str) -> str:
    """Replace exactly old_string with new_string in a file."""
    content = read_file(path)
    if old_string not in content:
        raise ValueError("String not found in file")
    new_content = content.replace(old_string, new_string)
    write_file(path, new_content)
    return f"Successfully edited {path}"

def list_directory(path: str) -> str:
    """List contents of a directory."""
    files = os.listdir(path)
    return "\n".join(files)

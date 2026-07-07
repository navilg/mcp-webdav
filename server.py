from fastmcp import FastMCP
import os
import argparse
import requests
from urllib.parse import urlparse, urlunparse

mcp = FastMCP(name="WebDAV MCP")


def _get_webdav_base() -> str:
    """Get the base WebDAV URL from environment."""
    url = os.getenv("WEBDAV_URL")
    if not url:
        raise ValueError("WEBDAV_URL environment variable is not set")
    return url.rstrip("/")


def _get_auth() -> tuple | None:
    """Get authentication tuple from environment if configured."""
    username = os.getenv("WEBDAV_USERNAME")
    password = os.getenv("WEBDAV_PASSWORD")
    if username and password:
        return (username, password)
    return None


def _build_full_url(path: str) -> str:
    """Build a full WebDAV URL from a path."""
    base = _get_webdav_base()
    # Ensure path starts with /
    clean_path = path.strip()
    if clean_path and not clean_path.startswith("/"):
        clean_path = "/" + clean_path
    return f"{base}{clean_path}" if clean_path else base


def _make_request(method: str, url: str, **kwargs) -> requests.Response:
    """Make an HTTP request with authentication to the WebDAV server."""
    auth = _get_auth()
    headers = kwargs.pop("headers", {})
    timeout = kwargs.pop("timeout", 30)
    try:
        response = requests.request(
            method, url, auth=auth, headers=headers, timeout=timeout, **kwargs
        )
        return response
    except requests.RequestException as exc:
        raise RuntimeError(f"WebDAV request failed: {exc}")


@mcp.tool
def list_files(path: str = "/") -> str:
    """
    List files and directories at the specified path on the WebDAV server.

    Args:
        path: Directory path to list (default: "/")

    Returns:
        A tab-separated table of entries with name, type, size, and last modified date.
    """
    url = _build_full_url(path)
    if not url.endswith("/"):
        url += "/"

    body = """<?xml version="1.0" encoding="utf-8"?>
<propfind xmlns="DAV:">
  <prop>
    <displayname/>
    <resourcetype/>
    <getcontentlength/>
    <getlastmodified/>
  </prop>
</propfind>"""

    headers = {
        "Depth": "1",
        "Content-Type": "application/xml",
    }

    try:
        response = _make_request("PROPFIND", url, data=body, headers=headers)
    except RuntimeError as exc:
        return f"Error: {exc}"

    if response.status_code in (401, 403):
        return f"Error: Authentication failed. Check WEBDAV_USERNAME and WEBDAV_PASSWORD."
    if response.status_code == 404:
        return f"Error: Path '{path}' not found on WebDAV server."
    if response.status_code not in (207, 200):
        return f"Error: Failed to list directory (HTTP {response.status_code})."

    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        return f"Error: Failed to parse server response: {exc}"

    # Namespace map
    ns = {"d": "DAV:"}

    entries = []
    for resp_elem in root.findall("d:response", ns):
        href = resp_elem.find("d:href", ns)
        href_text = href.text.strip() if href is not None else ""

        propstat = resp_elem.find("d:propstat", ns)
        if propstat is None:
            continue
        prop = propstat.find("d:prop", ns)
        if prop is None:
            continue

        displayname = prop.find("d:displayname", ns)
        name = displayname.text.strip() if displayname is not None and displayname.text else href_text.rstrip("/").split("/")[-1]

        resourcetype = prop.find("d:resourcetype", ns)
        is_dir = False
        if resourcetype is not None:
            if resourcetype.find("d:collection", ns) is not None:
                is_dir = True

        content_length = prop.find("d:getcontentlength", ns)
        size = content_length.text if content_length is not None and content_length.text else "-"

        last_modified = prop.find("d:getlastmodified", ns)
        modified = last_modified.text if last_modified is not None and last_modified.text else "-"

        # Skip the current directory listing (href == base url)
        parsed_base = urlparse(url)
        parsed_href = urlparse(href_text)
        if parsed_href.path.rstrip("/") == parsed_base.path.rstrip("/"):
            continue

        entries.append({
            "name": name,
            "type": "directory" if is_dir else "file",
            "size": size,
            "last_modified": modified,
        })

    if not entries:
        return f"Directory '{path}' is empty."

    # Format as TSV
    headers_list = ["name", "type", "size", "last_modified"]
    lines = ["\t".join(headers_list)]
    for entry in entries:
        lines.append("\t".join(str(entry.get(h, "")) for h in headers_list))

    return "\n".join(lines)


@mcp.tool
def read_file(path: str) -> str:
    """
    Read the contents of a file from the WebDAV server.

    Args:
        path: Path to the file on the WebDAV server

    Returns:
        The file content as a string.
    """
    url = _build_full_url(path)

    try:
        response = _make_request("GET", url)
    except RuntimeError as exc:
        return f"Error: {exc}"

    if response.status_code in (401, 403):
        return f"Error: Authentication failed. Check WEBDAV_USERNAME and WEBDAV_PASSWORD."
    if response.status_code == 404:
        return f"Error: File '{path}' not found on WebDAV server."
    if response.status_code != 200:
        return f"Error: Failed to read file (HTTP {response.status_code})."

    return response.text


@mcp.tool
def create_directory(path: str) -> str:
    """
    Create a new directory on the WebDAV server.

    If a directory with the same name already exists, no error is returned.

    Args:
        path: Path of the directory to create

    Returns:
        A message with the URL to access the directory.
    """
    url = _build_full_url(path)
    if not url.endswith("/"):
        url += "/"

    try:
        response = _make_request("MKCOL", url)
    except RuntimeError as exc:
        return f"Error: {exc}"

    if response.status_code == 405:
        return f"Directory '{path}' already exists. URL: {url}"
    if response.status_code in (401, 403):
        return f"Error: Authentication failed. Check WEBDAV_USERNAME and WEBDAV_PASSWORD."
    if response.status_code == 409:
        return f"Error: Parent directory does not exist for '{path}'."
    if response.status_code not in (201, 200):
        return f"Error: Failed to create directory (HTTP {response.status_code})."

    return f"Directory created successfully. URL: {url}"


@mcp.tool
def upload_file(path: str, content: str) -> str:
    """
    Upload a new file to the WebDAV server.

    Args:
        path: Full path including filename where the file should be uploaded
        content: Text content of the file

    Returns:
        A message with the URL to access the uploaded file.
    """
    url = _build_full_url(path)

    headers = {
        "Content-Type": "application/octet-stream",
    }

    try:
        response = _make_request("PUT", url, data=content.encode("utf-8"), headers=headers)
    except RuntimeError as exc:
        return f"Error: {exc}"

    if response.status_code in (401, 403):
        return f"Error: Authentication failed. Check WEBDAV_USERNAME and WEBDAV_PASSWORD."
    if response.status_code == 409:
        return f"Error: Parent directory does not exist for '{path}'."
    if response.status_code not in (201, 200, 204):
        return f"Error: Failed to upload file (HTTP {response.status_code})."

    return f"File uploaded successfully. URL: {url}"


@mcp.tool
def update_file(path: str, content: str) -> str:
    """
    Update an existing file on the WebDAV server by overwriting its content.

    Args:
        path: Full path to the existing file
        content: New text content for the file

    Returns:
        A message with the URL to access the updated file.
    """
    # First check if the file exists
    url = _build_full_url(path)

    try:
        check_response = _make_request("GET", url)
    except RuntimeError:
        # Proceed anyway; PUT will create if not exists
        check_response = None

    if check_response is not None and check_response.status_code == 404:
        return f"Error: File '{path}' does not exist. Use upload_file to create a new file."

    headers = {
        "Content-Type": "application/octet-stream",
    }

    try:
        response = _make_request("PUT", url, data=content.encode("utf-8"), headers=headers)
    except RuntimeError as exc:
        return f"Error: {exc}"

    if response.status_code in (401, 403):
        return f"Error: Authentication failed. Check WEBDAV_USERNAME and WEBDAV_PASSWORD."
    if response.status_code not in (200, 201, 204):
        return f"Error: Failed to update file (HTTP {response.status_code})."

    return f"File updated successfully. URL: {url}"


@mcp.tool
def delete_file(path: str) -> str:
    """
    Delete an existing file from the WebDAV server.

    Args:
        path: Full path to the file to delete

    Returns:
        A confirmation message.
    """
    url = _build_full_url(path)

    try:
        response = _make_request("DELETE", url)
    except RuntimeError as exc:
        return f"Error: {exc}"

    if response.status_code in (401, 403):
        return f"Error: Authentication failed. Check WEBDAV_USERNAME and WEBDAV_PASSWORD."
    if response.status_code == 404:
        return f"Error: File '{path}' not found on WebDAV server."
    if response.status_code not in (200, 201, 204):
        return f"Error: Failed to delete file (HTTP {response.status_code})."

    return f"File deleted successfully: {path}"


@mcp.tool
def delete_directory(path: str) -> str:
    """
    Delete an existing directory from the WebDAV server.

    The directory must be empty before deletion.

    Args:
        path: Path of the directory to delete

    Returns:
        A confirmation message.
    """
    url = _build_full_url(path)
    if not url.endswith("/"):
        url += "/"

    try:
        response = _make_request("DELETE", url)
    except RuntimeError as exc:
        return f"Error: {exc}"

    if response.status_code in (401, 403):
        return f"Error: Authentication failed. Check WEBDAV_USERNAME and WEBDAV_PASSWORD."
    if response.status_code == 404:
        return f"Error: Directory '{path}' not found on WebDAV server."
    if response.status_code == 405:
        return f"Error: '{path}' is not a directory or is not empty. Delete files first."
    if response.status_code not in (200, 201, 204):
        return f"Error: Failed to delete directory (HTTP {response.status_code})."

    return f"Directory deleted successfully: {path}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the WebDAV MCP server.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--transport", type=str, default="streamable-http", help="Transport protocol to use (default: streamable-http)")
    args = parser.parse_args()

    mcp.run(transport=args.transport, host=args.host, port=args.port)

# MCP WebDAV

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides CRUD operations on a WebDAV server using the `streamable-http` transport.

Built with [FastMCP](https://github.com/jlowin/fastmcp).

## Tools

| Tool | Description |
|------|-------------|
| `list_files(path)` | List files and directories at the specified path |
| `read_file(path)` | Read the contents of a file |
| `create_directory(path)` | Create a new directory (no-op if it already exists) |
| `upload_file(path, content)` | Upload a new file to a directory |
| `update_file(path, content)` | Update/overwrite an existing file |
| `delete_file(path)` | Delete an existing file |
| `delete_directory(path)` | Delete an existing directory |

## Prerequisites

- Python 3.11+ (for local run) or Docker (for container run)
- A WebDAV server (e.g., [Nextcloud](https://nextcloud.com/), [ownCloud](https://owncloud.com/), [Apache HTTP Server with mod_dav](https://httpd.apache.org/docs/2.4/mod/mod_dav.html))

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WEBDAV_URL` | Yes | Base URL of the WebDAV server (e.g., `https://example.com/remote.php/dav/files/username`) |
| `WEBDAV_USERNAME` | No | Username for basic authentication (required if server needs auth) |
| `WEBDAV_PASSWORD` | No | Password for basic authentication |

## Quick start (Docker)

Build image:

```bash
docker build -t mcp-webdav:latest .
```

Run container (port 8000):

```bash
docker run --rm -p 8000:8000 \
  -e WEBDAV_URL=https://your-webdav-server.com/path \
  -e WEBDAV_USERNAME=your_username \
  -e WEBDAV_PASSWORD=your_password \
  --name mcp-webdav \
  mcp-webdav:latest
```

## Quick start (local run)

Create `.env`:

```env
WEBDAV_URL=https://your-webdav-server.com/remote.php/dav/files/username
WEBDAV_USERNAME=your_username
WEBDAV_PASSWORD=your_password
```

Install dependencies and run:

```bash
pip install -r requirements.txt
python server.py --host 0.0.0.0 --port 8000 --transport streamable-http
```

## Using with MCP clients

Add to your MCP client configuration (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "webdav": {
      "url": "http://localhost:8000/mcp",
      "transport": "streamable-http"
    }
  }
}
```

Or for Docker:

```json
{
  "mcpServers": {
    "webdav": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "WEBDAV_URL",
        "-e", "WEBDAV_USERNAME",
        "-e", "WEBDAV_PASSWORD",
        "mcp-webdav:latest"
      ],
      "env": {
        "WEBDAV_URL": "https://your-webdav-server.com/path",
        "WEBDAV_USERNAME": "your_username",
        "WEBDAV_PASSWORD": "your_password"
      }
    }
  }
}
```

## Notes

- Default server bind is `0.0.0.0:8000`.
- Uses `streamable-http` transport by default (MCP's modern HTTP transport).
- `create_directory` will return success if the directory already exists (no error).
- `update_file` checks if the file exists before overwriting. Use `upload_file` for new files.
- `delete_directory` requires the directory to be empty. Delete files within it first.
- All upload/update operations work with text content. For binary files, see the API documentation.

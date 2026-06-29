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

## Test script

A test script is included to validate all 7 WebDAV tool functions against a live WebDAV server.

### Setup

1. Create your test env file:

```bash
cp test.env.example test.env
```

2. Fill in WebDAV credentials and test inputs in `test.env`:

```env
WEBDAV_URL=https://your-webdav-server.com/remote.php/dav/files/username
WEBDAV_USERNAME=your_webdav_username
WEBDAV_PASSWORD=your_webdav_password
```

### Run tests

The test script runs all tools in CRUD order:

```bash
python test_server.py
```

It automatically loads `test.env` and runs these tests sequentially:

1. **`test_list_files`** — Lists files/directories at the root path
2. **`test_create_directory`** — Creates a test directory
3. **`test_upload_file`** — Uploads a file into the test directory
4. **`test_read_file`** — Reads and verifies the uploaded file content
5. **`test_update_file`** — Overwrites the file and verifies the new content
6. **`test_delete_file`** — Deletes the file and verifies it's gone
7. **`test_delete_directory`** — Deletes the directory

## Notes

- Default server bind is `0.0.0.0:8000`.
- Uses `streamable-http` transport by default (MCP's modern HTTP transport).
- `create_directory` will return success if the directory already exists (no error).
- `update_file` checks if the file exists before overwriting. Use `upload_file` for new files.
- `delete_directory` requires the directory to be empty. Delete files within it first.
- All upload/update operations work with text content. For binary files, see the API documentation.
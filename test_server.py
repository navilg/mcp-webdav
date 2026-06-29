from dotenv import load_dotenv
import os
import server


def _parse_tsv(tsv_str: str) -> list[dict]:
    """Parse a TSV string into a list of dicts."""
    if not tsv_str or not tsv_str.strip():
        return []
    lines = tsv_str.strip().split("\n")
    headers = lines[0].split("\t")
    records = []
    for line in lines[1:]:
        if not line.strip():
            continue
        values = line.split("\t")
        record = {}
        for i, header in enumerate(headers):
            record[header] = values[i] if i < len(values) else ""
        records.append(record)
    return records


def test_list_files():
    """Test tool A: List files and directories at root path."""
    test_path = os.getenv("TEST_LIST_PATH", "/")
    print(f"\n=== Testing list_files(path='{test_path}') ===")
    result = server.list_files(test_path)
    assert not result.startswith("Error:"), f"Tool returned an error: {result}"
    records = _parse_tsv(result)
    print(f"Found {len(records)} entries at path '{test_path}'")
    for record in records[:5]:  # Show first 5 entries
        print(f"  - {record['type']}: {record['name']} (size: {record['size']})")
    if len(records) > 5:
        print(f"  ... and {len(records) - 5} more")
    assert all(k in record for k in ("name", "type", "size", "last_modified") for record in records)
    print("PASSED")


def test_create_directory():
    """Test tool C: Create a new directory."""
    dir_name = os.getenv("TEST_DIR_NAME", "test-mcp-dir")
    print(f"\n=== Testing create_directory(path='{dir_name}') ===")
    result = server.create_directory(dir_name)
    assert not result.startswith("Error:") or "already exists" in result, \
        f"Tool returned an error: {result}"
    print(result)
    assert "URL:" in result
    print("PASSED")


def test_upload_file():
    """Test tool D: Upload a new file in the created directory."""
    dir_name = os.getenv("TEST_DIR_NAME", "test-mcp-dir")
    file_name = os.getenv("TEST_FILE_NAME", "test-mcp-file.txt")
    content = os.getenv("TEST_FILE_CONTENT", "Hello, WebDAV MCP Server!")
    file_path = f"{dir_name}/{file_name}"
    print(f"\n=== Testing upload_file(path='{file_path}', content='{content}') ===")
    result = server.upload_file(file_path, content)
    assert not result.startswith("Error:"), f"Tool returned an error: {result}"
    print(result)
    assert "URL:" in result
    print("PASSED")


def test_read_file():
    """Test tool B: Read the uploaded file contents."""
    dir_name = os.getenv("TEST_DIR_NAME", "test-mcp-dir")
    file_name = os.getenv("TEST_FILE_NAME", "test-mcp-file.txt")
    file_path = f"{dir_name}/{file_name}"
    print(f"\n=== Testing read_file(path='{file_path}') ===")
    result = server.read_file(file_path)
    assert not result.startswith("Error:"), f"Tool returned an error: {result}"
    expected_content = os.getenv("TEST_FILE_CONTENT", "Hello, WebDAV MCP Server!")
    assert result == expected_content, f"Content mismatch. Expected '{expected_content}', got '{result}'"
    print(f"File content: {result}")
    print("PASSED")


def test_update_file():
    """Test tool E: Update/overwrite the uploaded file."""
    dir_name = os.getenv("TEST_DIR_NAME", "test-mcp-dir")
    file_name = os.getenv("TEST_FILE_NAME", "test-mcp-file.txt")
    updated_content = os.getenv("TEST_UPDATE_CONTENT", "Updated content for WebDAV MCP Server!")
    file_path = f"{dir_name}/{file_name}"
    print(f"\n=== Testing update_file(path='{file_path}', content='{updated_content}') ===")
    result = server.update_file(file_path, updated_content)
    assert not result.startswith("Error:"), f"Tool returned an error: {result}"
    print(result)
    assert "URL:" in result

    # Verify the content was updated
    print("Verifying updated content...")
    read_result = server.read_file(file_path)
    assert read_result == updated_content, f"Update verification failed. Got: {read_result}"
    print(f"Verified: file content is now '{read_result}'")
    print("PASSED")


def test_delete_file():
    """Test tool F: Delete the uploaded file."""
    dir_name = os.getenv("TEST_DIR_NAME", "test-mcp-dir")
    file_name = os.getenv("TEST_FILE_NAME", "test-mcp-file.txt")
    file_path = f"{dir_name}/{file_name}"
    print(f"\n=== Testing delete_file(path='{file_path}') ===")
    result = server.delete_file(file_path)
    assert not result.startswith("Error:"), f"Tool returned an error: {result}"
    print(result)
    assert "deleted successfully" in result

    # Verify the file is gone
    print("Verifying file deletion...")
    read_result = server.read_file(file_path)
    assert read_result.startswith("Error:") and "not found" in read_result, \
        f"File should not exist after deletion. Got: {read_result}"
    print(f"Verified: {read_result}")
    print("PASSED")


def test_delete_directory():
    """Test tool G: Delete the directory."""
    dir_name = os.getenv("TEST_DIR_NAME", "test-mcp-dir")
    print(f"\n=== Testing delete_directory(path='{dir_name}') ===")
    result = server.delete_directory(dir_name)
    assert not result.startswith("Error:") or "not found" in result, \
        f"Tool returned an error: {result}"
    print(result)
    assert "deleted successfully" in result or "not found" in result
    print("PASSED")


if __name__ == "__main__":
    load_dotenv("test.env")

    print("=" * 60)
    print("WebDAV MCP Server - Tool Tests")
    print("=" * 60)

    # Run tests in logical CRUD order
    test_list_files()           # A: List (read)
    test_create_directory()     # C: Create directory
    test_upload_file()          # D: Upload file (create)
    test_read_file()            # B: Read file (read)
    test_update_file()          # E: Update file
    test_delete_file()          # F: Delete file
    test_delete_directory()     # G: Delete directory

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)

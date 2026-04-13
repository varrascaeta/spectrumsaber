"""Tests for airflow utils - get_bottom_level_file_recursive function."""

from etl.utils import get_bottom_level_file_recursive


class TestGetBottomLevelFileRecursive:
    """Test get_bottom_level_file_recursive function."""

    def test_get_bottom_level_file_recursive_only_files(self, mock_ftp_client):
        """Test with directory containing only files."""
        mock_ftp_client.get_dir_data.return_value = [
            {"path": "/test/file1.txt", "is_dir": False, "name": "file1.txt"},
            {"path": "/test/file2.txt", "is_dir": False, "name": "file2.txt"},
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/test")

        assert len(result) == 2
        assert result[0]["parent"] == "/test"
        assert result[1]["parent"] == "/test"
        assert result[0]["path"] == "/test/file1.txt"
        assert result[1]["path"] == "/test/file2.txt"

    def test_get_bottom_level_file_recursive_with_subdirs(
        self, mock_ftp_client
    ):
        """Test with directory containing subdirectories."""
        # First call returns mix of files and dirs
        # Second call returns files from subdirectory
        mock_ftp_client.get_dir_data.side_effect = [
            [
                {
                    "path": "/test/file1.txt",
                    "is_dir": False,
                    "name": "file1.txt",
                },
                {"path": "/test/subdir", "is_dir": True, "name": "subdir"},
            ],
            [
                {
                    "path": "/test/subdir/file2.txt",
                    "is_dir": False,
                    "name": "file2.txt",
                },
            ],
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/test")

        # Should get files from both levels
        assert len(result) == 2
        assert any(f["path"] == "/test/file1.txt" for f in result)
        assert any(f["path"] == "/test/subdir/file2.txt" for f in result)

    def test_get_bottom_level_file_recursive_deeply_nested(
        self, mock_ftp_client
    ):
        """Test with deeply nested directory structure."""
        mock_ftp_client.get_dir_data.side_effect = [
            [{"path": "/level1/level2", "is_dir": True, "name": "level2"}],
            [
                {
                    "path": "/level1/level2/level3",
                    "is_dir": True,
                    "name": "level3",
                }
            ],
            [
                {
                    "path": "/level1/level2/level3/file.txt",
                    "is_dir": False,
                    "name": "file.txt",
                }
            ],
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/level1")

        assert len(result) == 1
        assert result[0]["path"] == "/level1/level2/level3/file.txt"

    def test_get_bottom_level_file_recursive_empty_directory(
        self, mock_ftp_client
    ):
        """Test with empty directory."""
        mock_ftp_client.get_dir_data.return_value = []

        result = get_bottom_level_file_recursive(mock_ftp_client, "/empty")

        assert result == []

    def test_get_bottom_level_file_recursive_only_directories(
        self, mock_ftp_client
    ):
        """Test with directories that contain only other directories (no files)."""
        mock_ftp_client.get_dir_data.side_effect = [
            [{"path": "/test/dir1", "is_dir": True, "name": "dir1"}],
            [],  # dir1 is empty
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/test")

        assert result == []

    def test_get_bottom_level_file_recursive_mixed_structure(
        self, mock_ftp_client
    ):
        """Test with complex mixed structure."""
        mock_ftp_client.get_dir_data.side_effect = [
            [
                {
                    "path": "/root/file1.txt",
                    "is_dir": False,
                    "name": "file1.txt",
                },
                {"path": "/root/dir1", "is_dir": True, "name": "dir1"},
                {
                    "path": "/root/file2.txt",
                    "is_dir": False,
                    "name": "file2.txt",
                },
                {"path": "/root/dir2", "is_dir": True, "name": "dir2"},
            ],
            [
                {
                    "path": "/root/dir1/file3.txt",
                    "is_dir": False,
                    "name": "file3.txt",
                },
            ],
            [
                {
                    "path": "/root/dir2/subdir",
                    "is_dir": True,
                    "name": "subdir",
                },
            ],
            [
                {
                    "path": "/root/dir2/subdir/file4.txt",
                    "is_dir": False,
                    "name": "file4.txt",
                },
            ],
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/root")

        assert len(result) == 4
        paths = [f["path"] for f in result]
        assert "/root/file1.txt" in paths
        assert "/root/file2.txt" in paths
        assert "/root/dir1/file3.txt" in paths
        assert "/root/dir2/subdir/file4.txt" in paths

    def test_get_bottom_level_file_recursive_sets_parent(
        self, mock_ftp_client
    ):
        """Test that parent field is set correctly for non-directory files."""
        mock_ftp_client.get_dir_data.return_value = [
            {"path": "/test/file.txt", "is_dir": False, "name": "file.txt"},
        ]

        result = get_bottom_level_file_recursive(
            mock_ftp_client, "/test/parent"
        )

        assert result[0]["parent"] == "/test/parent"

    def test_get_bottom_level_file_recursive_preserves_metadata(
        self, mock_ftp_client
    ):
        """Test that file metadata is preserved during recursion."""
        mock_ftp_client.get_dir_data.return_value = [
            {
                "path": "/test/file.txt",
                "is_dir": False,
                "name": "file.txt",
                "size": 1024,
                "modified": "2024-01-01",
            },
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/test")

        assert result[0]["size"] == 1024
        assert result[0]["modified"] == "2024-01-01"
        assert result[0]["name"] == "file.txt"

    def test_get_bottom_level_file_recursive_multiple_levels_sets_correct_parent(
        self, mock_ftp_client
    ):
        """Test that parent is set correctly in multi-level recursion."""
        mock_ftp_client.get_dir_data.side_effect = [
            [{"path": "/root/dir1", "is_dir": True, "name": "dir1"}],
            [{"path": "/root/dir1/dir2", "is_dir": True, "name": "dir2"}],
            [
                {
                    "path": "/root/dir1/dir2/file.txt",
                    "is_dir": False,
                    "name": "file.txt",
                }
            ],
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/root")

        # Parent should be the immediate directory, not root
        assert result[0]["parent"] == "/root/dir1/dir2"

    def test_get_bottom_level_file_recursive_handles_many_files(
        self, mock_ftp_client
    ):
        """Test with a large number of files."""
        many_files = [
            {
                "path": f"/test/file{i}.txt",
                "is_dir": False,
                "name": f"file{i}.txt",
            }
            for i in range(100)
        ]
        mock_ftp_client.get_dir_data.return_value = many_files

        result = get_bottom_level_file_recursive(mock_ftp_client, "/test")

        assert len(result) == 100
        assert all(f["parent"] == "/test" for f in result)

    def test_get_bottom_level_file_recursive_handles_special_chars_in_path(
        self, mock_ftp_client
    ):
        """Test with special characters in file paths."""
        mock_ftp_client.get_dir_data.return_value = [
            {
                "path": "/test/file-with-dash.txt",
                "is_dir": False,
                "name": "file-with-dash.txt",
            },
            {
                "path": "/test/file_with_underscore.txt",
                "is_dir": False,
                "name": "file_with_underscore.txt",
            },
            {
                "path": "/test/file.2024.txt",
                "is_dir": False,
                "name": "file.2024.txt",
            },
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/test")

        assert len(result) == 3
        paths = [f["path"] for f in result]
        assert "/test/file-with-dash.txt" in paths
        assert "/test/file_with_underscore.txt" in paths
        assert "/test/file.2024.txt" in paths

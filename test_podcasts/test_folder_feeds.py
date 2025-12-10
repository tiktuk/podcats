"""Tests for the folder-feeds feature (FolderChannel class)."""
import os
import xml.etree.ElementTree as ET
import pytest
from podcats import FolderChannel, is_audio_file


# The root directory for our test audio files
TEST_AUDIO_ROOT = os.path.join(os.path.dirname(__file__), "sample_audio")


@pytest.fixture
def folder_channel():
    """Fixture that provides a FolderChannel instance for testing."""
    return FolderChannel(
        root_dir=TEST_AUDIO_ROOT,
        root_url="http://localhost:5000",
        host="localhost",
        port=5000,
        title="Test Folder Feeds",
        link=None,
    )


class TestFolderChannelDiscovery:
    """Tests for folder discovery functionality."""

    def test_get_folders_finds_all_audio_folders(self, folder_channel):
        """Test that get_folders() finds all immediate subfolders with audio files."""
        folders = folder_channel.get_folders()

        # Should find all 3 audiobook folders
        assert len(folders) == 3
        assert "Solaris" in folders
        assert "Roadside Picnic" in folders
        assert "Confessions of a Mask" in folders


class TestFolderChannelGetChannel:
    """Tests for getting individual channel instances."""

    def test_get_channel_returns_channel_for_valid_folder(self, folder_channel):
        """Test that get_channel() returns a valid Channel for existing folder."""
        channel = folder_channel.get_channel("Solaris")

        assert channel is not None
        assert channel.folder_path == "Solaris"

    def test_get_channel_returns_none_for_invalid_folder(self, folder_channel):
        """Test that get_channel() returns None for non-existent folder."""
        channel = folder_channel.get_channel("NonExistentFolder")

        assert channel is None

    def test_get_channel_only_includes_folder_episodes(self, folder_channel):
        """Test that channel only includes episodes from the specific folder."""
        channel = folder_channel.get_channel("Solaris")
        episodes = list(channel)

        # Should only have episodes from the Solaris folder (3 chapters)
        assert len(episodes) == 3
        for episode in episodes:
            assert "Solaris" in episode.filename

    def test_get_channel_does_not_include_subfolder_episodes(self, folder_channel):
        """Test that channel does not include episodes from nested subfolders."""
        # Each folder should only have its own episodes, not from other folders
        for folder_name in folder_channel.get_folders():
            channel = folder_channel.get_channel(folder_name)
            episodes = list(channel)
            for episode in episodes:
                # All episodes should be from this folder specifically
                assert folder_name in episode.filename


class TestFolderChannelFeedGeneration:
    """Tests for RSS feed generation in folder-feeds mode."""

    def test_folder_channel_generates_valid_xml_for_each_folder(self, folder_channel):
        """Test that each folder generates valid XML RSS feed."""
        for folder_name in folder_channel.get_folders():
            channel = folder_channel.get_channel(folder_name)
            xml_output = channel.as_xml()

            # Should be valid XML
            try:
                root = ET.fromstring(xml_output)
            except ET.ParseError as e:
                pytest.fail(f"Generated XML for '{folder_name}' is not well-formed: {e}")

            # Should be RSS 2.0
            assert root.tag == "rss"
            assert root.get("version") == "2.0"

            # Should have channel element
            rss_channel = root.find("channel")
            assert rss_channel is not None

    def test_folder_feed_has_correct_episode_count(self, folder_channel):
        """Test that each folder feed has the correct number of episodes."""
        for folder_name in folder_channel.get_folders():
            channel = folder_channel.get_channel(folder_name)
            xml_output = channel.as_xml()

            # Count items in the feed
            root = ET.fromstring(xml_output)
            items = root.findall(".//item")

            # Each test folder has 3 chapters
            assert len(items) == 3, f"Expected 3 items for '{folder_name}', got {len(items)}"


class TestFolderChannelHtmlIndex:
    """Tests for HTML index page generation."""

    def test_html_index_is_generated(self, folder_channel):
        """Test that HTML index page is generated."""
        html_output = folder_channel.as_html_index()

        assert html_output is not None
        assert isinstance(html_output, bytes)
        assert len(html_output) > 0

    def test_html_index_lists_all_folders(self, folder_channel):
        """Test that HTML index lists all audio folders."""
        html_string = folder_channel.as_html_index().decode("utf-8")

        assert "Solaris" in html_string
        assert "Roadside Picnic" in html_string
        assert "Confessions of a Mask" in html_string

    def test_html_index_contains_feed_links(self, folder_channel):
        """Test that HTML index contains RSS feed links for each folder."""
        html_string = folder_channel.as_html_index().decode("utf-8")

        # Check for feed URL patterns
        assert "/feed/Solaris" in html_string or "/feed/Solaris" in html_string.replace("%20", " ")
        assert "/feed/Roadside%20Picnic" in html_string or "/feed/Roadside Picnic" in html_string

    def test_html_index_contains_web_links(self, folder_channel):
        """Test that HTML index contains web interface links for each folder."""
        html_string = folder_channel.as_html_index().decode("utf-8")

        # Check for web URL patterns
        assert "/web/Solaris" in html_string or "/web/Solaris" in html_string.replace("%20", " ")


class TestFolderChannelWithEmptyDirectory:
    """Tests for edge cases with empty or invalid directories."""

    def test_empty_directory_returns_no_folders(self, tmp_path):
        """Test that an empty directory returns no folders."""
        folder_channel = FolderChannel(
            root_dir=str(tmp_path),
            root_url="http://localhost:5000",
            host="localhost",
            port=5000,
            title="Empty Test",
            link=None,
        )

        folders = folder_channel.get_folders()
        assert folders == []

    def test_directory_with_non_audio_subfolders_returns_no_folders(self, tmp_path):
        """Test that subfolders without audio files are not included."""
        # Create a subfolder with only text files
        subfolder = tmp_path / "TextOnly"
        subfolder.mkdir()
        (subfolder / "readme.txt").touch()

        folder_channel = FolderChannel(
            root_dir=str(tmp_path),
            root_url="http://localhost:5000",
            host="localhost",
            port=5000,
            title="No Audio Test",
            link=None,
        )

        folders = folder_channel.get_folders()
        assert folders == []

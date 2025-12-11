"""Tests for the force-order-by-name feature using natural sorting."""
import os
import pytest
from podcats import Episode, Channel, natural_sort_key


# The root directory for our test audio files
TEST_AUDIO_ROOT = os.path.join(os.path.dirname(__file__), "sample_audio")
SOLARIS_DIR = os.path.join(TEST_AUDIO_ROOT, "Solaris")


class TestNaturalSortKey:
    """Tests for the natural_sort_key helper function."""

    def test_natural_sort_numbers(self):
        """Test that numbers are sorted numerically, not lexicographically."""
        items = ["Track 2", "Track 10", "Track 1"]
        sorted_items = sorted(items, key=natural_sort_key)
        assert sorted_items == ["Track 1", "Track 2", "Track 10"]

    def test_natural_sort_with_leading_zeros(self):
        """Test that leading zeros are handled correctly."""
        items = ["01 - A", "02 - B", "10 - C"]
        sorted_items = sorted(items, key=natural_sort_key)
        assert sorted_items == ["01 - A", "02 - B", "10 - C"]

    def test_natural_sort_case_insensitive(self):
        """Test that sorting is case-insensitive."""
        items = ["Zebra", "apple", "Banana"]
        sorted_items = sorted(items, key=natural_sort_key)
        assert sorted_items == ["apple", "Banana", "Zebra"]

    def test_natural_sort_mixed_content(self):
        """Test sorting with mixed text and numbers."""
        items = ["file10.mp3", "file2.mp3", "file1.mp3"]
        sorted_items = sorted(items, key=natural_sort_key)
        assert sorted_items == ["file1.mp3", "file2.mp3", "file10.mp3"]


class TestEpisodeNaturalSort:
    """Tests for Episode sorting with force_order_by_name enabled."""

    def test_episodes_sort_naturally(self):
        """Test that episodes sort by filename using natural sort."""
        file1 = os.path.join(SOLARIS_DIR, "01 - Chapter 1.mp3")
        file2 = os.path.join(SOLARIS_DIR, "02 - Chapter 2.mp3")
        file3 = os.path.join(SOLARIS_DIR, "03 - Chapter 3.mp3")

        ep1 = Episode(file1, "/Solaris", "http://localhost:5000", force_order_by_name=True)
        ep2 = Episode(file2, "/Solaris", "http://localhost:5000", force_order_by_name=True)
        ep3 = Episode(file3, "/Solaris", "http://localhost:5000", force_order_by_name=True)

        # Episodes should be sorted by natural order of filenames
        assert ep1 < ep2 < ep3

    def test_episodes_sort_correctly_with_sorted(self):
        """Test that sorted() works correctly with force_order_by_name."""
        files = [
            os.path.join(SOLARIS_DIR, "03 - Chapter 3.mp3"),
            os.path.join(SOLARIS_DIR, "01 - Chapter 1.mp3"),
            os.path.join(SOLARIS_DIR, "02 - Chapter 2.mp3"),
        ]

        episodes = [
            Episode(f, "/Solaris", "http://localhost:5000", force_order_by_name=True)
            for f in files
        ]

        sorted_episodes = sorted(episodes)

        # Should be sorted by natural order (1, 2, 3)
        assert "01" in sorted_episodes[0].filename
        assert "02" in sorted_episodes[1].filename
        assert "03" in sorted_episodes[2].filename

    def test_force_order_disabled_uses_date(self):
        """Test that without force_order_by_name, episodes sort by date."""
        file1 = os.path.join(SOLARIS_DIR, "01 - Chapter 1.mp3")
        file2 = os.path.join(SOLARIS_DIR, "02 - Chapter 2.mp3")

        ep1 = Episode(file1, "/Solaris", "http://localhost:5000", force_order_by_name=False)
        ep2 = Episode(file2, "/Solaris", "http://localhost:5000", force_order_by_name=False)

        # Compare using date, not filename
        if ep1.date < ep2.date:
            assert ep1 < ep2
        elif ep1.date > ep2.date:
            assert ep1 > ep2
        else:
            assert ep1 == ep2


class TestChannelWithForceOrderByName:
    """Tests for Channel with force_order_by_name enabled."""

    def test_channel_episodes_sorted_naturally(self):
        """Test that channel episodes are sorted using natural sort."""
        channel = Channel(
            root_dir=SOLARIS_DIR,
            root_url="http://localhost:5000",
            host="localhost",
            port=5000,
            title="Test",
            link=None,
            force_order_by_name=True,
        )

        sorted_episodes = sorted(channel)

        # Should be sorted naturally by filename
        assert "01" in sorted_episodes[0].filename
        assert "02" in sorted_episodes[1].filename
        assert "03" in sorted_episodes[2].filename

    def test_channel_without_force_order(self):
        """Test that Channel works normally without force_order_by_name."""
        channel = Channel(
            root_dir=SOLARIS_DIR,
            root_url="http://localhost:5000",
            host="localhost",
            port=5000,
            title="Test",
            link=None,
            force_order_by_name=False,
        )

        episodes = list(channel)
        assert len(episodes) > 0

        # All episodes should have force_order_by_name=False
        for ep in episodes:
            assert ep.force_order_by_name is False


class TestNaiveComparisonEdgeCases:
    """Tests for edge cases where naive string comparison would fail."""

    def test_track_10_vs_track_2_natural_sort(self, tmp_path):
        """Test that 'Track 10' sorts after 'Track 2' (not before as in naive string sort)."""
        # Create test files - naive sort would put "Track 10" before "Track 2"
        (tmp_path / "Track 2.mp3").write_bytes(b'\xff\xfb\x90\x00' * 100)
        (tmp_path / "Track 10.mp3").write_bytes(b'\xff\xfb\x90\x00' * 100)
        (tmp_path / "Track 1.mp3").write_bytes(b'\xff\xfb\x90\x00' * 100)

        ep1 = Episode(str(tmp_path / "Track 1.mp3"), "/test", "http://localhost:5000", force_order_by_name=True)
        ep2 = Episode(str(tmp_path / "Track 2.mp3"), "/test", "http://localhost:5000", force_order_by_name=True)
        ep10 = Episode(str(tmp_path / "Track 10.mp3"), "/test", "http://localhost:5000", force_order_by_name=True)

        # Natural sort: Track 1 < Track 2 < Track 10
        assert ep1 < ep2 < ep10

        # Also verify dates are sequential
        assert ep1.date < ep2.date < ep10.date

    def test_episode2_vs_episode10_natural_sort(self, tmp_path):
        """Test that 'Episode2' sorts before 'Episode10' using natural sort."""
        (tmp_path / "Episode2.mp3").write_bytes(b'\xff\xfb\x90\x00' * 100)
        (tmp_path / "Episode10.mp3").write_bytes(b'\xff\xfb\x90\x00' * 100)

        ep2 = Episode(str(tmp_path / "Episode2.mp3"), "/test", "http://localhost:5000", force_order_by_name=True)
        ep10 = Episode(str(tmp_path / "Episode10.mp3"), "/test", "http://localhost:5000", force_order_by_name=True)

        # Natural sort: Episode2 < Episode10 (not lexicographic where Episode10 < Episode2)
        assert ep2 < ep10
        assert ep2.date < ep10.date


class TestFilesWithoutNumbers:
    """Tests for files that have no numbers in the filename."""

    def test_alphabetical_files_sort_by_comparison(self, tmp_path):
        """Test that files without numbers still sort correctly via comparison operators."""
        (tmp_path / "Alpha.mp3").write_bytes(b'\xff\xfb\x90\x00' * 100)
        (tmp_path / "Beta.mp3").write_bytes(b'\xff\xfb\x90\x00' * 100)
        (tmp_path / "Gamma.mp3").write_bytes(b'\xff\xfb\x90\x00' * 100)

        ep_alpha = Episode(str(tmp_path / "Alpha.mp3"), "/test", "http://localhost:5000", force_order_by_name=True)
        ep_beta = Episode(str(tmp_path / "Beta.mp3"), "/test", "http://localhost:5000", force_order_by_name=True)
        ep_gamma = Episode(str(tmp_path / "Gamma.mp3"), "/test", "http://localhost:5000", force_order_by_name=True)

        # Should sort alphabetically via comparison operators
        assert ep_alpha < ep_beta < ep_gamma

    def test_files_without_numbers_get_valid_dates(self, tmp_path):
        """Test that files without numbers still generate valid dates."""
        (tmp_path / "NoNumbers.mp3").write_bytes(b'\xff\xfb\x90\x00' * 100)

        ep = Episode(str(tmp_path / "NoNumbers.mp3"), "/test", "http://localhost:5000", force_order_by_name=True)

        # Should still have a valid date
        assert isinstance(ep.date, (int, float))
        assert ep.date > 0

    def test_mixed_numbered_and_unnumbered_files(self, tmp_path):
        """Test sorting with a mix of numbered and unnumbered files."""
        (tmp_path / "01 - First.mp3").write_bytes(b'\xff\xfb\x90\x00' * 100)
        (tmp_path / "02 - Second.mp3").write_bytes(b'\xff\xfb\x90\x00' * 100)
        (tmp_path / "Bonus.mp3").write_bytes(b'\xff\xfb\x90\x00' * 100)

        ep1 = Episode(str(tmp_path / "01 - First.mp3"), "/test", "http://localhost:5000", force_order_by_name=True)
        ep2 = Episode(str(tmp_path / "02 - Second.mp3"), "/test", "http://localhost:5000", force_order_by_name=True)
        ep_bonus = Episode(str(tmp_path / "Bonus.mp3"), "/test", "http://localhost:5000", force_order_by_name=True)

        # Numbered files should sort correctly
        assert ep1 < ep2

        # All episodes should have valid dates
        assert ep1.date > 0
        assert ep2.date > 0
        assert ep_bonus.date > 0

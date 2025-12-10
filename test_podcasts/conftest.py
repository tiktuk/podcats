import os
import pytest
from podcats import Channel

# The root directory for our test audio files
TEST_AUDIO_ROOT = os.path.join(os.path.dirname(__file__), "sample_audio")


@pytest.fixture
def test_channel():
    """Fixture that provides a Channel instance for testing."""
    return Channel(
        root_dir=TEST_AUDIO_ROOT,
        root_url="http://localhost:5000",
        host="localhost",
        port=5000,
        title="Test Audiobook Feed",
        link="http://example.com/test-feed",
    )


@pytest.fixture
def solaris_episode(test_channel):
    """Fixture that provides the first Solaris episode (which has a cover image)."""
    for episode in test_channel:
        if "Solaris" in episode.filename:
            return episode
    pytest.fail("Could not find a Solaris episode")

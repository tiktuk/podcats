import os
import pytest
from podcats import Channel, Episode

# The root directory for our test audio files
TEST_AUDIO_ROOT = os.path.join(os.path.dirname(__file__), 'sample_audio')

@pytest.fixture(scope="module")
def channel_fixture():
    """
    A pytest fixture that creates a Channel instance for our test suite.
    This fixture has 'module' scope, so it's created only once for all tests in this file.
    """
    return Channel(
        root_dir=TEST_AUDIO_ROOT,
        root_url='http://localhost:5000',
        host='localhost',
        port=5000,
        title='Test Audiobook Feed',
        link='http://example.com/test-feed'
    )

def test_channel_finds_all_episodes(channel_fixture):
    """
    Tests if the Channel correctly finds all audio files in the directory structure.
    """
    # The Channel object is an iterator; convert it to a list to count the episodes.
    episodes = list(channel_fixture)
    
    # We created 3 chapters for each of the 3 audiobooks.
    expected_number_of_episodes = 9
    
    assert len(episodes) == expected_number_of_episodes, \
        f"Expected to find {expected_number_of_episodes} episodes, but found {len(episodes)}."

def test_episode_metadata_is_correct(channel_fixture):
    """
    Tests if a specific Episode has its metadata correctly parsed from the ID3 tags.
    """
    episodes = list(channel_fixture)
    
    # Sort episodes by filename to ensure a predictable order for testing
    episodes.sort(key=lambda e: os.path.basename(e.filename))

    # Find the first chapter of Solaris for inspection
    solaris_chapter_1 = next((ep for ep in episodes if 'Solaris' in ep.filename and '01' in ep.filename), None)
    
    assert solaris_chapter_1 is not None, "Could not find 'Solaris/01 - Chapter 1.mp3' in the episodes."
    
    # The title logic from the source is: <filename_without_ext><ID3_Title_Tag> 
    # So, "01 - Chapter 1" + "Chapter 1"
    expected_title = "01 - Chapter 1Chapter 1"
    assert solaris_chapter_1.title == expected_title, \
        f"Expected title to be '{expected_title}', but got '{solaris_chapter_1.title}'."
        
    # The test file is 1 second long
    expected_duration = 1
    assert solaris_chapter_1.duration == expected_duration, \
        f"Expected duration to be {expected_duration}s, but got {solaris_chapter_1.duration}s."

    # Check URL generation
    expected_url_path = "/static/Solaris/01%20-%20Chapter%201.mp3"
    assert expected_url_path in solaris_chapter_1.url

def test_feed_generation_as_xml(channel_fixture):
    """
    Tests if the channel's XML output is generated and contains expected content.
    """
    xml_output = channel_fixture.as_xml()
    
    assert xml_output is not None
    assert isinstance(xml_output, str)
    assert len(xml_output) > 0
    
    # Check for channel-level content
    assert "<title>Test Audiobook Feed</title>" in xml_output
    
    # Check for item-level content for a few samples
    assert "<title>01 - Chapter 1Chapter 1</title>" in xml_output # Solaris
    assert "<title>02 - Chapter 2Chapter 2</title>" in xml_output # Roadside Picnic
    assert "<title>03 - Chapter 3Chapter 3</title>" in xml_output # Confessions of a Mask
    
    # Check that all 9 items are present
    assert xml_output.count("<item>") == 9

def test_feed_generation_as_html(channel_fixture):
    """
    Tests if the channel's HTML output is generated and contains expected content.
    """
    html_output = channel_fixture.as_html()

    # The as_html() method encodes the output to bytes
    assert html_output is not None
    assert isinstance(html_output, bytes)
    assert len(html_output) > 0

    # Decode for string-based assertions
    html_string = html_output.decode('utf-8')

    # Check for channel-level content (from template)
    assert '<h1>Test Audiobook Feed</h1>' in html_string

    # Check for item-level content based on the actual HTML structure
    assert '>01 - Chapter 1Chapter 1</a></h2>' in html_string
    assert '<p><strong>Directory:</strong> Solaris</p>' in html_string
    assert '<p><strong>Directory:</strong> Roadside Picnic</p>' in html_string
    assert '<p><strong>Directory:</strong> Confessions of a Mask</p>' in html_string

    # Check that all 9 items are present by counting the <article> tags
    assert html_string.count('<article class=') == 9
import os
import xml.etree.ElementTree as ET


def test_channel_finds_all_episodes(test_channel):
    """
    Tests if the Channel correctly finds all audio files in the directory structure.
    """
    # The Channel object is an iterator; convert it to a list to count the episodes.
    episodes = list(test_channel)

    # We created 3 chapters for each of the 3 audiobooks.
    expected_number_of_episodes = 9

    assert (
        len(episodes) == expected_number_of_episodes
    ), f"Expected to find {expected_number_of_episodes} episodes, but found {len(episodes)}."


def test_episode_metadata_is_correct(test_channel):
    """
    Tests if a specific Episode has its metadata correctly parsed from the ID3 tags.
    """
    episodes = list(test_channel)

    # Sort episodes by filename to ensure a predictable order for testing
    episodes.sort(key=lambda e: os.path.basename(e.filename))

    # Find the first chapter of Solaris for inspection
    solaris_chapter_1 = next(
        (ep for ep in episodes if "Solaris" in ep.filename and "01" in ep.filename),
        None,
    )

    assert (
        solaris_chapter_1 is not None
    ), "Could not find 'Solaris/01 - Chapter 1.mp3' in the episodes."

    # The title logic now prefers ID3 tags: if TIT2 exists, use that
    expected_title = "Chapter 1"
    assert (
        solaris_chapter_1.title == expected_title
    ), f"Expected title to be '{expected_title}', but got '{solaris_chapter_1.title}'."

    # The test file is 1 second long
    expected_duration = 1
    assert (
        solaris_chapter_1.duration == expected_duration
    ), f"Expected duration to be {expected_duration}s, but got {solaris_chapter_1.duration}s."

    # Check URL generation
    expected_url_path = "/static/Solaris/01%20-%20Chapter%201.mp3"
    assert expected_url_path in solaris_chapter_1.url


def test_feed_generation_as_xml(test_channel):
    """
    Tests if the channel's XML output is generated and contains expected content.
    """
    xml_output = test_channel.as_xml()

    assert xml_output is not None
    assert isinstance(xml_output, str)
    assert len(xml_output) > 0

    # Test that the XML is well-formed and valid
    try:
        root = ET.fromstring(xml_output)
    except ET.ParseError as e:
        assert False, f"Generated XML is not well-formed: {e}"

    # Check RSS structure
    assert root.tag == "rss", "Root element should be 'rss'"
    assert root.get("version") == "2.0", "RSS version should be 2.0"

    # Check for channel element
    channel = root.find("channel")
    assert channel is not None, "RSS should have a channel element"

    # Check for required RSS elements
    assert channel.find("title") is not None, "Channel should have a title"
    assert channel.find("description") is not None, "Channel should have a description"
    assert channel.find("link") is not None, "Channel should have a link"

    # Check for channel-level content
    assert "<title>Test Audiobook Feed</title>" in xml_output

    # Check for item-level content for a few samples
    assert "<title>Chapter 1</title>" in xml_output  # Solaris
    assert "<title>Chapter 2</title>" in xml_output  # Roadside Picnic
    assert (
        "<title>Chapter 3</title>" in xml_output
    )  # Confessions of a Mask

    # Check that all 9 items are present
    assert xml_output.count("<item>") == 9

    # Check that items have required RSS elements
    items = channel.findall("item")
    assert len(items) == 9, "Should have 9 items in the RSS feed"

    # Check first item has required elements
    first_item = items[0]
    assert first_item.find("title") is not None, "Items should have a title"
    assert first_item.find("enclosure") is not None, "Items should have an enclosure"
    assert first_item.find("guid") is not None, "Items should have a guid"
    assert first_item.find("pubDate") is not None, "Items should have a pubDate"


def test_feed_generation_as_html(test_channel):
    """
    Tests if the channel's HTML output is generated and contains expected content.
    """
    html_output = test_channel.as_html()

    # The as_html() method encodes the output to bytes
    assert html_output is not None
    assert isinstance(html_output, bytes)
    assert len(html_output) > 0

    # Decode for string-based assertions
    html_string = html_output.decode("utf-8")

    # Test that the HTML is well-formed (basic check for doctype and structure)
    assert html_string.startswith("<!DOCTYPE html>"), "HTML should start with DOCTYPE"
    assert "<html" in html_string, "HTML should contain html tag"
    assert "</html>" in html_string, "HTML should end with closing html tag"

    # Check for basic HTML structure
    assert "<head>" in html_string, "HTML should have head section"
    assert "<body>" in html_string, "HTML should have body section"
    assert "</head>" in html_string, "HTML should close head section"
    assert "</body>" in html_string, "HTML should close body section"

    # Check for channel-level content (from template)
    assert "<h1>Test Audiobook Feed</h1>" in html_string

    # Check for item-level content based on the actual HTML structure
    assert ">Chapter 1</a></h2>" in html_string
    assert "<p><strong>Directory:</strong> Solaris</p>" in html_string
    assert "<p><strong>Directory:</strong> Roadside Picnic</p>" in html_string
    assert "<p><strong>Directory:</strong> Confessions of a Mask</p>" in html_string

    # Check that all 9 items are present by counting the <article> tags
    assert html_string.count("<article class=") == 9

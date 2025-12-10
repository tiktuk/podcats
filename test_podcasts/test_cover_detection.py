import os
from podcats import Episode


def test_cover_detection_in_same_directory(solaris_episode):
    """Test that cover images are detected when they exist in the same directory as the audio file."""
    # The cover.jpg we created should be detected
    assert solaris_episode.image is not None, "Cover image should be detected"
    assert (
        "cover.jpg" in solaris_episode.image
    ), "The detected cover should be cover.jpg"


def test_cover_image_url_construction(solaris_episode):
    """Test that the cover image URL is constructed correctly."""
    # The URL should be properly constructed
    assert solaris_episode.image.startswith(
        "http://localhost:5000/static/"
    ), "Image URL should start with the root URL"
    assert (
        "cover.jpg" in solaris_episode.image
    ), "Image URL should include the cover filename"
    assert (
        "Solaris" in solaris_episode.image
    ), "Image URL should include the relative directory"


def test_cover_image_in_rss_feed(test_channel):
    """Test that the cover image is included in the RSS feed."""
    # Generate the RSS feed
    rss_feed = test_channel.as_xml()

    # Check that the cover image is included in the channel metadata
    assert "<itunes:image href=" in rss_feed, "RSS feed should include itunes:image tag"
    assert "cover.jpg" in rss_feed, "RSS feed should include the cover image filename"
    assert (
        "http://localhost:5000/static/Solaris/cover.jpg" in rss_feed
    ), "RSS feed should include full URL to cover image"


def test_cover_image_in_html_output(test_channel):
    """Test that the cover image is included in the HTML output."""
    # Generate the HTML output
    html_output = test_channel.as_html().decode("utf-8")

    # Check that the cover image is included in the HTML
    assert (
        '<img class="book-cover" src="' in html_output
    ), "HTML should include book cover image"
    assert "cover.jpg" in html_output, "HTML should include the cover image filename"
    assert (
        "http://localhost:5000/static/Solaris/cover.jpg" in html_output
    ), "HTML should include full URL to cover image"


def test_no_cover_image_for_book_without_cover():
    """Test that no cover image is returned for a book without a cover image file."""
    # This should be a path to an audio file that doesn't have a cover image
    audio_file = os.path.join(
        os.path.dirname(__file__),
        "sample_audio",
        "Confessions of a Mask",
        "03 - Chapter 3.mp3",
    )
    episode = Episode(audio_file, "Confessions of a Mask", "http://localhost:5000")

    # The image property should be None since there's no cover image
    assert (
        episode.image is None
    ), "No cover image should be detected for a book without a cover file"

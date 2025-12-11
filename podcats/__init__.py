"""
Podcats is a podcast feed generator and a server.

It generates RSS feeds for podcast episodes from local audio files and,
optionally, exposes the feed and as well as the episode file via
a built-in web server so that they can be imported into iTunes
or another podcast client.

"""
import datetime
import logging
import os
import re
import time
import argparse
import mimetypes
from email.utils import formatdate
from os import path
from urllib.parse import quote, unquote
from xml.sax.saxutils import escape, quoteattr

import mutagen
import humanize
from mutagen.id3 import ID3
from mutagen.mp3 import HeaderNotFoundError
from flask import Flask, Response
# noinspection PyPackageRequirements
from jinja2 import Environment, FileSystemLoader

__version__ = '0.6.3'
__licence__ = 'BSD'
__author__ = 'Jakub Roztocil'
__url__ = 'https://github.com/jakubroztocil/podcats'


WEB_PATH = '/web'
STATIC_PATH = '/static'
TEMPLATES_ROOT = os.path.join(os.path.dirname(__file__), 'templates')
BOOK_COVER_EXTENSIONS = ('.jpg', '.jpeg', '.png')

jinja2_env = Environment(loader=FileSystemLoader(TEMPLATES_ROOT))

logger = logging.getLogger(__name__)


def is_audio_file(filepath):
    """Check if a file is an audio file based on mimetype or extension."""
    mimetype = mimetypes.guess_type(filepath)[0]
    return (mimetype and 'audio' in mimetype) or filepath.endswith('m4b')


def natural_sort_key(text):
    """
    Generate a sort key for natural/alphanumeric sorting.
    
    This splits the text into chunks of digits and non-digits,
    converting digit chunks to integers for proper numeric comparison.
    Example: "Track 2" < "Track 10" (instead of "Track 10" < "Track 2")

    >>> natural_sort_key("Track 10")
    ['track ', 10, '']
    >>> natural_sort_key("Track 2")
    ['track ', 2, '']
    """
    def convert(chunk):
        return int(chunk) if chunk.isdigit() else chunk.lower()
    
    return [convert(c) for c in re.split(r'(\d+)', text)]


class Episode(object):
    """Podcast episode"""

    def __init__(self, filename, relative_dir, root_url, title_mode='default', force_order_by_name=False):
        self.filename = filename
        self.relative_dir = relative_dir
        self.root_url = root_url
        self.title_mode = title_mode  # 'default', 'id3', or 'filename'
        self.force_order_by_name = force_order_by_name
        self.length = os.path.getsize(filename)

        try:
            self.tags = mutagen.File(self.filename, easy=True) or {}
        except HeaderNotFoundError as err:
            self.tags = {}
            logger.warning(
                "Could not load tags of file {filename} due to: {err!r}".format(filename=self.filename, err=err)
            )

        try:
            self.id3 = ID3(self.filename)
        except Exception:
            self.id3 = None

    def __lt__(self, other):
        if self.force_order_by_name:
            return natural_sort_key(os.path.basename(self.filename)) < natural_sort_key(os.path.basename(other.filename))
        return self.date < other.date

    def __gt__(self, other):
        if self.force_order_by_name:
            return natural_sort_key(os.path.basename(self.filename)) > natural_sort_key(os.path.basename(other.filename))
        return self.date > other.date

    def __eq__(self, other):
        if self.force_order_by_name:
            return natural_sort_key(os.path.basename(self.filename)) == natural_sort_key(os.path.basename(other.filename))
        return self.date == other.date

    def __le__(self, other):
        return self < other or self == other

    def __ge__(self, other):
        return self > other or self == other

    def as_xml(self):
        """Return episode item XML"""
        filename = os.path.basename(self.filename)
        directory = os.path.split(os.path.dirname(self.filename))[-1]
        template = jinja2_env.get_template('episode.xml')

        return template.render(
            title=escape(self.title),
            url=quoteattr(self.url),
            guid=escape(self.url),
            mimetype=self.mimetype,
            length=self.length,
            file_size_human=humanize.naturalsize(self.length),
            date=formatdate(self.date),
            image_url=self.image,
            duration=self.duration,
            duration_formatted=self.duration_formatted,
            filename=filename,
            directory=directory,
        )

    def as_html(self):
        """Return episode item html"""
        filename = os.path.basename(self.filename)
        directory = os.path.split(os.path.dirname(self.filename))[-1]
        template = jinja2_env.get_template('episode.html')
        try:
            date = formatdate(self.date)
        except ValueError:
            date = datetime.datetime.now(tz=datetime.timezone.utc)

        return template.render(
            title=escape(self.title),
            url=self.url,
            filename=filename,
            directory=directory,
            mimetype=self.mimetype,
            length=self.length,
            file_size_human=humanize.naturalsize(self.length),
            date=date,
            image_url=self.image,
            duration=self.duration,
            duration_formatted=self.duration_formatted,
        )

    def get_tag(self, name):
        """Return episode file tag info"""
        try:
            return self.tags[name][0]
        except (KeyError, IndexError):
            pass

    def _to_url(self, filepath):
        fn = os.path.basename(filepath)
        path_ = STATIC_PATH + '/' + self.relative_dir + '/' + fn
        path_ = re.sub(r'//', '/', path_)

        # Ensure we don't get double slashes when joining root_url and path
        if self.root_url.endswith('/') and path_.startswith('/'):
            path_ = path_[1:]  # Remove leading slash from path if root_url ends with slash

        url = self.root_url + quote(path_, errors="surrogateescape")
        return url

    @property
    def title(self):
        """Return episode title based on title_mode setting"""
        filename_title = os.path.splitext(os.path.basename(self.filename))[0]
        
        if self.title_mode == 'filename':
            # Use only the filename, ignore ID3 tags
            return filename_title
        
        if self.title_mode == 'id3':
            # Prefer ID3 tag, fall back to filename
            if self.id3 is not None:
                val = self.id3.getall('TIT2')
                if len(val) > 0:
                    title = str(val[0])
                    # Optionally append comment if present
                    comm = self.id3.getall('COMM')
                    if len(comm) > 0:
                        title += ' ' + str(comm[0])
                    return title
            return filename_title
        
        # Default: concatenate filename + ID3 title + comment (original behavior)
        text = filename_title
        if self.id3 is not None:
            val = self.id3.getall('TIT2')
            if len(val) > 0:
                text += str(val[0])
            val = self.id3.getall('COMM')
            if len(val) > 0:
                text += ' ' + str(val[0])
        return text

    @property
    def url(self):
        """Return episode url"""
        return self._to_url(self.filename)

    @property
    def date(self):
        """Return episode date as unix timestamp"""
        # If force_order_by_name is enabled, create artificial dates based on natural sort order.
        # This is needed because podcast players typically sort episodes by date, so we generate
        # fake dates that follow the natural filename order to ensure proper episode sequencing.
        if self.force_order_by_name:
            base_name = os.path.splitext(os.path.basename(self.filename))[0]
            
            # Create a base timestamp (Jan 1, 2020)
            base_timestamp = time.mktime(time.strptime("2020-01-01", "%Y-%m-%d"))
            
            # Extract the first number from the filename for day offset
            # e.g., "001 - Title" → 1, "002 - Title" → 2
            numbers = re.findall(r'\d+', base_name)
            if numbers:
                # Use the first number as the day offset
                day_offset = int(numbers[0])
            else:
                # No numbers found - use sum of character values for alphabetical ordering
                # This preserves relative order (earlier alphabet = smaller sum = earlier date)
                day_offset = sum(ord(c) for c in base_name.lower())
            
            # Convert to seconds (1 day = 86400 seconds)
            offset_seconds = day_offset * 86400
            
            return base_timestamp + offset_seconds
        
        # For regular podcast episodes, use the original logic
        dt = self.get_tag('date')
        if dt:
            formats = [
                '%Y-%m-%d:%H:%M:%S',
                '%Y-%m-%d:%H:%M',
                '%Y-%m-%d:%H',
                '%Y-%m-%d',
                '%Y-%m',
                '%Y',
            ]
            for fmt in formats:
                try:
                    dt = time.mktime(time.strptime(dt, fmt))
                    break
                except ValueError:
                    pass
            else:
                dt = None

        if not dt:
            dt = os.path.getmtime(self.filename)

        return dt

    @property
    def mimetype(self):
        """Return file mimetype name"""
        if self.filename.endswith('m4b'):
            return 'audio/x-m4b'
        else:
            return mimetypes.guess_type(self.filename)[0]

    @property
    def image(self):
        """Return an eventual cover image"""
        directory = os.path.split(self.filename)[0]
        image_files = []

        for fn in os.listdir(directory):
            ext = os.path.splitext(fn)[1]
            if ext.lower() in BOOK_COVER_EXTENSIONS:
                image_files.append(fn)

        if len(image_files) > 0:
            abs_path_image = os.path.join(directory, image_files[0])
            return self._to_url(abs_path_image)
        else:
            return None

    @property
    def duration(self):
        """Return episode duration in seconds"""
        try:
            audio = mutagen.File(self.filename)
            if audio and hasattr(audio, "info") and hasattr(audio.info, "length"):
                return int(audio.info.length)
            return None
        except Exception as err:
            logger.warning(
                "Could not get duration of file {filename} due to: {err!r}".format(
                    filename=self.filename, err=err
                )
            )
            return None

    @property
    def duration_formatted(self):
        """Return formatted duration as HH:MM:SS"""
        seconds = self.duration
        if seconds is None:
            return "Unknown"

        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
        else:
            return "{:02d}:{:02d}".format(minutes, seconds)


class Channel(object):
    """Podcast channel"""

    def __init__(self, root_dir, root_url, host, port, title, link, debug=False, folder_path=None, title_mode='default', force_order_by_name=False):
        self.root_dir = root_dir or os.getcwd()
        self.root_url = root_url
        self.host = host
        self.port = int(port)
        # Set link to specific RSS feed if folder_path is provided, otherwise to web interface
        if folder_path:
            self.link = link or self.root_url + "/feed/" + quote(folder_path, safe="")
        else:
            self.link = link or self.root_url
        self.folder_path = folder_path  # Optional: restrict to specific subfolder
        self.title = title or os.path.basename(
            os.path.abspath(self.root_dir.rstrip('/')))
        self.description = 'Feed generated by <a href="%s">Podcats</a>.' % __url__
        self.debug = debug
        self.title_mode = title_mode
        self.force_order_by_name = force_order_by_name

    def __iter__(self):
        # If folder_path is specified, only walk that specific subfolder
        if self.folder_path:
            walk_dir = os.path.join(self.root_dir, self.folder_path)
            if not os.path.exists(walk_dir):
                return
        else:
            walk_dir = self.root_dir

        for root, _, files in os.walk(walk_dir):
            relative_dir = root[len(self.root_dir):]

            # If folder_path is set, only include files directly in that folder (not subfolders)
            if self.folder_path:
                # Check if we're in the target folder (not a subfolder of it)
                if root != walk_dir:
                    continue

            for fn in files:
                filepath = os.path.join(root, fn)
                if is_audio_file(filepath):
                    yield Episode(filepath, relative_dir, self.root_url, self.title_mode, self.force_order_by_name)

    def as_xml(self):
        """Return channel XML with all episode items"""
        template = jinja2_env.get_template('feed.xml')

        # Get all episodes and sort them
        episodes = sorted(self)

        # Get the first episode's image URL if available
        image_url = None
        if episodes:
            image_url = episodes[0].image

        return template.render(
            title=escape(self.title),
            description=escape(self.description),
            link=escape(self.link),
            image_url=image_url,
            items=u''.join(episode.as_xml() for episode in episodes)
        ).strip()

    def as_html(self, index_url=None):
        """Return channel HTML with all episode items"""
        template = jinja2_env.get_template('feed.html')
        return template.render(
            title=escape(self.title),
            description=self.description,
            link=escape(self.link),
            items=u''.join(episode.as_html() for episode in sorted(self)),
            index_url=index_url,
        ).strip().encode("utf-8", "surrogateescape")


class FolderChannel(object):
    """Manages multiple podcast channels, one per subfolder"""

    def __init__(
        self,
        root_dir,
        root_url,
        host,
        port,
        title,
        link,
        debug=False,
        title_mode='default',
        force_order_by_name=False,
    ):
        self.root_dir = root_dir or os.getcwd()
        self.root_url = root_url
        self.host = host
        self.port = int(port)
        self.title = title
        self.link = link
        self.debug = debug
        self.title_mode = title_mode
        self.force_order_by_name = force_order_by_name
        self._folders = None

    def get_folders(self):
        """Get list of immediate subfolders that contain audio files"""
        if self._folders is not None:
            return self._folders

        folders = []
        try:
            for item in os.listdir(self.root_dir):
                item_path = os.path.join(self.root_dir, item)
                if os.path.isdir(item_path):
                    # Check if folder contains audio files
                    has_audio = False
                    for fn in os.listdir(item_path):
                        filepath = os.path.join(item_path, fn)
                        if os.path.isfile(filepath) and is_audio_file(filepath):
                            has_audio = True
                            break
                    if has_audio:
                        folders.append(item)
        except OSError:
            pass

        self._folders = sorted(folders)
        return self._folders

    def get_channel(self, folder_name):
        """Get a Channel instance for a specific folder"""
        if folder_name not in self.get_folders():
            return None

        folder_title = self.title or folder_name
        return Channel(
            root_dir=self.root_dir,
            root_url=self.root_url,
            host=self.host,
            port=self.port,
            title=folder_title,
            link=self.link,
            debug=self.debug,
            folder_path=folder_name,
            title_mode=self.title_mode,
            force_order_by_name=self.force_order_by_name,
        )

    def as_html_index(self):
        """Return HTML index page listing all folder feeds"""
        template = jinja2_env.get_template('folder_index.html')
        folders = self.get_folders()

        # Build folder info list
        folder_info = []
        for folder in folders:
            channel = self.get_channel(folder)
            episodes = list(channel)
            image_url = None
            if episodes:
                # Sort episodes to get the first one consistently
                sorted_episodes = sorted(episodes)
                image_url = sorted_episodes[0].image
            folder_info.append(
                {
                    'name': folder,
                    'url': '/feed/' + quote(folder, safe=''),
                    'web_url': '/web/' + quote(folder, safe=''),
                    'rss_full_url': self.root_url + '/feed/' + quote(folder, safe=''),
                    'episode_count': len(episodes),
                    'image_url': image_url,
                }
            )

        return (
            template.render(
                title=escape(self.title or 'Podcast Feeds'),
                folders=folder_info,
                root_url=self.root_url,
            )
            .strip()
            .encode('utf-8', 'surrogateescape')
        )


def serve(channel):
    """Serve podcast channel and episodes over HTTP"""
    server = Flask(
        __name__,
        static_folder=channel.root_dir,
        static_url_path=STATIC_PATH,
    )
    server.route('/')(
        lambda: Response(
            channel.as_xml(),
            content_type='application/xml; charset=utf-8')
    )
    server.add_url_rule(
        WEB_PATH,
        view_func=channel.as_html,
        methods=['GET'],
    )
    server.run(host=channel.host, port=channel.port, debug=channel.debug, threaded=True)


def serve_folder_feeds(folder_channel):
    """Serve multiple podcast feeds, one per subfolder"""
    server = Flask(
        __name__,
        static_folder=folder_channel.root_dir,
        static_url_path=STATIC_PATH,
    )

    # Root URL serves the index page
    @server.route('/{web_path}'.format(web_path=WEB_PATH))
    def index():
        return folder_channel.as_html_index()

    # RSS feed for a specific folder
    @server.route('/feed/<path:folder_name>')
    def folder_feed(folder_name):
        folder_name = unquote(folder_name)
        channel = folder_channel.get_channel(folder_name)
        if channel is None:
            return Response('Folder not found', status=404)
        return Response(channel.as_xml(), content_type='application/xml; charset=utf-8')

    # Web interface for a specific folder
    @server.route('/{web_path}/<path:folder_name>'.format(web_path=WEB_PATH))
    def folder_web(folder_name):
        folder_name = unquote(folder_name)
        channel = folder_channel.get_channel(folder_name)
        if channel is None:
            return Response('Folder not found', status=404)
        return channel.as_html(index_url=WEB_PATH)

    server.run(
        host=folder_channel.host,
        port=folder_channel.port,
        debug=folder_channel.debug,
        threaded=True,
    )


def main():
    """Main function"""
    args = parser.parse_args()
    
    # Validate mutually exclusive title options
    if args.title_from_id3 and args.title_from_filename:
        parser.error("--title-from-id3 and --title-from-filename are mutually exclusive")
    
    # Determine title mode
    if args.title_from_id3:
        title_mode = 'id3'
    elif args.title_from_filename:
        title_mode = 'filename'
    else:
        title_mode = 'default'
    
    # Default server URL for binding and display
    url = 'http://' + args.host + ':' + args.port

    # Use public URL if provided, otherwise use server URL
    root_url = args.public_url if args.public_url else url

    if not args.folder_feeds:
        # Original single-feed mode
        channel = Channel(
            root_dir=path.abspath(args.directory),
            root_url=root_url,  # Use the public URL for links if provided
            host=args.host,  # Still use host/port for server binding
            port=args.port,
            title=args.title,
            link=args.link,
            debug=args.debug,
            title_mode=title_mode,
            force_order_by_name=args.force_order_by_name,
        )
        if args.action == 'generate':
            print(channel.as_xml())
        elif args.action == 'generate_html':
            print(channel.as_html())
        else:
            print('Welcome to the Podcats web server!')
            print('\nListening on http://{}:{}'.format(args.host, args.port))

            if args.public_url:
                print('Using public URL: {}'.format(args.public_url))

            print('\nYour podcast feed is available at:\n')
            print('\t' + channel.root_url + '\n')
            print('The web interface is available at\n')
            print('\t{url}{web_path}\n'.format(url=root_url, web_path=WEB_PATH))
            serve(channel)
    else:
        # Handle folder-feeds mode
        folder_channel = FolderChannel(
            root_dir=path.abspath(args.directory),
            root_url=root_url,
            host=args.host,
            port=args.port,
            title=args.title,
            link=args.link,
            debug=args.debug,
            title_mode=title_mode,
            force_order_by_name=args.force_order_by_name,
        )

        if args.action == 'generate':
            # Generate all feeds
            folders = folder_channel.get_folders()
            if not folders:
                print('No subfolders with audio files found.')
                return
            for folder in folders:
                print(f'# Feed for folder: {folder}')
                print(f'# URL: /feed/{quote(folder, safe="")}')
                channel = folder_channel.get_channel(folder)
                print(channel.as_xml())
                print('\n')
        elif args.action == 'generate_html':
            # Generate index page
            print(folder_channel.as_html_index())
        else:
            # Serve mode
            folders = folder_channel.get_folders()
            print('Welcome to the Podcats web server (folder-feeds mode)!')
            print('\nListening on http://{}:{}'.format(args.host, args.port))

            if args.public_url:
                print('Using public URL: {}'.format(args.public_url))

            print('\nFound {} folder(s) with audio files:'.format(len(folders)))
            for folder in folders:
                print('  - {}'.format(folder))
                print('    RSS: {}/feed/{}'.format(root_url, quote(folder, safe='')))
                print('    Web: {}{}/{}'.format(root_url, WEB_PATH, quote(folder, safe='')))

            print('\nIndex page available at: {}{}\n'.format(root_url, WEB_PATH))
            serve_folder_feeds(folder_channel)


parser = argparse.ArgumentParser(
    description='Podcats: podcast feed generator and server <%s>.' % __url__
)
parser.add_argument(
    '--host',
    default='localhost',
    help='listen hostname or IP address'
)
parser.add_argument(
    '--port',
    default='5000',
    help='listen tcp port number'
)
parser.add_argument(
    '--public-url',
    help='public-facing URL for links in the feed (useful when behind a reverse proxy)'
)
parser.add_argument(
    'action',
    metavar='COMMAND',
    choices=['generate', 'generate_html', 'serve'],
    help='`generate` the RSS feed to the terminal, or'
         '`serve` the generated RSS as well as audio files'
         ' via the built-in web server'
)
parser.add_argument(
    'directory',
    metavar='DIRECTORY',
    help='path to a directory with episode audio files',
)
parser.add_argument(
    '--debug',
    action="store_true",
    help='Serve with debug mode on'
)
parser.add_argument('--title', help='optional feed title')
parser.add_argument('--link', help='optional feed link')
parser.add_argument(
    '--force-order-by-name',
    action="store_true",
    help='Force ordering episodes by filename instead of by date '
         'by creating an artificial timestamp based on the last '
         'number found in the filename.'
)
parser.add_argument(
    '--folder-feeds',
    action='store_true',
    help='Generate separate RSS feeds for each immediate subfolder '
    'instead of one combined feed for all files',
)
parser.add_argument(
    '--title-from-id3',
    action='store_true',
    help='Use ID3 tag for episode title instead of filename+tag concatenation. '
         'Falls back to filename if no ID3 title tag exists.',
)
parser.add_argument(
    '--title-from-filename',
    action='store_true',
    help='Use only the filename (without extension) for episode titles, ignoring ID3 tags.',
)


if __name__ == '__main__':
    main()

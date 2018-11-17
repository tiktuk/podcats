"""
Podcats is a podcast feed generator and a server.

It generates RSS feeds for podcast episodes from local audio files and,
optionally, exposes the feed and as well as the episode file via
a built-in web server so that they can be imported into iTunes
or another podcast client.

"""
import os
import re
import time
import argparse
import mimetypes
from email.utils import formatdate
from xml.sax.saxutils import escape, quoteattr

try:
    from urllib.request import pathname2url
except ImportError:
    # For python 2
    from urllib import pathname2url

import mutagen
import humanize
from mutagen.id3 import ID3
from flask import Flask, Response


__version__ = '0.5.0'
__licence__ = 'BSD'
__author__ = 'Jakub Roztocil'
__url__ = 'https://github.com/jakubroztocil/podcats'


FEED_TEMPLATE_XML = """
<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
    <channel>
        <title>{title}</title>
        <description>{description}</description>
        <link>{link}</link>
        {items}
    </channel>
</rss>
"""


FEED_TEMPLATE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta http-equiv="x-ua-compatible" content="ie=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>{title}</title>
</head>
    <body>
        <h1>{title}</h1>
        <p>{description}. RSS feed at <a href="{link}">{link}</a>.</p>
        {items}
    </body>
</html>
"""


EPISODE_TEMPLATE_XML = """
    <item>
        <title>{title}</title>
        <enclosure url={url} type="{mimetype}" length="{length}" />
        <guid>{guid}</guid>
        <pubDate>{date}</pubDate>
    </item>
"""


EPISODE_TEMPLATE_HTML = """
    <article>
        <h2><a href="{url}">{title}</a></h2>
        <p>
            <ul>
                <li>Directory: {directory}</li>
                <li>File: {filename}</li>
                <li>Date: {date}</li>
                <li>Size: {length}</li>
                <li>Mimetype: {mimetype}</li>
            </ul>
            <audio controls>
                <source src="{url}"/>
            </audio>
        </p>
    </article>
"""

WEB_PATH = 'web'


class Episode(object):
    """Podcast episode"""

    def __init__(self, filename, url):
        self.filename = filename
        self.url = url
        self.length = os.path.getsize(filename)
        self.tags = mutagen.File(self.filename, easy=True)
        try:
            self.id3 = ID3(self.filename)
        except:
            self.id3 = None

    def __lt__(self, other):
        return self.date < other.date

    def __gt__(self, other):
        return self.date > other.date

    def __cmp__(self, other):
        a, b = self.date, other.date
        return (a > b) - (a < b)  # Python3 cmp() equivalent

    def as_xml(self):
        """Return episode item XML."""
        return EPISODE_TEMPLATE_XML.format(
            title=escape(self.title),
            url=quoteattr(self.url),
            guid=escape(self.url),
            mimetype=self.mimetype,
            length=self.length,
            date=formatdate(self.date)
        )

    def as_html(self):
        """Return episode item html."""
        filename = os.path.basename(self.filename)
        directory = os.path.split(os.path.dirname(self.filename))[-1]
        return EPISODE_TEMPLATE_HTML.format(
            title=escape(self.title),
            url=self.url,
            filename=filename,
            directory=directory,
            mimetype=self.mimetype,
            length=humanize.naturalsize(self.length),
            date=formatdate(self.date)
        )

    def get_tag(self, name):
        """Return episode file tag info"""
        try:
            return self.tags[name][0]
        except (KeyError, IndexError):
            pass

    @property
    def title(self):
        """Return episode title"""
        text = os.path.splitext(os.path.basename(self.filename))[0]
        if self.id3 is not None:
            val = self.id3.getall('TIT2')
            if len(val) > 0:
                text += str(val[0])
            val = self.id3.getall('COMM')
            if len(val) > 0:
                text += ' ' + str(val[0])
        return text

    @property
    def date(self):
        """Return episode date as unix timestamp"""
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
        """Return file mimetype name."""
        if self.filename.endswith('m4b'):
            return 'audio/x-m4b'
        else:
            return mimetypes.guess_type(self.filename)[0]


class Channel(object):
    """Podcast channel"""

    def __init__(self, root_dir, root_url, host, port, title, link, debug=False):
        self.root_dir = root_dir or os.getcwd()
        self.root_url = root_url
        self.host = host
        self.port = int(port)
        self.link = link or self.root_url
        self.title = title or os.path.basename(self.root_dir.rstrip('/'))
        self.description = 'Feed generated by Podcats'
        self.debug = debug

    def __iter__(self):
        for root, _, files in os.walk(self.root_dir):
            relative_dir = root[len(self.root_dir) + 1:]
            for fn in files:
                filepath = os.path.join(root, fn)
                mimetype = mimetypes.guess_type(filepath)[0]
                if mimetype and 'audio' in mimetype or filepath.endswith('m4b'):
                    path = '/static/' + relative_dir + '/' + fn
                    path = re.sub(r'//', '/', path)
                    url = self.root_url + pathname2url(path)
                    yield Episode(filepath, url)

    def as_xml(self):
        """Return channel XML with all episode items"""
        return FEED_TEMPLATE_XML.format(
            title=escape(self.title),
            description=escape(self.description),
            link=escape(self.link),
            items=u''.join(episode.as_xml() for episode in sorted(self))
        ).strip()

    def as_html(self):
        """Return channel HTML with all episode items"""
        return FEED_TEMPLATE_HTML.format(
            title=escape(self.title),
            description=escape(self.description),
            link=escape(self.link),
            items=u''.join(episode.as_html() for episode in sorted(self)),
        ).strip()


def serve(channel):
    """Serve podcast channel and episodes over HTTP"""
    server = Flask(
        __name__,
        static_folder=channel.root_dir,
        static_url_path='/static',
    )
    server.route('/')(
        lambda: Response(
            channel.as_xml(),
            content_type='application/xml; charset=utf-8')
    )
    server.add_url_rule(
        '/{web_path}'.format(web_path=WEB_PATH),
        view_func=channel.as_html,
        methods=['GET'],
    )
    server.run(host=channel.host, port=channel.port, debug=channel.debug, threaded=True)


def main():
    """Main function"""
    args = parser.parse_args()
    url = 'http://' + args.host + ':' + args.port
    channel = Channel(
        root_dir=args.directory,
        root_url=url,
        host=args.host,
        port=args.port,
        title=args.title,
        link=args.link,
        debug=args.debug,
    )
    if args.action == 'generate':
        print(channel.as_xml())
    elif args.action == 'generate_html':
        print(channel.as_html())
    else:
        print('Welcome to the Podcats web server!')
        print('\nYour podcast feed is available at:\n')
        print('\t' + channel.root_url + '\n')
        print('The web interface is available at\n')
        print('\t{url}/{web_path}\n'.format(url=url, web_path=WEB_PATH))
        serve(channel)


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


if __name__ == '__main__':
    main()

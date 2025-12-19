Podcats
#######


.. image:: https://github.com/jakubroztocil/podcats/workflows/Build/badge.svg
    :target: https://github.com/jakubroztocil/podcats/actions

Podcats generates RSS feeds for podcast episodes from local audio files and,
optionally, exposes both the feed and episodes via a built in web server,
so that they can be conveniently imported into iTunes, Overcast or another
podcast client.


Installation
============
::

    $ pip install podcats


Usage
=====

Generate a podcast RSS from audio files stored in `my/offline/podcasts`::

    $ podcats generate my/offline/podcasts


Generate & serve the feed as well as the files at http://localhost:5000. ::

    $ podcats serve my/offline/podcasts

A web interface is available at http://localhost:5000/web.

You can also generate the html for the web interface. ::

    $ podcats generate_html my/offline/podcasts

Serve podcasts with a feed per subfolder in `../../audiobooks/`, titles from filenames, artificial publishing dates and links generate with a public url of `http://example.net`::

    $ podcats serve --folder-feeds --title-from-filename --force-order-by-name --host localhost --port 5000 --public-url http://example.net ../../audiobooks/


CLI options
===========

Command format::

    $ podcats [OPTIONS] COMMAND DIRECTORY

Positional arguments:

- **COMMAND**
  One of:

  - ``generate``: print RSS XML to stdout
  - ``generate_html``: print HTML for the web interface to stdout
  - ``serve``: start the built-in web server

- **DIRECTORY**
  Path to a directory containing episode audio files.

Options:

- ``--host``
  Listen hostname or IP address (default: ``localhost``).

- ``--port``
  Listen TCP port number (default: ``5000``).

- ``--public-url``
  Public-facing base URL to embed into generated feed links (useful when
  behind a reverse proxy).

- ``--debug``
  Serve with debug mode on.

- ``--title``
  Optional feed title.

- ``--link``
  Optional feed link.

- ``--force-order-by-name``
  Create artificial rss publishing dates based on sort order gathered by filename
  instead of file modification date. This is useful because many podcast players
  primarily sort episodes by publication date; if your files lack reliable dates/metadata,
  the episode order can appear scrambled unless a deterministic filename-based order is used.

- ``--folder-feeds``
  Generate separate RSS feeds for each immediate subfolder instead of one
  combined feed for all files.

- ``--title-from-id3``
  Use the ID3 title tag for episode titles. Falls back to filename if no ID3
  title tag exists.

- ``--title-from-filename``
  Use only the filename (without extension) for episode titles, ignoring ID3
  tags.

  ``--title-from-id3`` and ``--title-from-filename`` are mutually exclusive.

Contact
=======

Jakub Roztočil

* https://github.com/jakubroztocil
* https://twitter.com/jakubroztocil
* https://roztocil.co

Changelog
=========

0.6.3 (2019-02-03)
------------------

* Fixed relative paths.


0.6.2 (2018-11-25)
------------------

* Fixed missing templates in PyPI package.


0.6.1 (2018-11-20)
------------------

* Find and show eventual book covers in web interface (@tiktuk)


0.6.0 (2018-11-20)
------------------

* Added a web interface (@tiktuk)
* Support m4b-files (@tiktuk)
* Added ``--debug`` flag (@tiktuk)
* Feed now validates against RSS spec (@tiktuk)


0.5.0 (2017-02-26)
------------------

* Fixed ``setup.py`` for Python 3 (@ymomoi)


0.3.0 (2017-02-23)
------------------

* Added Python 3 support
* Improved episode ID tag title extraction (@ymomoi)
* Replaced ``--url`` with ``--host`` and ``--port`` (@ymomoi)

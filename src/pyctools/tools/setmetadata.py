#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014  Jim Easterbrook  jim@jim-easterbrook.me.uk
#
#  This program is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see
#  <http://www.gnu.org/licenses/>.

"""Set metadata.

Sets values in an image or video file's metadata sidecar, which is
created if it doesn't already exist.

Each value has a tag (or name). This is a single word which is
expanded to the custom namespace 'Xmp.pyctools.tag'.

Useful tags include: xlen, ylen and fourcc

"""

from __future__ import print_function

import argparse
import logging
import sys

from pyctools.core import Metadata

def main():
    # get command args
    parser = argparse.ArgumentParser(description='Set metadata values.')
    parser.add_argument('path', help='image or video file path')
    parser.add_argument(
        '-t', '--tag', metavar=('name', 'value'), action='append', nargs=2,
        help='Exiv2 tag name and value')
    args = parser.parse_args()
    if len(args.tag) < 1:
        return 0
    # open metadata (if it exists)
    md = Metadata().from_file(args.path, create=True)
    # set tag(s)
    for tag, value in args.tag:
        print(tag, value)
        md.set(tag, value)
    # save metadata
    md.to_file(args.path)
    return 0

if __name__ == '__main__':
    sys.exit(main())

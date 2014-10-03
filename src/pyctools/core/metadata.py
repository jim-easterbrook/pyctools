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

"""Pyctools "Metadata" class.

"""

__all__ = ['Metadata']

try:
    import pgi
    pgi.install_as_gi()
except ImportError:
    pass
from gi.repository import GObject, GExiv2

class Metadata(object):
    def __init__(self):
        self.md = GExiv2.Metadata()

    def from_file(self, path, create=False):
        xmp_path = path + '.xmp'
        try:
            self.md.open_path(xmp_path)
            return self
        except GObject.GError:
            pass
        try:
            self.md.open_path(path)
            return self
        except GObject.GError:
            pass
        if create:
            # create empty XMP
            with open(xmp_path, 'w') as of:
                of.write('<x:xmpmeta x:xmptk="XMP Core 4.4.0-Exiv2" ')
                of.write('xmlns:x="adobe:ns:meta/">\n</x:xmpmeta>')
            self.md.open_path(xmp_path)
        return self

    def to_file(self, path):
        xmp_path = path + '.xmp'
        self.md.save_file(xmp_path)
    
    def copy(self, other):
        return self

    def image_size(self):
        xlen = None
        ylen = None
        for tag in ('Exif.Image.ImageWidth', 'Xmp.tiff.ImageWidth'):
            if self.md.has_tag(tag):
                xlen = self.md.get_tag_long(tag)
                break
        for tag in ('Exif.Image.ImageLength', 'Xmp.tiff.ImageLength'):
            if self.md.has_tag(tag):
                ylen = self.md.get_tag_long(tag)
                break
        if xlen and ylen:
            return xlen, ylen
        raise RuntimeError('Metadata does not have image dimensions')

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
        self.data = {}
        self.comment = None
        self.set('audit', '')

    def from_file(self, path):
        for xmp_path in (path + '.xmp', path):
            md = GExiv2.Metadata()
            try:
                md.open_path(xmp_path)
            except GObject.GError:
                continue
            for tag in (md.get_exif_tags() +
                        md.get_iptc_tags() + md.get_xmp_tags()):
                if md.get_tag_type(tag) in ('XmpBag', 'XmpSeq'):
                    self.data[tag] = md.get_tag_multiple(tag)
                else:
                    self.data[tag] = md.get_tag_string(tag)
            self.comment = md.get_comment()
            break
        return self

    def to_file(self, path):
        xmp_path = path + '.xmp'
        # create empty XMP
        with open(xmp_path, 'w') as of:
            of.write('<x:xmpmeta x:xmptk="XMP Core 4.4.0-Exiv2" ')
            of.write('xmlns:x="adobe:ns:meta/">\n</x:xmpmeta>')
        # open empty XMP
        md = GExiv2.Metadata()
        md.open_path(xmp_path)
        # add our namespace
        md.register_xmp_namespace(
            'https://github.com/jim-easterbrook/pyctools', 'pyctools')
        # copy metadata
        for tag, value in self.data.items():
            if md.get_tag_type(tag) in ('XmpBag', 'XmpSeq'):
                md.set_tag_multiple(tag, value)
            else:
                md.set_tag_string(tag, value)
        if self.comment is not None:
            md.set_comment(self.comment)
        # save file
        md.save_file(xmp_path)
    
    def copy(self, other):
        # copy from other to self
        self.data.update(other.data)
        if other.comment is not None:
            self.comment = other.comment
        return self

    def image_size(self):
        xlen = None
        ylen = None
        for tag in ('Xmp.pyctools.xlen', 'Exif.Photo.PixelXDimension',
                    'Exif.Image.ImageWidth', 'Xmp.tiff.ImageWidth'):
            if tag in self.data:
                xlen = int(self.data[tag])
                break
        for tag in ('Xmp.pyctools.ylen', 'Exif.Photo.PixelYDimension',
                    'Exif.Image.ImageLength', 'Xmp.tiff.ImageLength'):
            if tag in self.data:
                ylen = int(self.data[tag])
                break
        if xlen and ylen:
            return xlen, ylen
        raise RuntimeError('Metadata does not have image dimensions')

    def get(self, tag):
        full_tag = 'Xmp.pyctools.' + tag
        return self.data[full_tag]

    def set(self, tag, value):
        full_tag = 'Xmp.pyctools.' + tag
        self.data[full_tag] = value

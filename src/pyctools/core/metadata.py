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

"""Pyctools "Metadata" handler.

"""

__all__ = ['Metadata']
__docformat__ = 'restructuredtext en'

try:
    import pgi
    pgi.install_as_gi()
except ImportError:
    pass
from gi.repository import GObject, GExiv2

class Metadata(object):
    """Store "data about the data" in a :py:class:`~.frame.Frame`.

    This container stores information about an image or video sequence
    that is not the actual image data. The main use of this is the
    "audit trail". Each Pyctools component extends the audit trail
    with a short description of what it does, creating a detailed
    record of the processing. This can be useful in working out what
    went wrong (or right!) in some cases.

    Many image file formats (such as JPEG) allow storage of metadata
    within the image file, but in Pyctools the metadata is always
    stored in a separate "sidecar" file. This allows the use of any
    image/video file format and, because the metadata is stored in XMP
    text format, the sidecar can be read with any text editor.

    "Raw" video files, often used to store YUV, have their image
    dimensions and "`fourcc <http://www.fourcc.org/>`_" format stored
    in a metadata file. The
    :py:mod:`pyctools-setmetadata<pyctools.tools.setmetadata>` tool
    can be used to create or modify the metadata file if this
    information is missing.

    """
    def __init__(self):
        self.data = {}
        self.comment = None
        self.set('audit', '')

    def from_file(self, path):
        """Read metadata from an XMP sidecar file or, if there is no
        sidecar, from the image/video file (if it has metadata).

        Returns the :py:class:`Metadata` object, allowing convenient
        code like this::

            md = Metadata().from_file(path)

        :param str path: The image/video file path name.

        :rtype: :py:class:`Metadata`

        """
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
        """Write metadata to an XMP sidecar file.

        :param str path: The image/video file path name.

        """
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
        """Copy metadata from another :py:class:`Metadata` object.

        Returns the :py:class:`Metadata` object, allowing convenient
        code like this::

            md = Metadata().copy(other_md)

        :param Metadata other: The metadata to copy.

        :rtype: :py:class:`Metadata`

        """
        # copy from other to self
        self.data.update(other.data)
        if other.comment is not None:
            self.comment = other.comment
        return self

    def image_size(self):
        """Get image dimensions from metadata.

        This is primarily used by the
        :py:class:`~pyctools.components.io.rawfilereader.RawFileReader`
        component, as raw video files don't have a header in which to
        store the dimensions.

        :returns: width, height.

        :rtype: :py:class:`int`, :py:class:`int`

        """
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
        """Get a metadata value.

        Each metadata value is referenced by a ``tag`` -- a short
        string such as ``'xlen'`` or ``'audit'``. In the sidecar file
        these tag names are prepended with ``'Xmp.pyctools.'``, which
        corresponds to a custom namespace in the XML file.

        :param str tag: The tag name.

        :returns: The metadata value associated with ``tag``.

        :rtype: :py:class:`str`

        """
        full_tag = 'Xmp.pyctools.' + tag
        return self.data[full_tag]

    def set(self, tag, value):
        """Set a metadata value.

        Each metadata value is referenced by a ``tag`` -- a short
        string such as ``'xlen'`` or ``'audit'``. In the sidecar file
        these tag names are prepended with ``'Xmp.pyctools.'``, which
        corresponds to a custom namespace in the XML file.

        :param str tag: The tag name.

        :param str value: The metadata value.

        """
        full_tag = 'Xmp.pyctools.' + tag
        self.data[full_tag] = value

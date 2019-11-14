#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-19  Pyctools contributors
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

__all__ = ['Frame', 'Metadata']
__docformat__ = 'restructuredtext en'

import os

try:
    import pgi
    pgi.install_as_gi()
except ImportError:
    pass
import gi
for gexiv2_vsn in ('0.10', '0.4'):
    try:
        gi.require_version('GExiv2', gexiv2_vsn)
        break
    except ValueError:
        pass
from gi.repository import GExiv2, GLib
import numpy
import PIL.Image

from pyctools.core.types import pt_float

class Frame(object):
    """Container for a single image or frame of video.

    This is a fairly free-form container (to which you can add other
    data), but every :py:class:`Frame` object must have:

    * a frame number
    * a data item
    * a type description string, such as "RGB"
    * a :py:class:`Metadata` item

    The data item can be a :py:class:`numpy:numpy.ndarray` or
    :py:mod:`PIL:PIL.Image` object. In most instances a
    :py:class:`numpy:numpy.ndarray` should have 3 dimensions: line,
    pixel, colour component.

    """
    def __init__(self, **kwds):
        super(Frame, self).__init__(**kwds)
        self.frame_no = -1
        self.data = None
        self.type = 'empty'
        self.metadata = Metadata()

    def initialise(self, other):
        """Initialise a :py:class:`Frame` from another :py:class:`Frame`.

        Copies the metadata and (a reference to) the data from
        :py:obj:`other`. Note that the data is not actually copied --
        you must make a copy of the data before changing it.

        :param Frame other: The frame to copy.

        """
        self.frame_no = other.frame_no
        self.data = other.data
        self.type = other.type
        self.metadata.copy(other.metadata)

    def size(self):
        """Return image dimensions (height, width)"""
        if isinstance(self.data, numpy.ndarray):
            h, w = self.data.shape[:2]
        elif isinstance(self.data, PIL.Image.Image):
            w, h = self.data.size()
        else:
            raise RuntimeError(
                'Cannot get size of "%s"' % self.data.__class__.__name__)
        return h, w

    def as_numpy(self, dtype=None, copy=False):
        """Get image data in :py:class:`numpy:numpy.ndarray` form.

        Note that if the image data is already in the correct format
        this can be a null operation.

        When converting to limited range types (``numpy.uint8``,
        ``numpy.uint16``) the data is clipped (limited) to the range.

        :keyword numpy.dtype dtype: What
            :py:class:`~numpy:numpy.dtype` the data should be in, e.g.
            ``numpy.float32``. If ``dtype`` is ``None`` then no
            conversion will be done.

        :keyword bool copy: Forces a copy of the data to be made, even
            if it is already an :py:class:`numpy:numpy.ndarray` with the
            requested dtype.

        :return: The image data as :py:class:`numpy:numpy.ndarray`.

        :rtype: :py:class:`numpy.ndarray`

        """
        if isinstance(self.data, numpy.ndarray):
            result = self.data
        elif isinstance(self.data, PIL.Image.Image):
            if self.data.mode == 'P':
                data = self.data.convert()
            else:
                data = self.data
            if data.mode == 'F':
                result = numpy.array(data, dtype=numpy.float32)
            elif data.mode == 'I':
                result = numpy.array(data, dtype=numpy.int32)
            elif dtype is not None:
                result = numpy.array(data, dtype=dtype)
            else:
                result = numpy.array(data, dtype=pt_float)
            copy = False
        else:
            raise RuntimeError(
                'Cannot convert "%s" to numpy' % self.data.__class__.__name__)
        if dtype is not None and result.dtype != dtype:
            if dtype == numpy.uint8:
                result = result.clip(0, 255)
            elif dtype == numpy.uint16:
                result = result.clip(0, 2**16 - 1)
            result = result.astype(dtype)
            copy = False
        if copy:
            result = result.copy()
        return result

    def as_PIL(self):
        """Get image data in :py:mod:`PIL:PIL.Image` form.

        Note that if the image data is already in the correct format
        this is a null operation.

        :return: The image data as :py:mod:`PIL:PIL.Image`.

        :rtype: :py:mod:`PIL:PIL.Image`

        """
        if isinstance(self.data, numpy.ndarray):
            if self.data.dtype == numpy.uint8:
                result = PIL.Image.fromarray(self.data)
            else:
                result = PIL.Image.fromarray(
                    self.data.clip(0, 255).astype(numpy.uint8))
        elif isinstance(self.data, PIL.Image.Image):
            result = self.data
        else:
            raise RuntimeError(
                'Cannot convert "%s" to PIL' % self.data.__class__.__name__)
        return result


class Metadata(object):
    """Store "data about the data" in a :py:class:`Frame`.

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
    def __init__(self, **kwds):
        super(Metadata, self).__init__(**kwds)
        self.data = {}
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
            except GLib.GError:
                continue
            tags = md.get_exif_tags() + md.get_iptc_tags() + md.get_xmp_tags()
            for tag in tags:
                if tag.startswith('Exif.Thumbnail'):
                    continue
                if tag.startswith('Xmp.xmp.Thumbnails'):
                    continue
                count = tags.count(tag)
                if count > 1 or md.get_tag_type(tag) in ('XmpBag', 'XmpSeq'):
                    self.data[tag] = md.get_tag_multiple(tag)
                else:
                    self.data[tag] = md.get_tag_string(tag)
                if tag == 'Xmp.pyctools.audit':
                    self.data[tag] = self.data[tag].strip()
            break
        return self

    def to_file(self, path, thumbnail=None):
        """Write metadata to an image, video or XMP sidecar file.

        :param str path: The image/video file path name.

        """
        xmp_path = path + '.xmp'
        # remove any existing XMP file
        if os.path.exists(xmp_path):
            os.unlink(xmp_path)
        # attempt to open image/video file for metadata
        md_path = path
        md = GExiv2.Metadata()
        try:
            md.open_path(md_path)
            if thumbnail:
                md.set_exif_thumbnail_from_buffer(thumbnail)
        except GLib.GError:
            # file type does not support metadata so use XMP sidecar
            md_path = xmp_path
            # create empty XMP file
            with open(md_path, 'w') as of:
                of.write('''<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 4.4.0-Exiv2">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
   xmp:CreatorTool=""/>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>''')
            md = GExiv2.Metadata()
            md.open_path(md_path)
        # add our namespace
        md.register_xmp_namespace(
            'https://github.com/jim-easterbrook/pyctools', 'pyctools')
        # copy metadata
        for tag, value in self.data.items():
            if '[' in tag:
                # XMP structured tag, need to create container
                container = tag.split('[')[0]
                for t in md.get_xmp_tags():
                    if t.startswith(container):
                        # container already exists
                        break
                else:
                    type_ = md.get_tag_type(container)
                    if type_ == 'XmpBag':
                        type_ = GExiv2.StructureType.BAG
                    elif type_ == 'XmpSeq':
                        type_ = GExiv2.StructureType.SEQ
                    else:
                        type_ = GExiv2.StructureType.ALT
                    md.set_xmp_tag_struct(container, type_)
            if tag == 'Xmp.pyctools.audit' and value[0] != '\n':
                value = '\n' + value
            if isinstance(value, list):
                md.set_tag_multiple(tag, value)
            else:
                md.set_tag_string(tag, value)
        # save file
        md.save_file(md_path)

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

    def get(self, tag, default=None):
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
        if full_tag in self.data:
            return self.data[full_tag]
        return default

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

#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-22  Pyctools contributors
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

from datetime import datetime
import os
import threading

import exiv2
import numpy
import PIL.Image

from pyctools.core.types import pt_float


# initialise exiv2
exiv2.LogMsg.setLevel(exiv2.LogMsg.info)
exiv2.XmpParser.initialize()
# register our XMP namespace from main thread
exiv2.XmpProperties.registerNs(
    'https://github.com/jim-easterbrook/pyctools', 'pyctools')

# create a lock to serialise Exiv2 calls
exiv2_lock = threading.Lock()


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

    def set_audit(self, *args, **kwds):
        """See :py:meth:`Metadata.set_audit`."""
        self.metadata.set_audit(*args, **kwds)

    def merge_audit(self, *args, **kwds):
        """See :py:meth:`Metadata.merge_audit`."""
        self.metadata.merge_audit(*args, **kwds)

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
        self.exif_data = exiv2.ExifData()
        self.iptc_data = exiv2.IptcData()
        self.xmp_data = exiv2.XmpData()
        self.set('audit', '')

    def set_audit(self, component, text,
                  with_history=True, with_date=False, with_config=None):
        r"""Set audit trail.

        This is a convenient way to add to the audit trail in a
        "standard" format. The component's module and class names are
        added to the audit trail to record which component did the
        processing. The text should describe what was done and finish
        with a newline, e.g. ``data = FFT(data)\n``. Using the word
        ``data`` to describe single input or output data keeps the audit
        trail consistent. If you are combining two or more inputs you
        can "rename" each one with the :py:meth:`merge_audit` method.

        :param Component component: The component that's processing the
            frame.

        :param str text: Text to be added to the audit trail.

        :param bool with_history: Whether to include the previous audit
            trail.

        :param bool with_date: Whether to include the current date &
            time in the audit trail. This is primarily used when writing
            files.

        :param ConfigParent with_config: Whether to add the component's
            configuration options with
            :py:meth:`.config.ConfigParent.audit_string`.

        """
        if with_history:
            audit = self.get('audit')
        else:
            audit = ''
        audit += text
        if with_config:
            audit += with_config.audit_string()
        if not isinstance(component, type):
            component = component.__class__
        audit += '    <{}.{}>\n'.format(
            component.__module__, component.__name__)
        if with_date:
            audit += '    <{}>\n'.format(datetime.now().isoformat())
        self.set('audit', audit)

    def merge_audit(self, parts):
        r"""Merge audit trails from two or more frames.

        The audit trail from each frame is indented and wrapped with
        braces (``{}``). This makes the audit trail easier to read when
        a component uses two or more inputs.

        The ``parts`` parameter is a :py:class:`dict` of
        :py:class:`Frame` or :py:class:`Metadata` objects. The
        :py:class:`dict` keys are used to label each indented audit trail.

        For example, this Python code::

            out_frame.merge_audit({'Y': Y_frame, 'UV': UV_frame})
            out_frame.set_audit(
                self, 'data = YUVtoRGB(Y, UV)\n    matrix: {}\n'.format(matrix))

        could produce this audit trail:

        .. code-block:: none

            Y = {
                data = test.y
                    path: '/home/jim/Videos/test.y', looping: 'repeat', noaudit: True
                    <pyctools.components.io.videofilereader.VideoFileReader>
                }
            UV = {
                data = test.uv
                    path: '/home/jim/Videos/test.uv', looping: 'repeat', noaudit: True
                    <pyctools.components.io.videofilereader.VideoFileReader>
                }
            data = YUVtoRGB(Y, UV)
                matrix: 601
                <pyctools.components.colourspace.yuvtorgb.YUVtoRGB>

        :param dict parts: The inputs to merge.

        """
        audit = ''
        for name, metadata in parts.items():
            if isinstance(metadata, Frame):
                metadata = metadata.metadata
            audit += name + ' = {\n'
            for line in metadata.get('audit').splitlines():
                audit += '    ' + line + '\n'
            audit += '    }\n'
        self.set('audit', audit)

    def from_file(self, path):
        """Read metadata from an XMP sidecar file or, if there is no
        sidecar, from the image/video file (if it has metadata).

        Returns the :py:class:`Metadata` object, allowing convenient
        code like this::

            md = Metadata().from_file(path)

        :param str path: The image/video file path name.

        :rtype: :py:class:`Metadata`

        """
        xmp_path = path + '.xmp'
        if not os.path.exists(xmp_path):
            xmp_path = path
        try:
            with exiv2_lock:
                im = exiv2.ImageFactory.open(xmp_path)
                im.readMetadata()
        except exiv2.Error as ex:
            print(xmp_path, str(ex))
            return self
        self.exif_data.clear()
        self.iptc_data.clear()
        self.xmp_data.clear()
        for datum in im.exifData():
            self.exif_data.add(datum)
        for datum in im.iptcData():
            self.iptc_data.add(datum)
        for datum in im.xmpData():
            self.xmp_data.add(datum)
        audit = self.get('audit') or ''
        self.set('audit', audit)
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
        writable = True
        md_path = path
        try:
            with exiv2_lock:
                im = exiv2.ImageFactory.open(md_path)
                im.readMetadata()
        except exiv2.Error:
            # file type does not support metadata so use XMP sidecar
            writable = False
        writable = writable and (
            self.exif_data.empty() or im.checkMode(exiv2.MetadataId.Exif) in (
                exiv2.AccessMode.Write, exiv2.AccessMode.ReadWrite))
        writable = writable and (
            self.iptc_data.empty() or im.checkMode(exiv2.MetadataId.Iptc) in (
                exiv2.AccessMode.Write, exiv2.AccessMode.ReadWrite))
        writable = writable and (
            self.xmp_data.empty() or im.checkMode(exiv2.MetadataId.Xmp) in (
                exiv2.AccessMode.Write, exiv2.AccessMode.ReadWrite))
        if not writable:
            md_path = xmp_path
            with exiv2_lock:
                # create empty XMP file
                im = exiv2.ImageFactory.create(exiv2.ImageType.xmp, md_path)
        if thumbnail:
            thumb = exiv2.ExifThumb(self.exif_data)
            thumb.setJpegThumbnail(thumbnail)
        im.setExifData(self.exif_data)
        im.setIptcData(self.iptc_data)
        im.setXmpData(self.xmp_data)
        with exiv2_lock:
            im.writeMetadata()

    def copy(self, other):
        """Copy metadata from another :py:class:`Metadata` object.

        Returns the :py:class:`Metadata` object, allowing convenient
        code like this::

            md = Metadata().copy(other_md)

        :param Metadata other: The metadata to copy.

        :rtype: :py:class:`Metadata`

        """
        # copy from other to self
        for datum in other.exif_data:
            tag = datum.key()
            if tag in self.exif_data:
                del self.exif_data[tag]
            self.exif_data.add(datum)
        for datum in other.iptc_data:
            tag = datum.key()
            if (tag in self.iptc_data
                    and not exiv2.IptcDataSets.dataSetRepeatable(
                                        datum.tag(), datum.record())):
                del self.iptc_data[tag]
            self.iptc_data.add(datum)
        for datum in other.xmp_data:
            tag = datum.key()
            if tag in self.xmp_data:
                del self.xmp_data[tag]
            self.xmp_data.add(datum)
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
        for tag, data in (('Xmp.pyctools.xlen', self.xmp_data),
                          ('Exif.Photo.PixelXDimension', self.exif_data),
                          ('Exif.Image.ImageWidth', self.exif_data),
                          ('Xmp.tiff.ImageWidth', self.xmp_data)):
            if tag in data:
                xlen = data[tag].toLong()
                break
        for tag, data in (('Xmp.pyctools.ylen', self.xmp_data),
                          ('Exif.Photo.PixelYDimension', self.exif_data),
                          ('Exif.Image.ImageLength', self.exif_data),
                          ('Xmp.tiff.ImageLength', self.xmp_data)):
            if tag in data:
                ylen = data[tag].toLong()
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
        if full_tag in self.xmp_data:
            return self.xmp_data[full_tag].toString()
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
        if value is None:
            del self.xmp_data[full_tag]
        else:
            self.xmp_data[full_tag] = str(value)

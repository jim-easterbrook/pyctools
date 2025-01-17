# Pyctools - a picture processing algorithm development kit.
# http://github.com/jim-easterbrook/pyctools
# Copyright (C) 2025  Pyctools contributors
#
# This file is part of Pyctools.
#
# Pyctools is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Pyctools is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pyctools.  If not, see <http://www.gnu.org/licenses/>.

__all__ = []
__docformat__ = 'restructuredtext en'

import os
import sys

if 'sphinx' in sys.modules:
    __all__ += ['SaneScanner']

try:
    import sane
    sane.init()
    sane_types = dict((sane.TYPE_STR[x], x) for x in sane.TYPE_STR)
except ImportError:
    if 'sphinx' in sys.modules:
        sane = None
    else:
        raise

import numpy

from pyctools.core.config import (
    ConfigBool, ConfigEnum, ConfigInt, ConfigIntEnum, ConfigStr)
from pyctools.core.base import Component, InputBuffer
from pyctools.core.frame import Frame


class ScannerFactory(object):
    """Ensure scanner is only connected once.

    """

    scanners = {}

    def get_dev(self, name):
        if name not in self.scanners:
            self.scanners[name] = sane.open(name)
        return self.scanners[name]

scanner_factory = ScannerFactory()


class SaneScanner(Component):
    """Base class for scanners using the Linux SANE_ scanner library.

    This component requires the `python-sane`_ package.

    Different scanners have different configuration options, so the
    config documentation is generated dynamically when a scanner class
    derived from :py:class:`SaneScanner` is instantiated. A derived
    class for each connected scanner make and model is defined when the
    :py:mod:`~.sanescanner` module is imported.

    The component has two outputs. ``preview`` is used when the
    scanner's ``preview`` config setting is selected. The scanned image
    is streamed continually, allowing downstream processes such as gamma
    correction to be adjusted for best image quality.

    The main ``output`` is used to send a single scanned image when the
    ``preview`` config setting is not selected. This would typically be
    connected to a similar processing pipeline but ending in an image
    file writer.

    .. _python-sane: https://python-sane.readthedocs.io/
    .. _SANE: http://www.sane-project.org/

    """

    inputs = []
    outputs = ['output', 'preview']     #:

    def initialise(self):
        # create a dummy input to enable process_frame when scan is complete
        self.input_buffer['scan_done'] = InputBuffer(self.new_frame)
        # connect to scanner
        self.dev = scanner_factory.get_dev(self._name)
        # add config to docstring
        self.__doc__ += self.config_doc()
        # initialise config
        for name in self.dev.optlist:
            if not name:
                continue
            option = self.dev[name]
            if option.type in (
                sane_types['TYPE_FIXED'], sane_types['TYPE_BUTTON'],
                sane_types['TYPE_GROUP']) or not option.is_settable():
                continue
            kw = {'has_default': False, 'enabled': option.is_active()}
            if option.type == sane_types['TYPE_BOOL']:
                config_type = ConfigBool
            elif option.type == sane_types['TYPE_INT']:
                config_type = ConfigInt
            else:
                config_type = ConfigStr
            if isinstance(option.constraint, list):
                if config_type == ConfigStr:
                    config_type = ConfigEnum
                else:
                    config_type = ConfigIntEnum
                kw['choices'] = option.constraint
            elif option.constraint:
                kw['min_value'] = option.constraint[0]
                kw['max_value'] = option.constraint[1]
            if kw['enabled']:
                kw['value'] = getattr(self.dev, name)
            self.config[name] = config_type(**kw)

    def config_doc(self):
        # convert scanner options to config doc string
        result = '.. list-table:: Config\n\n'
        for name in self.dev.optlist:
            if not name:
                continue
            option = self.dev[name]
            if option.type in (
                    sane_types['TYPE_FIXED'], sane_types['TYPE_BUTTON'],
                    sane_types['TYPE_GROUP']) or not option.is_settable():
                continue
            result += f'    * - ``{name}``\n'
            if option.type == sane_types['TYPE_BOOL']:
                result += f'      - bool\n'
            elif option.type == sane_types['TYPE_INT']:
                result += f'      - int\n'
            else:
                result += f'      - str\n'
            result += f'      - {option.desc}\n'
        result += '\n'
        return result

    def on_set_config(self):
        self.update_config()
        for name, value in self.config.items():
            if name not in self.dev.optlist:
                continue
            option = self.dev[name]
            value.enabled = option.is_active()
            if not value.enabled:
                continue
            try:
                setattr(self.dev, name, value)
            except Exception as ex:
                print('Cannot set "{}" to "{}": {}'.format(
                    name, value, str(ex)))
        self._shadow_config = None

    def on_start(self):
        self.on_set_config()
        try:
            self.dev.start()
            image = self.dev.arr_snap(progress=self.progress)
        except Exception as ex:
            # probably scan was cancelled
            print(str(ex))
            self.stop()
            return
        # scale data
        if image.dtype == numpy.uint8:
            pass
        elif image.dtype == numpy.uint16:
            image = image.astype(numpy.float32) / numpy.float32(2 ** 8)
        else:
            self.logger.error('Cannot handle %s data type', str(image.dtype))
            self.stop()
            return
        # create a Pyctools Frame
        frame = Frame()
        if image.shape[2] == 3:
            frame.type = 'RGB'
        elif image.shape[2] == 1:
            frame.type = 'Y'
        else:
            frame.type = '???'
        # send frame to dummy input
        frame.data = image
        frame.frame_no = 0
        frame.set_audit(self, 'data = scan\n', with_config=self.config)
        self.input_buffer['scan_done'].input(frame)

    def progress(self, line_no, max_lines):
        # hacky way to see if user has requested stop
        if None in self._event_loop.incoming:
            self.dev.cancel()

    def process_frame(self):
        preview = self.config['preview']
        output_name = self.outputs[preview]
        in_frame = self.input_buffer['scan_done'].get()
        out_frame = self.outframe_pool[output_name].get()
        out_frame.initialise(in_frame)
        self.send(output_name, out_frame)
        if preview:
            # stream frame to preview output
            in_frame.frame_no += 1
            self.input_buffer['scan_done'].input(in_frame)
        else:
            # shut down pipeline after sending one main frame
            self.stop()


# create class for each connected scanner
if sane:
    for (_name, _vendor, _model, _type) in sane.get_devices(localOnly=True):
        _class_name = 'Sane_{vendor}_{model}'.format(
            vendor = _vendor.title().replace(' ', ''),
            model = _model.title().replace(' ', '')
            )
        _class = type(_class_name, (SaneScanner,), {
            '__doc__': f'{_vendor} {_model} scanner.\n\n', '_name': _name})
        setattr(sys.modules[__name__], _class_name, _class)
        __all__.append(_class_name)

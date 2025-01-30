#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-25  Pyctools contributors
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

"""Pyctools visual graph editor.

.. image:: ../../images/editor_8.png

The :py:mod:`pyctools-editor <pyctools.tools.editor>` is a tool that
allows you to connect Pyctools components to make complex networks or
"graphs". You may find it easier to use than writing Python scripts
the old fashioned way.

If Pyctools has been :doc:`installed <../../manual/installation>`
correctly you should be able to start the editor with one of the
following commands::

    pyctools-editor

or ::

    python -m pyctools.tools.editor

The latter version may give you a more useful error message if the
program fails for some reason.

See the :doc:`getting started <../../manual/getting_started>` guide
for a short tutorial on using the editor.

"""

__all__ = []
__docformat__ = 'restructuredtext en'

import argparse
from collections import defaultdict
import gc
import importlib
import inspect
import logging
import os
import pprint
import pickle
import pkgutil
import re
import sys
import types
import warnings

import docutils.core

import pyctools.components
from pyctools.core.compound import Compound
from pyctools.core.config import *
from pyctools.core.qt import (catch_all, execute, get_app, qt_package,
                              QtCore, QtGui, QtSlot, QtWidgets)

if qt_package == 'PyQt5':
    from PyQt5.QtWidgets import QAction, QActionGroup
elif qt_package == 'PyQt6':
    from PyQt6.QtGui import QAction, QActionGroup
elif qt_package == 'PySide2':
    from PySide2.QtWidgets import QAction, QActionGroup
elif qt_package == 'PySide6':
    from PySide6.QtGui import QAction, QActionGroup
else:
    raise ImportError(f'Unrecognised qt_package value "{qt_package}"')


logger = logging.getLogger('pyctools-editor')

_COMP_MIMETYPE = 'application/x-pyctools-component'
_INPUT_MIMETYPE = 'application/x-pyctools-component-input'
_OUTPUT_MIMETYPE = 'application/x-pyctools-component-output'


class ConfigPathWidget(QtWidgets.QPushButton):
    def __init__(self, config, **kwds):
        super(ConfigPathWidget, self).__init__(**kwds)
        self.set_value(config)
        self.clicked.connect(self.new_value)

    @QtSlot()
    @catch_all
    def new_value(self):
        directory = self.config
        if self.config.exists:
            value = QtWidgets.QFileDialog.getOpenFileName(
                self, 'Choose file', directory)
        else:
            value = QtWidgets.QFileDialog.getSaveFileName(
                self, 'Choose file', directory)
        value = value[0]
        if value:
            self.show_value(value)

    def show_value(self, value):
        self.value = value
        if not value:
            self.setText('')
            return
        max_len = 40
        if len(value) > max_len:
            parts = value.split(os.path.sep)
            if len(parts) > 3:
                parts[2] = '...'
            value = os.path.sep.join(parts)
        while len(value) > max_len and len(parts) > 4:
            del parts[3]
            value = os.path.sep.join(parts)
        while len(value) > max_len and len(parts[-1]) > 4:
            parts[-1] = '...' + parts[-1][4:]
            value = os.path.sep.join(parts)
        self.setText(value)

    def get_value(self):
        return self.value

    def set_value(self, config):
        self.config = config
        self.show_value(config)
        self.setEnabled(config.enabled)


class ConfigBoolWidget(QtWidgets.QCheckBox):
    def __init__(self, config, **kwds):
        super(ConfigBoolWidget, self).__init__(**kwds)
        self.set_value(config)

    def get_value(self):
        return self.isChecked()

    def set_value(self, config):
        self.setChecked(config)
        self.setEnabled(config.enabled)


class ConfigIntWidget(QtWidgets.QSpinBox):
    def __init__(self, config, **kwds):
        super(ConfigIntWidget, self).__init__(**kwds)
        self.set_value(config)

    def get_value(self):
        return self.value()

    def set_value(self, config):
        if config.min_value is None:
            self.setMinimum(-(2**31))
        else:
            self.setMinimum(config.min_value)
        if config.max_value is None:
            self.setMaximum((2**31)-1)
        else:
            self.setMaximum(config.max_value)
        self.setWrapping(config.wrapping)
        self.setValue(config)
        self.setEnabled(config.enabled)


class ConfigFloatWidget(QtWidgets.QDoubleSpinBox):
    def __init__(self, config, **kwds):
        super(ConfigFloatWidget, self).__init__(**kwds)
        self.set_value(config)

    def get_value(self):
        return self.value()

    def set_value(self, config):
        self.setDecimals(config.decimals)
        if config.min_value is None:
            self.setMinimum(-(2**31))
        else:
            self.setMinimum(config.min_value)
        if config.max_value is None:
            self.setMaximum((2**31)-1)
        else:
            self.setMaximum(config.max_value)
        self.setWrapping(config.wrapping)
        self.setValue(config)
        self.setEnabled(config.enabled)


class ConfigStrWidget(QtWidgets.QLineEdit):
    def __init__(self, config, **kwds):
        super(ConfigStrWidget, self).__init__(**kwds)
        self.set_value(config)

    def get_value(self):
        return self.text()

    def set_value(self, config):
        self.setText(config)
        self.setEnabled(config.enabled)


class ConfigEnumWidget(QtWidgets.QComboBox):
    _type = str

    def __init__(self, config, **kwds):
        super(ConfigEnumWidget, self).__init__(**kwds)
        for item in config.choices:
            self.addItem(str(item))
        if config.extendable:
            self.addItem('<new>')
        self.set_value(config)
        self.currentIndexChanged.connect(self.new_value)

    @QtSlot(int)
    @catch_all
    def new_value(self, idx):
        value = str(self.itemText(idx))
        if value == '<new>':
            value, OK = QtWidgets.QInputDialog.getText(
                self, 'New option', 'Please enter a new option value')
            blocked = self.blockSignals(True)
            if OK:
                value = str(value)
                self.insertItem(idx, value)
            else:
                idx = 0
            self.setCurrentIndex(idx)
            self.blockSignals(blocked)

    def get_value(self):
        return self._type(self.currentText())

    def set_value(self, config):
        self.setCurrentIndex(self.findText(str(config)))
        self.setEnabled(config.enabled)


class ConfigIntEnumWidget(ConfigEnumWidget):
    _type = int


class ConfigParentWidget(QtWidgets.QWidget):
    def __init__(self, config, **kwds):
        super(ConfigParentWidget, self).__init__(**kwds)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.child_widgets = {}
        column_count = 1
        while True:
            row_count = len(config) // column_count
            if row_count <= 10:
                break
            column_count += 1
        row = 0
        for name, child in config.items():
            if row == 0:
                column = QtWidgets.QFormLayout()
                self.layout().addLayout(column)
            self.child_widgets[name] = config_widget[type(child)](child)
            column.addRow(name, self.child_widgets[name])
            row = (row + 1) % row_count

    def get_value(self):
        result = {}
        for name, widget in self.child_widgets.items():
            result[name] = widget.get_value()
        return result

    def set_value(self, config):
        for name, widget in self.child_widgets.items():
            widget.set_value(config[name])


class ConfigGrandParentWidget(QtWidgets.QTabWidget):
    def __init__(self, config, **kwds):
        super(ConfigGrandParentWidget, self).__init__(**kwds)
        for name, child in config.items():
            widget = config_widget[type(child)](child)
            self.addTab(widget, name)

    def get_value(self):
        result = {}
        for n in range(self.count()):
            widget = self.widget(n)
            name = self.tabText(n)
            name = name.replace('&', '')
            result[name] = widget.get_value()
        return result

    def set_value(self, config):
        for idx in range(self.count()):
            name = self.tabText(idx)
            widget = self.widget(idx)
            widget.set_value(config[name])


def ConfigCompoundWidget(config, **kwds):
    for value in config.values():
        if isinstance(value, ConfigParent):
            return ConfigGrandParentWidget(config, **kwds)
    return ConfigParentWidget(config, **kwds)


config_widget = {
    CompoundConfig    : ConfigCompoundWidget,
    ConfigEnum        : ConfigEnumWidget,
    ConfigFloat       : ConfigFloatWidget,
    ConfigParent      : ConfigParentWidget,
    ConfigBool        : ConfigBoolWidget,
    ConfigInt         : ConfigIntWidget,
    ConfigIntEnum     : ConfigIntEnumWidget,
    ConfigPath        : ConfigPathWidget,
    ConfigStr         : ConfigStrWidget,
    }

class ConfigDialog(QtWidgets.QDialog):
    def __init__(self, component, **kwds):
        super(ConfigDialog, self).__init__(**kwds)
        self.setWindowFlags(self.windowFlags() |
                            QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.component = component
        self.setLayout(QtWidgets.QVBoxLayout())
        # central area
        config = self.component.obj.get_config()
        self.main_area = config_widget[type(config)](config)
        self.layout().addWidget(self.main_area)
        # buttons
        buttons = QtWidgets.QDialogButtonBox()
        self.close_button = buttons.addButton(
            'Close', buttons.ButtonRole.AcceptRole)
        self.apply_button = buttons.addButton(
            'Apply', buttons.ButtonRole.ApplyRole)
        self.cancel_button = buttons.addButton(
            'Cancel', buttons.ButtonRole.RejectRole)
        buttons.clicked.connect(self.button_clicked)
        self.layout().addWidget(buttons)

    @QtSlot(QtWidgets.QAbstractButton)
    @catch_all
    def button_clicked(self, button):
        if button in (self.apply_button, self.close_button):
            self.component.obj.set_config(self.main_area.get_value())
        if button == self.apply_button:
            self.main_area.set_value(self.component.obj.get_config())
        if button in (self.cancel_button, self.close_button):
            self.close()


class ComponentLink(QtWidgets.QGraphicsPathItem):
    def __init__(self, source, outbox, dest, inbox, **kwds):
        super(ComponentLink, self).__init__(**kwds)
        self.setFlags(self.GraphicsItemFlag.ItemIsSelectable)
        self.setZValue(-10.0)
        self.source = source
        self.outbox = outbox
        self.dest = dest
        self.inbox = inbox

    @catch_all
    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemSceneHasChanged:
            if self.scene():
                self.redraw()
        if change == self.GraphicsItemChange.ItemSelectedHasChanged:
            pen = self.pen()
            if value:
                pen.setStyle(QtCore.Qt.PenStyle.DashLine)
            else:
                pen.setStyle(QtCore.Qt.PenStyle.SolidLine)
            self.setPen(pen)
        return super(ComponentLink, self).itemChange(change, value)

    def collides(self, x0, y0, x1, y1, shareable=False):
        # shareable: multiple links can start at one output
        line = QtWidgets.QGraphicsLineItem(x0, y0, x1, y1, self)
        collisions = line.collidingItems()
        line.setParentItem(None)
        for item in collisions:
            if not isinstance(item, (ComponentOutline, ComponentLink)):
                continue
            if self.parentItem() and item.parentItem() != self.parentItem():
                # we are in a compound component and the item isn't
                continue
            if isinstance(item, ComponentOutline):
                return item.mapRectToParent(item.boundingRect())
            # test each element of path as collidingItems uses the
            # bounding rect
            path = item.path()
            for n in range(1, path.elementCount()):
                p0 = path.elementAt(n - 1)
                p1 = path.elementAt(n)
                if x0 == x1:
                    # vertical line
                    if (p0.x == x0 and p1.x == x0
                            and max(p0.y, p1.y) > min(y0, y1)
                            and min(p0.y, p1.y) < max(y0, y1)):
                        return QtCore.QRectF(
                            p0.x - 0.5, min(p0.y, p1.y) - 0.5,
                            1.0, abs(p1.y - p0.y) + 1.0)
                else:
                    # horizontal line
                    if (p0.y == y0 and p1.y == y0
                            and max(p0.x, p1.x) > min(x0, x1)
                            and min(p0.x, p1.x) < max(x0, x1)):
                        if (shareable and item.source == self.source
                                      and item.outbox == self.outbox):
                            continue
                        return QtCore.QRectF(
                            min(p0.x, p1.x) - 0.5, p0.y - 0.5,
                            abs(p1.x - p0.x) + 1.0, 1.0)
        return None

    def five_segment_link(self, x0, y0, xn, yn):
        # cache for positions of vertical lines
        x1_c = {}
        x2_c = {}
        # maximum positions between y0 and yn
        steps = abs(int(yn - y0)) // 10
        steps = (steps + 1) // 2
        # try between y0 & yn, then outside that range
        for converge in True, False:
            y1 = y0
            y2 = yn
            for j in range(steps):
                # try y1, then y2
                for try1 in True, False:
                    y = (y2, y1)[try1]
                    # get non-colliding position of first vertical
                    if y in x1_c:
                        x1 = x1_c[y]
                    else:
                        x1 = x0 + 4
                        collision = self.collides(x1, y0, x1, y)
                        while collision:
                            while x1 <= collision.right():
                                x1 += 10
                            collision = self.collides(x1, y0, x1, y)
                        x1_c[y] = x1
                    # get non-colliding position of second vertical
                    if y in x2_c:
                        x2 = x2_c[y]
                    else:
                        x2 = xn - 10
                        collision = self.collides(x2, y, x2, yn)
                        while collision:
                            while x2 >= collision.left():
                                x2 -= 10
                            collision = self.collides(x2, y, x2, yn)
                        x2_c[y] = x2
                    # test a horizontal joining the two verticals
                    collision = self.collides(x1, y, x2, y)
                    if not collision:
                        return ((x0, y0), (x1, y0), (x1, y),
                                (x2, y), (x2, yn), (xn, yn))
                    # move beyond colliding item
                    if (try1 == converge) == (yn >= y0):
                        while y <= collision.bottom():
                            y += 10
                    else:
                        while y >= collision.top():
                            y -= 10
                    if try1:
                        y1 = y
                    else:
                        y2 = y
                if y2 == y1:
                    pass
                elif converge and ((y2 <= y1) == (yn > y0)):
                    break
            steps = 5
        return None

    def find_route(self, x0, y0, xn, yn):
        if xn - 10 < x0 + 4:
            # backwards link, 5 segments
            result = self.five_segment_link(x0, y0, xn, yn)
            if result:
                return result
            # draw direct line
            return ((x0, y0), (xn, yn))
        # try single line
        if yn == y0:
            if not self.collides(x0, y0, xn - 2, yn, shareable=True):
                return ((x0, y0), (xn, yn))
        # try 3-segment line
        for dx in range(10, min(40, 1 + (int(xn + 6 - x0) // 2)), 10):
            for x1 in int(xn) - dx, int(x0 - 6) + dx:
                if not (self.collides(x1, y0, x1, yn)
                        or self.collides(x0, y0, x1, y0, shareable=True)
                        or self.collides(x1, yn, xn - 2, yn)):
                    return ((x0, y0), (x1, y0), (x1, yn), (xn, yn))
        # try 5-segment line
        result = self.five_segment_link(x0, y0, xn, yn)
        if result:
            return result
        # draw direct line
        return ((x0, y0), (xn, yn))

    def smooth(self, points):
        c = 3
        result = [points[0]]
        for (x0, y0), (x1, y1), (x2, y2) in zip(
                points[:-2], points[1:-1], points[2:]):
            if x0 == x2 or y0 == y2:
                # straight line
                continue
            cx = (-c, c)[x0 < x2]
            cy = (-c, c)[y0 < y2]
            if y0 == y1:
                result.append((x1 - cx, y1))
                result.append((x1, y1 + cy))
            else:
                result.append((x1, y1 - cy))
                result.append((x1 + cx, y1))
        result.append(points[-1])
        return result

    def redraw(self):
        self.prepareGeometryChange()
        self.setPath(QtGui.QPainterPath())
        source_pos = self.source.outputs[self.outbox].scenePos()
        dest_pos = self.dest.inputs[self.inbox].scenePos()
        if self.parentItem():
            source_pos = self.mapFromScene(source_pos)
            dest_pos = self.mapFromScene(dest_pos)
        x0, y0 = source_pos.x() + 6, source_pos.y()
        xn, yn = dest_pos.x(), dest_pos.y()
        points = self.smooth(self.find_route(x0, y0, xn, yn))
        path = QtGui.QPainterPath(QtCore.QPointF(*points[0]))
        for point in points[1:]:
            path.lineTo(*point)
        self.prepareGeometryChange()
        self.setPath(path)
        # in PySide the link vanishes unless we get a reference to the
        # scene here
        scene = self.scene()


class IOIcon(QtWidgets.QGraphicsRectItem):
    def __init__(self, name, **kwds):
        super(IOIcon, self).__init__(**kwds)
        self.name = name
        self.setAcceptDrops(True)
        # draw an invisible rectangle to define drag-and-drop area
        pen = self.pen()
        pen.setStyle(QtCore.Qt.PenStyle.NoPen)
        self.setPen(pen)
        self.setRect(-3, -8, 13, 17)
        # draw a smaller visible triangle
        self.triangle = QtWidgets.QGraphicsPolygonItem(
            QtGui.QPolygonF([QtCore.QPointF(0, -5),
                             QtCore.QPointF(6, 0),
                             QtCore.QPointF(0, 5),
                             QtCore.QPointF(0, -5)]), self)
        # create label
        label = QtWidgets.QGraphicsSimpleTextItem(name, parent=self)
        font = label.font()
        font.setPointSizeF(font.pointSize() * 0.75)
        label.setFont(font)
        # set label position
        br = label.boundingRect()
        if self.mime_type == _INPUT_MIMETYPE:
            label.setPos(4, -br.height())
        else:
            label.setPos(-(2 + br.width()), -br.height())

    def mousePressEvent(self, event):
        pass

    @catch_all
    def mouseMoveEvent(self, event):
        start_pos = event.buttonDownScreenPos(QtCore.Qt.MouseButton.LeftButton)
        if (QtCore.QLineF(QtCore.QPointF(event.screenPos()),
                          QtCore.QPointF(start_pos)).length() <
                                    QtWidgets.QApplication.startDragDistance()):
            return
        start_pos = event.buttonDownScenePos(QtCore.Qt.MouseButton.LeftButton)
        drag = QtGui.QDrag(event.widget())
        mimeData = QtCore.QMimeData()
        mimeData.setData(self.mime_type, pickle.dumps(start_pos))
        drag.setMimeData(mimeData)
        execute(drag, QtCore.Qt.DropAction.LinkAction)

    @catch_all
    def dragEnterEvent(self, event):
        event.setAccepted(event.mimeData().hasFormat(self.link_mime_type))

    @catch_all
    def dropEvent(self, event):
        if not event.mimeData().hasFormat(self.link_mime_type):
            return super(IOIcon, self).dropEvent(event)
        start_pos = pickle.loads(
            event.mimeData().data(self.link_mime_type).data())
        link_from = self.scene().itemAt(
            QtCore.QPointF(start_pos), self.transform())
        while link_from and not isinstance(link_from, IOIcon):
            link_from = link_from.parentItem()
        if isinstance(link_from, OutputIcon):
            source = link_from.parentItem()
            outbox = link_from.name
            dest = self.parentItem()
            inbox = self.name
        elif isinstance(link_from, InputIcon):
            source = self.parentItem()
            outbox = self.name
            dest = link_from.parentItem()
            inbox = link_from.name
        else:
            return
        for link in self.scene().matching_items(ComponentLink):
            if (link.source == source and link.outbox == outbox and
                                link.dest == dest and link.inbox == inbox):
                self.scene().removeItem(link)
        link = ComponentLink(source, outbox, dest, inbox)
        self.scene().addItem(link)


class InputIcon(IOIcon):
    mime_type = _INPUT_MIMETYPE
    link_mime_type = _OUTPUT_MIMETYPE


class OutputIcon(IOIcon):
    mime_type = _OUTPUT_MIMETYPE
    link_mime_type = _INPUT_MIMETYPE


py_mod = re.compile(':py:mod:`\.*(\S*)(\s*<[\w\.]*>)?`')
py_other = re.compile(
    ':py:(attr|class|data|func|meth|obj):`(~[\w\.]*\.)?(.*?)`')

def strip_sphinx_domains(text):
    text = py_mod.sub(r'*\1*', text)
    text = py_other.sub(r'*\3*', text)
    return text


class ComponentOutline(QtWidgets.QGraphicsRectItem):
    def __init__(self, name, obj, **kwds):
        super(ComponentOutline, self).__init__(**kwds)
        self.name = name
        # boundary
        self.width = 100
        self.height = 60 + (max(2, len(obj.inputs), len(obj.outputs)) * 20)
        self.setRect(0, 0, self.width, self.height)
        if isinstance(obj, Compound):
            # add dotted outside border
            self.surround = QtWidgets.QGraphicsRectItem(
                -3, -3, self.width + 6, self.height + 6, self)
            pen = self.surround.pen()
            pen.setStyle(QtCore.Qt.PenStyle.DashDotLine)
            self.surround.setPen(pen)
        # name label
        self.name_label = QtWidgets.QGraphicsSimpleTextItem(name, parent=self)
        font = self.name_label.font()
        font.setBold(True)
        self.name_label.setFont(font)
        self.name_label.setPos(8, 8)
        # class label
        self.set_class_label(obj.__class__.__name__ + '()')
        # inputs
        self.inputs = {}
        for idx, name in enumerate(obj.inputs):
            self.inputs[name] = InputIcon(name, parent=self)
            self.inputs[name].setPos(0, 60 + (idx * 20))
        # outputs
        self.outputs = {}
        for idx, name in enumerate(obj.outputs):
            self.outputs[name] = OutputIcon(name, parent=self)
            self.outputs[name].setPos(self.width, 60 + (idx * 20))

    def set_class_label(self, text):
        class_label = QtWidgets.QGraphicsSimpleTextItem(parent=self)
        font = class_label.font()
        font.setPointSizeF(font.pointSize() * 0.8)
        font.setItalic(True)
        class_label.setFont(font)
        max_width = self.width - 10
        if self.width > 120:
            # expanded compound component, put on same line as label
            max_width -= self.name_label.boundingRect().width() + 5
        class_label.setText(QtGui.QFontMetrics(font).elidedText(
            text, QtCore.Qt.TextElideMode.ElideRight, max_width))
        text_width = class_label.boundingRect().width()
        if self.width > 120:
            class_label.setPos((self.width - 5) - text_width, 9)
        else:
            class_label.setPos(5, 30)

    @catch_all
    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemPositionChange:
            value.setX(value.x() + 5 - ((value.x() + 5) % 10))
            value.setY(value.y() + 5 - ((value.y() + 5) % 10))
            return value
        if self.scene():
            if change == self.GraphicsItemChange.ItemSceneHasChanged:
                self.redraw()
            if change == self.GraphicsItemChange.ItemPositionHasChanged:
                # redraw all links in case component is now on top of one
                for link in self.scene().matching_items(ComponentLink):
                    link.redraw()
                self.scene().update_scene_rect(no_shrink=True)
        return super(ComponentOutline, self).itemChange(change, value)

    def redraw(self):
        # do anything needed after component has been added to a scene
        # e.g. anything requiring collision detection
        pass


class ComponentIcon(ComponentOutline):
    def __init__(self, name, obj, **kwds):
        super(ComponentIcon, self).__init__(name, obj, **kwds)
        self.setFlags(self.GraphicsItemFlag.ItemIsMovable |
                      self.GraphicsItemFlag.ItemIsSelectable |
                      self.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.obj = obj
        self.config_dialog = None
        # context menu actions
        self.context_menu_actions = {
            'Rename': self.rename,
            'Delete': self.delete,
            'Configure': self.do_config,
            }
        # set icon's tooltip
        help_text = inspect.getdoc(self.obj)
        if help_text:
            help_text = strip_sphinx_domains(help_text)
            help_text = docutils.core.publish_parts(
                help_text, writer_name='html')['html_body']
        else:
            help_text = '<p>Undocumented</p>'
        help_text = '<h4>{}()</h4>\n{}\n<p>Module: {}</p>'.format(
            self.obj.__class__.__name__, help_text, self.obj.__module__)
        self.setToolTip(help_text)

    def rename(self):
        old_name = self.name
        self.name = None
        name = self.scene().get_unique_name(old_name)
        self.name = old_name
        if not name:
            return
        self.name = name
        if self.config_dialog:
            self.config_dialog.setWindowTitle('%s configuration' % self.name)
        self.name_label.setText(self.name)

    def delete(self):
        self.scene().delete_child(self)

    def do_config(self):
        if self.config_dialog and self.config_dialog.isVisible():
            self.config_dialog.raise_()
            self.config_dialog.activateWindow()
        else:
            self.config_dialog = ConfigDialog(
                self, parent=self.scene().views()[0])
            self.config_dialog.setWindowTitle('%s configuration' % self.name)
            self.config_dialog.show()

    def regenerate(self):
        config = self.obj.get_config()
        self.obj = self.obj.__class__()
        self.obj.set_config(config)
        return self.name, self.obj

    @catch_all
    def contextMenuEvent(self, event):
        event.accept()
        menu = QtWidgets.QMenu()
        actions = {}
        for label, method in self.context_menu_actions.items():
            actions[menu.addAction(label)] = method
        action = execute(menu, event.screenPos())
        if action:
            actions[action]()
        self.ungrabMouse()

    @catch_all
    def mouseDoubleClickEvent(self, event):
        self.do_config()


class MockIO(object):
    pass


class CompoundIcon(ComponentIcon):
    def __init__(self, name, obj, expanded=False, **kwds):
        self.expanded = expanded
        super(CompoundIcon, self).__init__(name, obj, **kwds)
        self.context_menu_actions['Expand/contract'] = self.expand_contract
        # repurpose existing inputs and outputs
        self.mock_IO = MockIO()
        self.mock_IO.inputs = {}
        for name, icon in self.outputs.items():
            self.mock_IO.inputs[name] = icon
        self.mock_IO.outputs = {}
        for name, icon in self.inputs.items():
            self.mock_IO.outputs[name] = icon

    def expand_contract(self):
        old_w, old_h = self.width, self.height
        self.expanded = not self.expanded
        self.redraw()
        delta_x = self.width - old_w
        delta_y = self.height - old_h
        # move other components
        pos = self.scenePos()
        x = pos.x()
        y = pos.y()
        for child in self.scene().matching_items(ComponentIcon):
            if child == self:
                continue
            pos = child.scenePos()
            move = [0, 0]
            if pos.x() >= x + old_w:
                move[0] = delta_x
            if pos.y() >= y + old_h:
                move[1] = delta_y
            if move != [0, 0]:
                child.moveBy(*move)
        # redraw all links
        for link in self.scene().matching_items(ComponentLink):
            link.redraw()
        self.scene().update_scene_rect(no_shrink=True)

    def build_left(self, dest, pos, x, y, dx, dy):
        for (src_name, outbox), (dest_name, inbox) in self.obj.links:
            if src_name in pos or (dest_name, inbox) != dest:
                continue
            # find a vacant position
            xn, yn = x - dx, y
            while [xn, yn] in pos.values():
                yn += dy
            pos[src_name] = [xn, yn]
            if src_name == 'self':
                return
            # cascade back from component's inputs
            for name in self.obj.children[src_name].inputs:
                self.build_left((src_name, name), pos, xn, yn, dx, dy)
            # cascade forward from component's outputs
            for name in self.obj.children[src_name].outputs:
                self.build_right((src_name, name), pos, xn, yn, dx, dy)
            return

    def build_right(self, source, pos, x, y, dx, dy):
        for (src_name, outbox), (dest_name, inbox) in self.obj.links:
            if dest_name in pos or (src_name, outbox) != source:
                continue
            # find a vacant position
            idx = 0
            xn, yn = x, y
            while [xn, yn] in pos.values():
                idx += 1
                xn, yn = x + ((idx % 2) * dx), y + ((idx // 2) * dy)
            pos[dest_name] = [xn, yn]
            if dest_name == 'self':
                continue
            # cascade forward from component's outputs
            for name in self.obj.children[dest_name].outputs:
                self.build_right((dest_name, name), pos, xn, yn, dx, dy)
            # cascade back from component's inputs
            for name in self.obj.children[dest_name].inputs:
                self.build_left((dest_name, name), pos, xn, yn, dx, dy)

    def redraw(self):
        # delete previous version
        for child in self.childItems():
            if isinstance(child, IOIcon):
                continue
            if child in (self.name_label, self.surround):
                continue
            child.setParentItem(None)
        child_comps = {}
        if self.expanded and self.obj.children:
            # create components and get max size
            dx, dy = 0, 0
            for name, obj in self.obj.children.items():
                child = ComponentOutline(name, obj, parent=self)
                child.setEnabled(False)
                dx = max(dx, child.width + 30)
                dy = max(dy, child.height + 30)
                child_comps[name] = child
            # position components according to linkages
            pos = {}
            # start by working back from outputs
            x, y = 0, 0
            for name in self.obj.outputs:
                self.build_left(('self', name), pos, x, y, dx, dy)
            if 'self' in pos:
                x, y = pos['self']
                del pos['self']
            # then work forwards from inputs
            for name in self.obj.inputs:
                self.build_right(('self', name), pos, x, y, dx, dy)
            if 'self' in pos:
                x, y = pos['self']
                del pos['self']
            # work backwards from any unplaced components
            for dest_name in child_comps:
                if dest_name in pos:
                    continue
                for name in self.obj.children[dest_name].inputs:
                    self.build_left((dest_name, name), pos, x, y, dx, dy)
            if 'self' in pos:
                x, y = pos['self']
                del pos['self']
            # work forwards from any unplaced components
            for src_name in child_comps:
                if src_name in pos:
                    continue
                for name in self.obj.children[src_name].outputs:
                    self.build_right((src_name, name), pos, x, y, dx, dy)
            if 'self' in pos:
                del pos['self']
            # move components to close gaps
            x_max = max([x[0] for x in pos.values()])
            changed = True
            while changed:
                changed = False
                for name in pos:
                    new_pos = [pos[name][0] + dx, pos[name][1]]
                    if new_pos[0] <= x_max and new_pos not in pos.values():
                        pos[name] = new_pos
                        changed = True
            x_min = min([x[0] for x in pos.values()])
            changed = True
            while changed:
                changed = False
                for name in pos:
                    new_pos = [pos[name][0] - dx, pos[name][1]]
                    if new_pos[0] >= x_min and new_pos not in pos.values():
                        pos[name] = new_pos
                        changed = True
            # reposition components
            x_min = min([x[0] for x in pos.values()])
            x_max = max([x[0] for x in pos.values()])
            y_min = min([x[1] for x in pos.values()])
            y_max = max([x[1] for x in pos.values()])
            for name, [x, y] in pos.items():
                child_comps[name].setPos(x + 40 - x_min, y + 30 - y_min)
            self.width = (x_max - x_min) + dx + 50
            self.height = (y_max - y_min) + dy + 30
        else:
            self.width = 100
            self.height = 60 + (20 * max(
                2, len(self.obj.inputs), len(self.obj.outputs)))
        # redraw boundary
        self.setRect(0, 0, self.width, self.height)
        self.surround.setRect(-3, -3, self.width + 6, self.height + 6)
        # redraw class label
        self.set_class_label(self.obj.__class__.__name__ + '()')
        # move outputs
        for icon in self.outputs.values():
            y = icon.pos().y()
            icon.setPos(self.width, y)
        # draw linkages
        if self.expanded:
            for (src, outbox), (dest, inbox) in self.obj.links:
                if src == 'self':
                    src_comp = self.mock_IO
                else:
                    src_comp = child_comps[src]
                if dest == 'self':
                    dest_comp = self.mock_IO
                else:
                    dest_comp = child_comps[dest]
                link = ComponentLink(src_comp, outbox,
                                     dest_comp, inbox, parent=self)
                link.setEnabled(False)
                link.redraw()
        self.scene().update_scene_rect(no_shrink=True)


class NetworkArea(QtWidgets.QGraphicsScene):
    min_size = QtCore.QRectF(0, 0, 800, 600)

    def __init__(self, components, **kwds):
        super(NetworkArea, self).__init__(**kwds)
        self.components = components
        self.setSceneRect(self.min_size)
        self.runnable = None

    def dragEnterEvent(self, event):
        if not event.mimeData().hasFormat(_COMP_MIMETYPE):
            return super(NetworkArea, self).dragEnterEvent(event)
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        if not event.mimeData().hasFormat(_COMP_MIMETYPE):
            return super(NetworkArea, self).dragMoveEvent(event)

    def dragMoveEvent(self, event):
        if not event.mimeData().hasFormat(_COMP_MIMETYPE):
            return super(NetworkArea, self).dragMoveEvent(event)

    @catch_all
    def dropEvent(self, event):
        if not event.mimeData().hasFormat(_COMP_MIMETYPE):
            return super(NetworkArea, self).dropEvent(event)
        name = event.mimeData().text()
        self.add_component(self.components[name]['class'], event.scenePos())

    def keyPressEvent(self, event):
        if not event.matches(QtGui.QKeySequence.StandardKey.Delete):
            event.ignore()
            return
        event.accept()
        for child in self.items():
            if child.isSelected():
                self.delete_child(child)

    def delete_child(self, child):
        if isinstance(child, ComponentIcon):
            for link in self.matching_items(ComponentLink):
                if link.source == child or link.dest == child:
                    self.removeItem(link)
            child.obj = None
        if child.scene():
            self.removeItem(child)
        gc.collect()

    def update_scene_rect(self, no_shrink=False):
        rect = self.itemsBoundingRect()
        rect.adjust(-150, -150, 150, 150)
        rect = rect.united(self.min_size)
        if no_shrink:
            rect = rect.united(self.sceneRect())
        self.setSceneRect(rect)

    def add_component(self, klass, position):
        base_name = re.sub('[^A-Z]', '', klass.__name__).lower()
        name = base_name
        n = 0
        while self.name_in_use(name):
            name = base_name + str(n)
            n += 1
        name = self.get_unique_name(name)
        if name:
            self.new_component(name, klass(), position)

    def new_component(self, name, obj, position, expanded=False):
        if isinstance(obj, Compound):
            component = CompoundIcon(name, obj, expanded=expanded)
        else:
            component = ComponentIcon(name, obj)
        component.setPos(position)
        self.addItem(component)
        self.update_scene_rect()
        return component

    def get_unique_name(self, base_name):
        while True:
            name, OK = QtWidgets.QInputDialog.getText(
                self.views()[0], 'Component name',
                'Please enter a unique component name', text=base_name)
            if not OK:
                return ''
            name = str(name)
            if not self.name_in_use(name):
                return name

    def name_in_use(self, name):
        for child in self.matching_items(ComponentIcon):
            if child.name == name:
                return True
        return False

    def matching_items(self, klass):
        for child in self.items():
            if child.isEnabled() and isinstance(child, klass):
                yield child

    def get_linkages(self):
        linkages = defaultdict(list)
        for child in self.matching_items(ComponentLink):
            source = child.source.name, child.outbox
            dest = child.dest.name, child.inbox
            linkages[source].append(dest)
        return linkages

    @QtSlot()
    @catch_all
    def run_graph(self):
        self.stop_graph()
        # create compound component and run it
        components = {}
        for child in self.matching_items(ComponentIcon):
            name, obj = child.regenerate()
            components[name] = obj
        gc.collect()
        self.runnable = Compound(
            linkages=self.get_linkages(), **components)
        self.runnable.start()

    @QtSlot()
    @catch_all
    def stop_graph(self):
        if self.runnable:
            self.runnable.stop()
            self.runnable = None

    def load_script(self, file_name):
        script_dir, script_name = os.path.split(file_name)
        script_name = os.path.splitext(script_name)[0]
        sys.path.insert(0, script_dir)
        if script_name in sys.modules:
            module = importlib.reload(sys.modules[script_name])
        else:
            module = importlib.import_module(script_name)
        del sys.path[0]
        ComponentNetwork = None
        Network = None
        if hasattr(module, 'ComponentNetwork'):
            ComponentNetwork = module.ComponentNetwork
        elif hasattr(module, 'Network'):
            Network = module.Network
        else:
            # not a recognised script
            logger.error('Script not recognised')
            return
        for child in self.items():
            self.delete_child(child)
        if ComponentNetwork:
            logger.info('New style network')
            network = ComponentNetwork()
            components = network.children
            positions = network.positions
            expanded = network.expanded
            links = network.links
            if hasattr(network, 'user_config'):
                network.set_config(network.user_config)
            else:
                # reinstantiate components without config constructor arguments
                for name, comp in components.items():
                    config = comp.get_config()
                    components[name] = comp.__class__()
                    components[name].set_config(config)
        elif Network:
            logger.info('Old style network')
            components = {}
            positions = {}
            expanded = {}
            for name, details in Network.components.items():
                components[name] = eval(details['class'])()
                components[name].set_config(eval(details['config']))
                positions[name] = details['pos']
                if 'expanded' in details:
                    expanded[name] = details['expanded']
            links = []
            for source, dests in Network.linkages.items():
                if isinstance(dests[0], str):
                    # not a list of pairs, so make it into one
                    dests = list(zip(dests[0::2], dests[1::2]))
                for dest in dests:
                    links.append((source, dest))
        comps = {}
        # add component icons
        for name, comp in components.items():
            kw = {}
            if name in expanded:
                kw['expanded'] = expanded[name]
            comps[name] = self.new_component(
                name, comp, QtCore.QPointF(*positions[name]), **kw)
        # add link icons
        for (src, outbox), (dest, inbox) in links:
            link = ComponentLink(comps[src], outbox, comps[dest], inbox)
            self.addItem(link)
        self.views()[0].centerOn(self.itemsBoundingRect().center())

    def save_script(self, file_name):
        components = {}
        modules = []
        user_config = {}
        positions = {}
        expanded = {}
        with_qt = False
        for child in self.matching_items(ComponentIcon):
            name = child.name
            obj = child.obj
            mod = obj.__class__.__module__
            user_config[name] = obj.get_config().to_dict()
            components[name] = '{}.{}'.format(mod, obj.__class__.__name__)
            positions[name] = (child.pos().x(), child.pos().y())
            if isinstance(child, CompoundIcon):
                expanded[name] = child.expanded
            if mod not in modules:
                modules.append(mod)
                with_qt = (with_qt or
                           self.components[components[name]]['needs_qt'])
        user_config_str = '{'
        for name, value in user_config.items():
            if not value:
                continue
            indent = len(name) + 12
            user_config_str += "\n        '{}': {},".format(
                name, ('\n' + (' ' * indent)).join(
                    pprint.pformat(value, width=80-indent).splitlines()))
        user_config_str += '\n        }\n'
        linkages = self.get_linkages()
        linkages = ('\n' + (' ' * 23)).join(pprint.pformat(
            dict(linkages), width=80-23).splitlines())
        positions = ('\n' + (' ' * 16)).join(pprint.pformat(
            positions, width=80-16).splitlines())
        expanded = ('\n' + (' ' * 15)).join(pprint.pformat(
            expanded, width=80-15, compact=True).splitlines())
        modules.sort()
        with open(file_name, 'w') as of:
            of.write("""#!/usr/bin/env python
# File written by pyctools-editor. Do not edit.

from pyctools.core.compound import Compound
""")
            if with_qt:
                of.write('from pyctools.core.qt import ComponentRunner\n')
            else:
                of.write('from pyctools.core.compound import ComponentRunner\n')
            for module in modules:
                of.write('import %s\n' % module)
            of.write("""
class ComponentNetwork(Compound):
    positions = {positions}
    expanded = {expanded}
    user_config = {user_config}

    def __init__(self):
        super(ComponentNetwork, self).__init__("""
                     .format(positions=positions, expanded=expanded,
                             user_config=user_config_str))
            for name, component in components.items():
                of.write("\n            {} = {}(),".format(name, component))
            of.write("""
            linkages = {linkages}
            )

if __name__ == '__main__':
    runner = ComponentRunner()
    runner.run_network(ComponentNetwork())
"""
                     .format(linkages=linkages))


class ComponentItemModel(QtGui.QStandardItemModel):
    def mimeTypes(self):
        return [_COMP_MIMETYPE]

    def mimeData(self, index_list):
        if len(index_list) != 1:
            return None
        idx = index_list[0]
        if not idx.isValid():
            return None
        data = idx.data(QtCore.Qt.ItemDataRole.UserRole+1)
        if not data:
            return None
        result = QtCore.QMimeData()
        result.setData(_COMP_MIMETYPE, b'')
        result.setText(data)
        return result

    def add_components(self, components):
        # build tree from component list
        root_node = self.invisibleRootItem()
        for name, item in components.items():
            # find or create node, ignoring 'pyctools.components' prefix
            parts = name.split('.')[2:]
            node = self.get_node(root_node, parts)
            # set node
            if item['class']:
                node.setData(name)
                help_text = inspect.getdoc(item['class'])
                if help_text:
                    help_text = help_text.splitlines()[0]
                    help_text = strip_sphinx_domains(help_text)
                    help_text = docutils.core.publish_parts(
                        help_text, writer_name='html')['html_body']
                    node.setToolTip(help_text)
            else:
                node.setToolTip(item['tooltip'])
                node.setDragEnabled(False)
                font = node.font()
                font.setItalic(True)
                node.setFont(font)
        # collapse nodes with single children
        self.remove_singletons(root_node)
        root_node.sortChildren(0)

    def get_node(self, parent, parts):
        for row in range(parent.rowCount()):
            child = parent.child(row)
            if child.text() == parts[0]:
                break
        else:
            child = QtGui.QStandardItem(parts[0])
            child.setEditable(False)
            parent.appendRow(child)
        if len(parts) > 1:
            return self.get_node(child, parts[1:])
        return child

    def remove_singletons(self, parent):
        if parent.rowCount() == 1:
            child = parent.child(0)
            if not child.rowCount():
                child = parent.takeRow(0)[0]
                parent.setData(child.data())
                parent.setText(child.text())
                parent.setToolTip(child.toolTip())
                return
        for row in range(parent.rowCount()):
            self.remove_singletons(parent.child(row))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, script=None, **kwds):
        super(MainWindow, self).__init__(**kwds)
        self.setWindowTitle("Pyctools graph editor")
        self.script_file = os.getcwd()
        # get component list
        self.get_components()
        ## file menu
        file_menu = self.menuBar().addMenu('File')
        file_menu.addAction('Load script', self.load_script, 'Ctrl+O')
        file_menu.addAction('Save script', self.save_script, 'Ctrl+S')
        file_menu.addSeparator()
        quit_action = QAction('Quit', self)
        quit_action.setShortcuts(['Ctrl+Q', 'Ctrl+W'])
        quit_action.triggered.connect(
            QtWidgets.QApplication.instance().closeAllWindows)
        file_menu.addAction(quit_action)
        ## zoom menu
        zoom_menu = self.menuBar().addMenu('Zoom')
        zoom_menu.addAction('Zoom in', self.zoom_in, 'Ctrl++')
        zoom_menu.addAction('Zoom out', self.zoom_out, 'Ctrl+-')
        zoom_menu.addSeparator()
        self.zoom_group = QActionGroup(self)
        for zoom in (25, 35, 50, 70, 100, 141, 200):
            action = QAction('%d%%' % zoom, self)
            action.setCheckable(True)
            if zoom == 100:
                action.setChecked(True)
            action.setData(zoom)
            zoom_menu.addAction(action)
            self.zoom_group.addAction(action)
        self.zoom_group.triggered.connect(self.set_zoom)
        ## main application area
        self.setCentralWidget(QtWidgets.QWidget())
        grid = QtWidgets.QGridLayout()
        grid.setColumnStretch(0, 1)
        self.centralWidget().setLayout(grid)
        # component list and network drawing area
        splitter = QtWidgets.QSplitter(self)
        splitter.setChildrenCollapsible(False)
        self.component_list = QtWidgets.QTreeView(parent=self)
        self.component_list.setDragEnabled(True)
        self.component_list.setHeaderHidden(True)
        self.component_list.setUniformRowHeights(True)
        self.component_list.setModel(ComponentItemModel())
        self.component_list.model().add_components(self.components)
        self.component_list.resizeColumnToContents(0)
        self.component_list.updateGeometries()
        splitter.addWidget(self.component_list)
        self.network_area = NetworkArea(self.components, parent=self)
        self.view = QtWidgets.QGraphicsView(self.network_area)
        self.view.setAcceptDrops(True)
        self.view.setDragMode(self.view.DragMode.RubberBandDrag)
        self.view.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.view.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        splitter.addWidget(self.view)
        splitter.setStretchFactor(1, 1)
        grid.addWidget(splitter, 0, 0, 1, 5)
        # status or other information
        self.status = QtWidgets.QLabel()
        grid.addWidget(self.status, 1, 0, 1, 3)
        # buttons
        run_button = QtWidgets.QPushButton('run graph')
        run_button.clicked.connect(self.network_area.run_graph)
        grid.addWidget(run_button, 1, 3)
        stop_button = QtWidgets.QPushButton('stop graph')
        stop_button.clicked.connect(self.network_area.stop_graph)
        grid.addWidget(stop_button, 1, 4)
        # load initial script
        if script:
            script = os.path.abspath(script)
            self.set_window_title(script)
            self.network_area.load_script(script)

    def get_components(self):
        # get list of available components (and import them!)
        self.components = {}
        # pkgutil.walk_packages doesn't work with namespace packages, so
        # we do a simple file search instead
        for path in pyctools.components.__path__:
            depth = len(path.split(os.path.sep)) - 2
            for root, dirs, files in os.walk(path):
                pkg_parts = root.split(os.path.sep)[depth:]
                if pkg_parts[-1] == '__pycache__':
                    continue
                for file_name in files:
                    base, ext = os.path.splitext(file_name)
                    if base == '__init__' or ext != '.py':
                        continue
                    # import module
                    mod_name = '.'.join(pkg_parts + [base])
                    try:
                        mod = __import__(mod_name, globals(), locals(), ['*'])
                    except ImportError as ex:
                        self.components[mod_name] = {
                            'class': None,
                            'module': mod_name,
                            'tooltip': '<p>{}</p>'.format(str(ex)),
                            }
                        continue
                    if not hasattr(mod, '__all__') or not mod.__all__:
                        continue
                    # try to find out if module needs Qt
                    needs_qt = False
                    for item in dir(mod):
                        if item in ('QtEventLoop', 'QtThreadEventLoop'):
                            needs_qt = True
                            break
                        if not 'Qt' in item:
                            continue
                        item = getattr(mod, item)
                        if not isinstance(item, types.ModuleType):
                            continue
                        if item.__name__.startswith('PyQt'):
                            needs_qt = True
                            break
                    # add module's components to list
                    for name in mod.__all__:
                        full_name = '.'.join((mod_name, name))
                        self.components[full_name] = {
                            'class': getattr(mod, name),
                            'module': mod_name,
                            'name': name,
                            'needs_qt': needs_qt,
                            }

    @QtSlot()
    @catch_all
    def load_script(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Load file', self.script_file, 'Python scripts (*.py)')
        file_name = file_name[0]
        if file_name:
            self.set_window_title(file_name)
            self.network_area.load_script(file_name)

    @QtSlot()
    @catch_all
    def save_script(self):
        file_name = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save file', self.script_file, 'Python scripts (*.py)')
        file_name = file_name[0]
        if file_name:
            self.set_window_title(file_name)
            self.network_area.save_script(file_name)

    def set_window_title(self, file_name):
        self.script_file = file_name
        self.setWindowTitle(
            "Pyctools graph editor - %s" % os.path.basename(file_name))

    @QtSlot()
    @catch_all
    def zoom_in(self):
        self.inc_zoom(1)

    @QtSlot()
    @catch_all
    def zoom_out(self):
        self.inc_zoom(-1)

    def inc_zoom(self, inc):
        action_list = self.zoom_group.actions()
        current_action = self.zoom_group.checkedAction()
        if current_action:
            idx = action_list.index(current_action) + inc
            idx = max(min(idx, len(action_list) - 1), 0)
        else:
            idx = (1 + len(action_list)) // 2
        action_list[idx].setChecked(True)
        self.set_zoom()

    @QtSlot()
    @catch_all
    def set_zoom(self):
        current_action = self.zoom_group.checkedAction()
        zoom = float(current_action.data()) / 100.0
        self.view.resetTransform()
        self.view.scale(zoom, zoom)


def main():
    app = get_app()
    # get command args
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-s', '--script', metavar='file_name',
                        help='a script to load at startup')
    parser.add_argument('-t', '--test', action='store_true',
                        help='turn on extra warnings useful to a developer')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='increase verbosity of log messages')
    args = parser.parse_args(sys.argv[1:])
    logging.basicConfig(level=logging.ERROR - (args.verbose * 10))
    if args.test:
        warnings.simplefilter('default')
    # create GUI and run application event loop
    main = MainWindow(script=args.script)
    main.show()
    return execute(app)


if __name__ == '__main__':
    sys.exit(main())

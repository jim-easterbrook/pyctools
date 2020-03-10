#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-20  Pyctools contributors
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
import inspect
import logging
import os
import pprint
import re
import six
from six.moves import cPickle
import pkgutil
import sys
import types

import docutils.core
from PyQt5 import QtCore, QtGui, QtWidgets

import pyctools.components
from pyctools.core.compound import Compound
from pyctools.core.config import *
from pyctools.core.qt import catch_all


logger = logging.getLogger('pyctools-editor')

_COMP_MIMETYPE = 'application/x-pyctools-component'
_INPUT_MIMETYPE = 'application/x-pyctools-component-input'
_OUTPUT_MIMETYPE = 'application/x-pyctools-component-output'


class ConfigPathWidget(QtWidgets.QPushButton):
    def __init__(self, config, **kwds):
        super(ConfigPathWidget, self).__init__(**kwds)
        self.config = config
        self.show_value(self.config)
        self.clicked.connect(self.set_value)

    @QtCore.pyqtSlot()
    @catch_all
    def set_value(self):
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
            parts = value.split('/')
            if len(parts) > 3:
                parts[2] = '...'
            value = '/'.join(parts)
        while len(value) > max_len and len(parts) > 4:
            del parts[3]
            value = '/'.join(parts)
        while len(value) > max_len and len(parts[-1]) > 4:
            parts[-1] = '...' + parts[-1][4:]
            value = '/'.join(parts)
        self.setText(value)

    def get_value(self):
        return self.value


class ConfigBoolWidget(QtWidgets.QCheckBox):
    def __init__(self, config, **kwds):
        super(ConfigBoolWidget, self).__init__(**kwds)
        self.config = config
        self.setChecked(self.config)

    def get_value(self):
        return self.isChecked()


class ConfigIntWidget(QtWidgets.QSpinBox):
    def __init__(self, config, **kwds):
        super(ConfigIntWidget, self).__init__(**kwds)
        self.config = config
        if self.config.min_value is None:
            self.setMinimum(-(2**31))
        else:
            self.setMinimum(self.config.min_value)
        if self.config.max_value is None:
            self.setMaximum((2**31)-1)
        else:
            self.setMaximum(self.config.max_value)
        self.setWrapping(config.wrapping)
        self.setValue(self.config)

    def get_value(self):
        return self.value()


class ConfigFloatWidget(QtWidgets.QDoubleSpinBox):
    def __init__(self, config, **kwds):
        super(ConfigFloatWidget, self).__init__(**kwds)
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

    def get_value(self):
        return self.value()


class ConfigStrWidget(QtWidgets.QLineEdit):
    def __init__(self, config, **kwds):
        super(ConfigStrWidget, self).__init__(**kwds)
        self.setText(config)

    def get_value(self):
        return self.text()


class ConfigEnumWidget(QtWidgets.QComboBox):
    def __init__(self, config, **kwds):
        super(ConfigEnumWidget, self).__init__(**kwds)
        for item in config.choices:
            self.addItem(item)
        if config.extendable:
            self.addItem('<new>')
        self.setCurrentIndex(self.findText(config))
        self.currentIndexChanged.connect(self.new_value)

    @QtCore.pyqtSlot(int)
    @catch_all
    def new_value(self, idx):
        value = str(self.itemText(idx))
        if value == '<new>':
            value, OK = QtWidgets.QInputDialog.getText(
                self, 'New option', 'Please enter a new option text')
            blocked = self.blockSignals(True)
            if OK:
                value = str(value)
                self.insertItem(idx, value)
            else:
                idx = 0
            self.setCurrentIndex(idx)
            self.blockSignals(blocked)

    def get_value(self):
        return self.currentText()


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
        for name in self.child_widgets:
            result[name] = self.child_widgets[name].get_value()
        return result


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


def ConfigCompoundWidget(config, **kwds):
    for value in config.values():
        if isinstance(value, ConfigParent):
            return ConfigGrandParentWidget(config, **kwds)
    return ConfigParentWidget(config, **kwds)


config_widget = {
    ConfigEnum        : ConfigEnumWidget,
    ConfigFloat       : ConfigFloatWidget,
    ConfigParent      : ConfigCompoundWidget,
    ConfigBool        : ConfigBoolWidget,
    ConfigInt         : ConfigIntWidget,
    ConfigPath        : ConfigPathWidget,
    ConfigStr         : ConfigStrWidget,
    }

class ConfigDialog(QtWidgets.QDialog):
    def __init__(self, config, notify, **kwds):
        super(ConfigDialog, self).__init__(
            flags=QtCore.Qt.WindowStaysOnTopHint, **kwds)
        self.notify = notify
        self.setLayout(QtWidgets.QVBoxLayout())
        # central area
        self.main_area = config_widget[type(config)](config)
        self.layout().addWidget(self.main_area)
        # buttons
        buttons = QtWidgets.QDialogButtonBox()
        self.close_button = buttons.addButton(
            'Close', QtWidgets.QDialogButtonBox.AcceptRole)
        self.apply_button = buttons.addButton(
            'Apply', QtWidgets.QDialogButtonBox.ApplyRole)
        self.cancel_button = buttons.addButton(
            'Cancel', QtWidgets.QDialogButtonBox.RejectRole)
        buttons.clicked.connect(self.button_clicked)
        self.layout().addWidget(buttons)

    @QtCore.pyqtSlot(QtWidgets.QAbstractButton)
    @catch_all
    def button_clicked(self, button):
        if button in (self.apply_button, self.close_button):
            self.notify(self.main_area.get_value())
        if button in (self.cancel_button, self.close_button):
            self.close()


class ComponentLink(QtWidgets.QGraphicsPathItem):
    def __init__(self, source, outbox, dest, inbox, **kwds):
        super(ComponentLink, self).__init__(**kwds)
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsSelectable)
        self.setZValue(-10.0)
        self.source = source
        self.outbox = outbox
        self.dest = dest
        self.inbox = inbox
        self.redraw()

    @catch_all
    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
            if isinstance(value, QtCore.QVariant):
                value = value.toBool()
            pen = self.pen()
            if value:
                pen.setStyle(QtCore.Qt.DashLine)
            else:
                pen.setStyle(QtCore.Qt.SolidLine)
            self.setPen(pen)
        return super(ComponentLink, self).itemChange(change, value)

    def collides(self, x0, y0, x1, y1):
        line = QtWidgets.QGraphicsLineItem(x0, y0, x1, y1, self)
        collisions = line.collidingItems()
        line.setParentItem(None)
        for item in collisions:
            if item.parentItem() != self.parentItem():
                continue
            if isinstance(item, ComponentIcon):
                return True
            if item == self or not isinstance(item, ComponentLink):
                continue
            path = item.path()
            for n in range(1, path.elementCount()):
                p0 = path.elementAt(n - 1)
                p1 = path.elementAt(n)
                if x0 == x1:
                    # vertical line
                    if (p0.x == x0 and p1.x == x0
                            and max(p0.y, p1.y) > min(y0, y1)
                            and min(p0.y, p1.y) < max(y0, y1)):
                        return True
                else:
                    # horizontal line
                    if (p0.y == y0 and p1.y == y0
                            and max(p0.x, p1.x) > min(x0, x1)
                            and min(p0.x, p1.x) < max(x0, x1)):
                        return True
        return False

    def find_route(self, x0, y0, x1, xn, yn):
        if xn - 10 < x1:
            # backwards link, 5 segments
            if yn >= y0:
                dy = 10
            else:
                dy = -10
            x2 = xn - 10
            for y1 in range(int(y0) + dy, int(yn), dy):
                if not self.collides(x1, y1, x2, y1):
                    return ((x0, y0), (x1, y0), (x1, y1),
                            (x2, y1), (x2, yn), (xn, yn))
            else:
                # draw direct line
                return ((x0, y0), (xn, yn))
        # try single line
        if yn == y0:
            if not self.collides(x0, y0, xn - 2, yn):
                return ((x0, y0), (xn, yn))
        # try 3-segment line
        if not (self.collides(x1, y0, x1, yn)
                or self.collides(x1, yn, xn - 2, yn)):
            return ((x0, y0), (x1, y0), (x1, yn), (xn, yn))
        # try 5-segment line
        x2 = xn - 10
        for yoff in range(0, 100, 10):
            for y1 in (y0 - yoff, y0 + yoff, yn - yoff, yn + yoff):
                if not self.collides(x1, y1, x2, y1):
                    return ((x0, y0), (x1, y0), (x1, y1),
                            (x2, y1), (x2, yn), (xn, yn))
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
        source_pos = self.source.outputs[self.outbox].scenePos()
        dest_pos = self.dest.inputs[self.inbox].scenePos()
        if self.parentItem():
            source_pos = self.mapFromScene(source_pos)
            dest_pos = self.mapFromScene(dest_pos)
        x0, y0 = source_pos.x() + 6, source_pos.y()
        x1 = x0 + 4 + (self.source.output_no[self.outbox] * 10)
        xn, yn = dest_pos.x(), dest_pos.y()
        points = self.smooth(self.find_route(x0, y0, x1, xn, yn))
        path = QtGui.QPainterPath(QtCore.QPointF(*points[0]))
        for point in points[1:]:
            path.lineTo(*point)
        self.setPath(path)


class IOIcon(QtWidgets.QGraphicsRectItem):
    def __init__(self, name, **kwds):
        super(IOIcon, self).__init__(**kwds)
        self.name = name
        self.setAcceptDrops(True)
        # draw an invisible rectangle to define drag-and-drop area
        pen = self.pen()
        pen.setStyle(QtCore.Qt.NoPen)
        self.setPen(pen)
        self.setRect(-3, -8, 13, 17)
        # draw a smaller visible triangle
        self.triangle = QtWidgets.QGraphicsPolygonItem(
            QtGui.QPolygonF([QtCore.QPointF(0, -5),
                             QtCore.QPointF(6, 0),
                             QtCore.QPointF(0, 5),
                             QtCore.QPointF(0, -5)]), self)
        # create label
        self.label = QtWidgets.QGraphicsSimpleTextItem(name, parent=self)
        font = self.label.font()
        font.setPointSizeF(font.pointSize() * 0.75)
        self.label.setFont(font)

    def mousePressEvent(self, event):
        pass

    @catch_all
    def mouseMoveEvent(self, event):
        start_pos = event.buttonDownScreenPos(QtCore.Qt.LeftButton)
        if (QtCore.QLineF(event.screenPos(), start_pos).length() <
                                        QtWidgets.QApplication.startDragDistance()):
            return
        start_pos = event.buttonDownScenePos(QtCore.Qt.LeftButton)
        drag = QtGui.QDrag(event.widget())
        mimeData = QtCore.QMimeData()
        mimeData.setData(self.mime_type, cPickle.dumps(start_pos))
        drag.setMimeData(mimeData)
        dropAction = drag.exec_(QtCore.Qt.LinkAction)

    @catch_all
    def dragEnterEvent(self, event):
        event.setAccepted(event.mimeData().hasFormat(self.link_mime_type))

    @catch_all
    def dropEvent(self, event):
        if not event.mimeData().hasFormat(self.link_mime_type):
            return super(IOIcon, self).dropEvent(event)
        start_pos = cPickle.loads(event.mimeData().data(self.link_mime_type).data())
        link_from = self.scene().itemAt(start_pos, self.transform())
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

    def __init__(self, *args, **kwds):
        super(InputIcon, self).__init__(*args, **kwds)
        # set label position
        br = self.label.boundingRect()
        self.label.setPos(8, -br.height() / 2)

    def connect_pos(self):
        return self.scenePos()


class OutputIcon(IOIcon):
    mime_type = _OUTPUT_MIMETYPE
    link_mime_type = _INPUT_MIMETYPE

    def __init__(self, *args, **kwds):
        super(OutputIcon, self).__init__(*args, **kwds)
        # set label position
        br = self.label.boundingRect()
        self.label.setPos(-(2 + br.width()), -br.height() / 2)

    def connect_pos(self):
        pos = self.scenePos()
        pos.setX(pos.x() + 6)
        return pos


py_class = re.compile(':py:class:`(~[\w\.]*\.)?(.*?)`')
py_mod = re.compile(':py:mod:`\.*(\S*)(\s*<[\w\.]*>)?`')
py_other = re.compile(':py:(data|func|meth|obj):`(.*?)`')

def strip_sphinx_domains(text):
    text = py_class.sub(r'*\2*', text)
    text = py_mod.sub(r'*\1*', text)
    text = py_other.sub(r'*\2*', text)
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
            pen.setStyle(QtCore.Qt.DashDotLine)
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
        self.input_no = {}
        for idx, name in enumerate(obj.inputs):
            self.inputs[name] = InputIcon(name, parent=self)
            self.inputs[name].setPos(0, 60 + (idx * 20))
            self.input_no[name] = idx
        # outputs
        self.outputs = {}
        self.output_no = {}
        for idx, name in enumerate(obj.outputs):
            self.outputs[name] = OutputIcon(name, parent=self)
            self.outputs[name].setPos(self.width, 60 + (idx * 20))
            self.output_no[name] = idx

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
            text, QtCore.Qt.ElideRight, max_width))
        text_width = class_label.boundingRect().width()
        if self.width > 120:
            class_label.setPos((self.width - 5) - text_width, 9)
        else:
            class_label.setPos(5, 30)


class ComponentIcon(ComponentOutline):
    def __init__(self, name, obj, **kwds):
        super(ComponentIcon, self).__init__(name, obj, **kwds)
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable |
                      QtWidgets.QGraphicsItem.ItemIsSelectable |
                      QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
        self.obj = obj
        self.config_dialog = None
        # context menu actions
        self.context_menu_actions = [
            ('Rename',    self.rename),
            ('Delete',    self.delete),
            ('Configure', self.do_config),
            ]
        # set icon's tooltip
        help_text = inspect.getdoc(self.obj)
        if help_text:
            help_text = strip_sphinx_domains(help_text)
            help_text = docutils.core.publish_parts(
                help_text, writer_name='html')['html_body']
        else:
            help_text = '<p>Undocumented</p>'
        help_text = '<h4>{}()</h4>\n{}\n<p>File: {}</p>'.format(
            self.obj.__class__.__name__, help_text,
            inspect.getfile(self.obj.__class__))
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
                self.obj.get_config(), self.new_config,
                parent=self.scene().views()[0])
            self.config_dialog.setWindowTitle('%s configuration' % self.name)
            self.config_dialog.show()

    def new_config(self, config):
        self.obj.set_config(config)

    def regenerate(self):
        config = self.obj.get_config()
        self.obj = self.obj.__class__(config=config)
        return self.name, self.obj

    @catch_all
    def contextMenuEvent(self, event):
        event.accept()
        menu = QtWidgets.QMenu()
        actions = {}
        for label, method in self.context_menu_actions:
            actions[menu.addAction(label)] = method
        action = menu.exec_(event.screenPos())
        if action:
            actions[action]()
        self.ungrabMouse()

    @catch_all
    def mouseDoubleClickEvent(self, event):
        self.do_config()

    @catch_all
    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            if isinstance(value, QtCore.QVariant):
                value = value.toPointF()
            value.setX(value.x() + 5 - ((value.x() + 5) % 10))
            value.setY(value.y() + 5 - ((value.y() + 5) % 10))
            return value
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged and self.scene():
            if isinstance(value, QtCore.QVariant):
                value = value.toPointF()
            self.scene().parent().status.setText(
                'position: {}, {}'.format(value.x(), value.y()))
            for link in self.scene().matching_items(ComponentLink):
                # redraw all links in case component is now on top of one
                link.redraw()
            self.scene().update_scene_rect(no_shrink=True)
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged and self.scene():
            if value:
                self.scene().parent().status.setText('position: {}, {}'.format(
                    self.scenePos().x(), self.scenePos().y()))
            else:
                self.scene().parent().status.clear()
        return super(ComponentIcon, self).itemChange(change, value)


class CompoundIcon(ComponentIcon):
    def __init__(self, name, obj, expanded=False, **kwds):
        self.expanded = expanded
        super(CompoundIcon, self).__init__(name, obj, **kwds)
        self.context_menu_actions.append(
            ('Expand/contract', self.expand_contract))
        # draw internals if needed
        self.set_expanded()

    def expand_contract(self):
        old_w, old_h = self.width, self.height
        self.expanded = not self.expanded
        self.set_expanded()
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
        self.scene().update_scene_rect(no_shrink=True)

    def position_component(self, component_name, pos, dx, dy):
        if component_name == 'self':
            return
        if self.recurse_depth[component_name] > 2:
            return
        self.recurse_depth[component_name] += 1
        # find "ideal" position based on components connected to inputs
        new_pos = None
        in_no = 0
        for src, dst in self.obj.input_connections(component_name):
            connected = src[0]
            if connected in pos:
                out_no = 0
                for s, d in self.obj.output_connections(connected):
                    if d[0] == component_name:
                        break
                    out_no += 1
                x = pos[connected][0] + dx
                y = pos[connected][1] + (dy * (out_no - in_no))
                if new_pos:
                    new_pos = [max(new_pos[0], x), min(new_pos[1], y)]
                else:
                    new_pos = [x, y]
            in_no += 1
        # if no connected input, use connected outputs
        if not new_pos:
            out_no = 0
            for src, dst in self.obj.output_connections(component_name):
                connected = dst[0]
                if connected in pos:
                    in_no = 0
                    for s, d in self.obj.input_connections(connected):
                        if s[0] == component_name:
                            break
                        in_no += 1
                    x = pos[connected][0] - dx
                    y = pos[connected][1] - (dy * (out_no - in_no))
                    if new_pos:
                        new_pos = [min(new_pos[0], x), max(new_pos[1], y)]
                    else:
                        new_pos = [x, y]
                out_no += 1
        # if no connected output, use origin
        if not new_pos:
            new_pos = [0, 0]
        pos[component_name] = new_pos
        # position components connected to inputs
        for src, dst in self.obj.input_connections(component_name):
            self.position_component(src[0], pos, dx, dy)
        # position components connected to outputs
        for src, dst in self.obj.output_connections(component_name):
            self.position_component(dst[0], pos, dx, dy)
        # final check for collisions
        new_pos = pos[component_name]
        del pos[component_name]
        while new_pos in pos.values():
            new_pos[1] += dy
        pos[component_name] = new_pos
        self.recurse_depth[component_name] -= 1

    def set_expanded(self):
        # delete previous version
        for child in self.childItems():
            if isinstance(child, IOIcon):
                continue
            if child in (self.name_label, self.surround):
                continue
            child.setParentItem(None)
        child_comps = {}
        if self.expanded and self.obj._compound_children:
            # create components and get max size
            dx, dy = 0, 0
            for name, obj in self.obj._compound_children.items():
                child = ComponentOutline(name, obj, parent=self)
                child.setEnabled(False)
                dx = max(dx, child.width + 40)
                dy = max(dy, child.height + 20)
                child_comps[name] = child
            # position components according to linkages
            pos = {}
            self.recurse_depth = defaultdict(int)
            while len(pos) < len(child_comps):
                for name in child_comps:
                    if name not in pos:
                        self.position_component(name, pos, dx, dy)
                        break
            x_min, y_min = pos[list(pos.keys())[0]]
            x_max, y_max = x_min, y_min
            for i in pos:
                x_min = min(x_min, pos[i][0])
                y_min = min(y_min, pos[i][1])
                x_max = max(x_max, pos[i][0])
                y_max = max(y_max, pos[i][1])
            for i in pos:
                pos[i][0] += 40 - x_min
                pos[i][1] += 30 - y_min
            # reposition components
            for name in pos:
                child_comps[name].setPos(*pos[name])
            self.width = (x_max - x_min) + dx + 40
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
            for (src, outbox), (dest, inbox) in self.obj.all_connections():
                if src == 'self':
                    source_pos = self.inputs[outbox].connect_pos()
                    source_pos.setX(source_pos.x() + 6)
                    dest_pos = child_comps[dest].inputs[inbox].connect_pos()
                elif dest == 'self':
                    dest_pos = self.outputs[inbox].connect_pos()
                    dest_pos.setX(dest_pos.x() - 6)
                    source_pos = child_comps[src].outputs[outbox].connect_pos()
                else:
                    link = ComponentLink(child_comps[src], outbox,
                                         child_comps[dest], inbox, parent=self)
                    link.setEnabled(False)
                    continue
                line = QtWidgets.QGraphicsLineItem(QtCore.QLineF(
                    self.mapFromScene(source_pos), self.mapFromScene(dest_pos)
                    ), self)
        if self.scene():
            self.scene().update_scene_rect(no_shrink=True)


class NetworkArea(QtWidgets.QGraphicsScene):
    min_size = QtCore.QRectF(0, 0, 800, 600)

    def __init__(self, **kwds):
        super(NetworkArea, self).__init__(**kwds)
        self.setSceneRect(self.min_size)
        self.runnable = None

    def dragEnterEvent(self, event):
        if not event.mimeData().hasFormat(_COMP_MIMETYPE):
            return super(NetworkArea, self).dragEnterEvent(event)
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        if not event.mimeData().hasFormat(_COMP_MIMETYPE):
            return super(NetworkArea, self).dragMoveEvent(event)
        self.parent().status.clear()

    def dragMoveEvent(self, event):
        if not event.mimeData().hasFormat(_COMP_MIMETYPE):
            return super(NetworkArea, self).dragMoveEvent(event)
        self.parent().status.setText('position: {}, {}'.format(
            event.scenePos().x(), event.scenePos().y()))

    @catch_all
    def dropEvent(self, event):
        if not event.mimeData().hasFormat(_COMP_MIMETYPE):
            return super(NetworkArea, self).dropEvent(event)
        self.parent().status.clear()
        data = event.mimeData().data(_COMP_MIMETYPE).data()
        klass = cPickle.loads(data)
        self.add_component(klass, event.scenePos())

    def keyPressEvent(self, event):
        if not event.matches(QtGui.QKeySequence.Delete):
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
        self.removeItem(child)

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

    def new_component(self, name, obj, position, expanded=False,
                      parent=None, config={}):
        if config:
            obj.set_config(config)
        if isinstance(obj, Compound):
            component = CompoundIcon(
                name, obj, parent=parent, expanded=expanded)
        else:
            component = ComponentIcon(name, obj, parent=parent)
        component.setPos(position)
        if not parent:
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

    @QtCore.pyqtSlot()
    @catch_all
    def run_graph(self):
        self.stop_graph()
        # create compound component and run it
        components = {}
        for child in self.matching_items(ComponentIcon):
            name, obj = child.regenerate()
            components[name] = obj
        self.runnable = Compound(linkages=self.get_linkages(), **components)
        self.runnable.start()

    @QtCore.pyqtSlot()
    @catch_all
    def stop_graph(self):
        if self.runnable:
            self.runnable.stop()
            self.runnable = None

    def load_script(self, file_name):
        global ComponentNetwork, Network

        with open(file_name) as f:
            code = f.read()
        if 'Network' not in code:
            # not a recognised script
            logger.error('Script not recognised')
            return
        code = compile(code, file_name, 'exec')
        ComponentNetwork = None
        Network = None
        try:
            exec(code, globals())
        except ImportError as ex:
            logger.error(str(ex))
        for child in self.items():
            self.removeItem(child)
        if ComponentNetwork:
            logger.info('New style network')
            network = ComponentNetwork()
        elif Network:
            logger.info('Old style network')
            factory = Network()
            network = factory.make()
            network.positions = {}
            network.expanded = {}
            for name, comp in factory.components.items():
                network.positions[name] = comp['pos']
                if 'expanded' in comp:
                    network.expanded[name] = comp['expanded']
        else:
            # not a recognised script
            logger.error('Script not recognised')
            return
        comps = {}
        # add component icons
        for name, comp in network._compound_children.items():
            kw = {'config': comp.get_config()}
            if name in network.expanded:
                kw['expanded'] = network.expanded[name]
            comps[name] = self.new_component(
                name, comp, QtCore.QPointF(*network.positions[name]), **kw)
        # add link icons
        for name in comps:
            for ((src, outbox),
                 (dest, inbox)) in network.output_connections(name):
                link = ComponentLink(comps[src], outbox, comps[dest], inbox)
                self.addItem(link)
        for link in self.matching_items(ComponentLink):
            # redraw all links in case of collisions
            link.redraw()
        self.views()[0].centerOn(self.itemsBoundingRect().center())

    def save_script(self, file_name, needs_qt):
        components = {}
        modules = []
        positions = {}
        expanded = {}
        with_qt = False
        for child in self.matching_items(ComponentIcon):
            name = child.name
            obj = child.obj
            mod = obj.__class__.__module__
            config = obj.get_config()
            config=('\n' + (' ' * 23)).join(pprint.pformat(
                dict(config), width=80-23, compact=True).splitlines())
            components[name] = {
                'class' : '{}.{}'.format(mod, obj.__class__.__name__),
                'config' : config,
                }
            positions[name] = (child.pos().x(), child.pos().y())
            if isinstance(child, CompoundIcon):
                expanded[name] = child.expanded
            if mod not in modules:
                modules.append(mod)
                with_qt = with_qt or needs_qt[mod]
        linkages = self.get_linkages()
        linkages=('\n' + (' ' * 23)).join(pprint.pformat(
            dict(linkages), width=80-23).splitlines())
        positions=('\n' + (' ' * 16)).join(pprint.pformat(
            positions, width=80-16).splitlines())
        expanded=('\n' + (' ' * 15)).join(pprint.pformat(
            expanded, width=80-15, compact=True).splitlines())
        modules.sort()
        with open(file_name, 'w') as of:
            of.write("""#!/usr/bin/env python
# File written by pyctools-editor. Do not edit.

import argparse
import logging
""")
            if with_qt:
                of.write('import sys\n\n'
                         'from PyQt5 import QtCore, QtWidgets\n')
            of.write('\nfrom pyctools.core.compound import Compound\n')
            for module in modules:
                of.write('import %s\n' % module)
            of.write("""
class ComponentNetwork(Compound):
    positions = {positions}
    expanded = {expanded}

    def __init__(self, config={{}}, **kwds):
        super(ComponentNetwork, self).__init__("""
                     .format(positions=positions, expanded=expanded))
            for name, component in components.items():
                of.write("""
            {name} = {class}(
                config={config}),""".format(name=name, **component))
            of.write("""
            linkages = {linkages},
            config = config, **kwds)

if __name__ == '__main__':
"""
                     .format(linkages=linkages))
            if with_qt:
                of.write('    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_X11InitThreads)\n'
                         '    app = QtWidgets.QApplication(sys.argv)\n')
            of.write("""
    comp = ComponentNetwork()
    cnf = comp.get_config()
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    cnf.parser_add(parser)
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='increase verbosity of log messages')
    args = parser.parse_args()
    logging.basicConfig(level=logging.ERROR - (args.verbose * 10))
    del args.verbose
    cnf.parser_set(args)
    comp.set_config(cnf)
    comp.start()
""")
            if with_qt:
                of.write('    app.exec_()\n')
            else:
                of.write("""
    try:
        comp.join(end_comps=True)
    except KeyboardInterrupt:
        pass
""")
            of.write("""
    comp.stop()
    comp.join()
""")


class ComponentItemModel(QtGui.QStandardItemModel):
    def mimeTypes(self):
        return [_COMP_MIMETYPE]

    def mimeData(self, index_list):
        if len(index_list) != 1:
            return None
        idx = index_list[0]
        if not idx.isValid():
            return None
        data = idx.data(QtCore.Qt.UserRole+1)
        if isinstance(data, QtCore.QVariant):
            data = data.toPyObject()
        if not data:
            return None
        result = QtCore.QMimeData()
        result.setData(_COMP_MIMETYPE,
                       cPickle.dumps(data, cPickle.HIGHEST_PROTOCOL))
        return result


class ComponentList(QtWidgets.QTreeView):
    def __init__(self, **kwds):
        super(ComponentList, self).__init__(**kwds)
        self.setModel(ComponentItemModel(self))
        self.setDragEnabled(True)
        self.setHeaderHidden(True)
        # get list of available components (and import them!)
        components = {}
        self.needs_qt = {}
        for module_loader, name, ispkg in pkgutil.walk_packages(
                path=pyctools.components.__path__,
                prefix='pyctools.components.'):
            # import module
            try:
                mod = __import__(name, globals(), locals(), ['*'])
            except ImportError:
                continue
            if not hasattr(mod, '__all__') or not mod.__all__:
                continue
            # convert 'pyctools.components.a.b.c' to components['a']['b']['c']
            parts = name.split('.')[2:]
            if len(mod.__all__) == 1:
                # single component in module
                parts = parts[:-1]
            # descend hierarchy to this module
            parent = components
            for part in parts:
                if part not in parent:
                    parent[part] = {}
                parent = parent[part]
            # add this module's components to hierarchy
            for comp in mod.__all__:
                parent[comp] = getattr(mod, comp)
            # try to find out if module needs Qt
            self.needs_qt[name] = False
            for item in dir(mod):
                if item in ('QtEventLoop', 'QtThreadEventLoop'):
                    self.needs_qt[name] = True
                    break
                if not 'Qt' in item:
                    continue
                item = getattr(mod, item)
                if not isinstance(item, types.ModuleType):
                    continue
                if item.__name__.startswith('PyQt'):
                    self.needs_qt[name] = True
                    break
        # build tree from list
        root_node = self.model().invisibleRootItem()
        self.add_nodes(root_node, components)
        root_node.sortChildren(0)
        self.resizeColumnToContents(0)
        self.updateGeometries()

    def add_nodes(self, root_node, components):
        for name, item in components.items():
            if item:
                node = QtGui.QStandardItem(name)
                node.setEditable(False)
                root_node.appendRow(node)
                if isinstance(item, dict):
                    self.add_nodes(node, item)
                else:
                    node.setData(item)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, script=None, **kwds):
        super(MainWindow, self).__init__(**kwds)
        self.setWindowTitle("Pyctools graph editor")
        self.script_file = os.getcwd()
        ## file menu
        file_menu = self.menuBar().addMenu('File')
        file_menu.addAction('Load script', self.load_script, 'Ctrl+O')
        file_menu.addAction('Save script', self.save_script, 'Ctrl+S')
        file_menu.addSeparator()
        quit_action = QtWidgets.QAction('Quit', self)
        quit_action.setShortcuts(['Ctrl+Q', 'Ctrl+W'])
        quit_action.triggered.connect(
            QtWidgets.QApplication.instance().closeAllWindows)
        file_menu.addAction(quit_action)
        ## zoom menu
        zoom_menu = self.menuBar().addMenu('Zoom')
        zoom_menu.addAction('Zoom in', self.zoom_in, 'Ctrl++')
        zoom_menu.addAction('Zoom out', self.zoom_out, 'Ctrl+-')
        zoom_menu.addSeparator()
        self.zoom_group = QtWidgets.QActionGroup(self)
        for zoom in (25, 35, 50, 70, 100, 141, 200):
            action = QtWidgets.QAction('%d%%' % zoom, self)
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
        self.component_list = ComponentList(parent=self)
        splitter.addWidget(self.component_list)
        self.network_area = NetworkArea(parent=self)
        self.view = QtWidgets.QGraphicsView(self.network_area)
        self.view.setAcceptDrops(True)
        self.view.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
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

    @QtCore.pyqtSlot()
    @catch_all
    def load_script(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Load file', self.script_file, 'Python scripts (*.py)')
        file_name = file_name[0]
        if file_name:
            self.set_window_title(file_name)
            self.network_area.load_script(file_name)

    @QtCore.pyqtSlot()
    @catch_all
    def save_script(self):
        file_name = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save file', self.script_file, 'Python scripts (*.py)')
        file_name = file_name[0]
        if file_name:
            self.set_window_title(file_name)
            self.network_area.save_script(
                file_name, self.component_list.needs_qt)

    def set_window_title(self, file_name):
        self.script_file = file_name
        self.setWindowTitle(
            "Pyctools graph editor - %s" % os.path.basename(file_name))

    @QtCore.pyqtSlot()
    @catch_all
    def zoom_in(self):
        self.inc_zoom(1)

    @QtCore.pyqtSlot()
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

    @QtCore.pyqtSlot()
    @catch_all
    def set_zoom(self):
        current_action = self.zoom_group.checkedAction()
        zoom = float(current_action.data()) / 100.0
        self.view.resetTransform()
        self.view.scale(zoom, zoom)


def main():
    # let PyQt handle its options (need at least one argument after options)
    sys.argv.append('xxx')
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_X11InitThreads)
    app = QtWidgets.QApplication(sys.argv)
    del sys.argv[-1]
    # get command args
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-s', '--script', metavar='file_name',
                        help='a script to load at startup')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='increase verbosity of log messages')
    args = parser.parse_args(sys.argv[1:])
    logging.basicConfig(level=logging.ERROR - (args.verbose * 10))
    # create GUI and run application event loop
    main = MainWindow(script=args.script)
    main.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())

#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-17  Pyctools contributors
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
import logging
import os
import pprint
import re
import six
from six.moves import cPickle
import pkgutil
import sys
import types

import pyctools.components
from pyctools.core.compound import Compound
from pyctools.core.config import *
from pyctools.core.qt import qt_version_info, Qt, QtCore, QtGui, QtWidgets

logger = logging.getLogger('pyctools-editor')

_COMP_MIMETYPE = 'application/x-pyctools-component'
_INPUT_MIMETYPE = 'application/x-pyctools-component-input'
_OUTPUT_MIMETYPE = 'application/x-pyctools-component-output'

class ConfigPathWidget(QtWidgets.QPushButton):
    def __init__(self, config, **kwds):
        super(ConfigPathWidget, self).__init__(**kwds)
        self.config = config
        self.show_value(self.config.get())
        self.clicked.connect(self.set_value)

    def set_value(self):
        value = self.config.get()
        if value:
            directory = value
        else:
            directory = ''
        if self.config.exists:
            value = QtWidgets.QFileDialog.getOpenFileName(
                self, 'Choose file', directory)
        else:
            value = QtWidgets.QFileDialog.getSaveFileName(
                self, 'Choose file', directory)
        if qt_version_info >= (5,):
            value = value[0]
        if value:
            self.config.set(value)
            self.show_value(value)

    def show_value(self, value):
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

class ConfigBoolWidget(QtWidgets.QCheckBox):
    def __init__(self, config, **kwds):
        super(ConfigBoolWidget, self).__init__(**kwds)
        self.config = config
        self.setChecked(self.config.get())
        self.stateChanged.connect(self.config.set)

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
        self.setValue(self.config.get())
        self.valueChanged.connect(self.config.set)

class ConfigFloatWidget(QtWidgets.QDoubleSpinBox):
    def __init__(self, config, **kwds):
        super(ConfigFloatWidget, self).__init__(**kwds)
        self.config = config
        self.setDecimals(self.config.decimals)
        if self.config.min_value is None:
            self.setMinimum(-(2**31))
        else:
            self.setMinimum(self.config.min_value)
        if self.config.max_value is None:
            self.setMaximum((2**31)-1)
        else:
            self.setMaximum(self.config.max_value)
        self.setWrapping(self.config.wrapping)
        self.setValue(self.config.get())
        self.valueChanged.connect(self.config.set)

class ConfigStrWidget(QtWidgets.QLineEdit):
    def __init__(self, config, **kwds):
        super(ConfigStrWidget, self).__init__(**kwds)
        self.config = config
        value = self.config.get()
        if value is None:
            value = ''
        self.setText(value)
        self.editingFinished.connect(self.set_value)

    def set_value(self):
        self.config.set(str(self.text()))

class ConfigEnumWidget(QtWidgets.QComboBox):
    def __init__(self, config, **kwds):
        super(ConfigEnumWidget, self).__init__(**kwds)
        self.config = config
        for item in self.config.choices:
            self.addItem(item)
        if self.config.extendable:
            self.addItem('<new>')
        self.setCurrentIndex(self.findText(self.config.get()))
        self.currentIndexChanged.connect(self.new_value)

    @QtCore.pyqtSlot(int)
    def new_value(self, idx):
        value = str(self.itemText(idx))
        if value == '<new>':
            value, OK = QtWidgets.QInputDialog.getText(
                self, 'New option', 'Please enter a new option text')
            if not OK:
                return
            value = str(value)
            blocked = self.blockSignals(True)
            self.insertItem(idx, value)
            self.setCurrentIndex(idx)
            self.blockSignals(blocked)
        self.config.set(value)

class ConfigParentWidget(QtWidgets.QWidget):
    def __init__(self, config, **kwds):
        super(ConfigParentWidget, self).__init__(**kwds)
        self.config = config
        self.setLayout(QtWidgets.QFormLayout())
        for name in sorted(self.config.value):
            child = self.config.value[name]
            widget = config_widget[type(child)](child)
            self.layout().addRow(name, widget)

class ConfigGrandParentWidget(QtWidgets.QTabWidget):
    def __init__(self, config, **kwds):
        super(ConfigGrandParentWidget, self).__init__(**kwds)
        self.config = config
        for name in sorted(self.config.value):
            child = self.config.value[name]
            widget = config_widget[type(child)](child)
            self.addTab(widget, name)

config_widget = {
    ConfigEnum        : ConfigEnumWidget,
    ConfigFloat       : ConfigFloatWidget,
    ConfigGrandParent : ConfigGrandParentWidget,
    ConfigBool        : ConfigBoolWidget,
    ConfigInt         : ConfigIntWidget,
    ConfigParent      : ConfigParentWidget,
    ConfigPath        : ConfigPathWidget,
    ConfigStr         : ConfigStrWidget,
    }

class ConfigDialog(QtWidgets.QDialog):
    def __init__(self, parent, **kwds):
        super(ConfigDialog, self).__init__(flags=Qt.WindowStaysOnTopHint, **kwds)
        self.setWindowTitle('%s configuration' % parent.name)
        self.component = parent
        self.config = self.component.obj.get_config()
        self.setLayout(QtWidgets.QGridLayout())
        self.layout().setColumnStretch(0, 1)
        # central area
        main_area = config_widget[type(self.config)](self.config)
        self.layout().addWidget(main_area, 0, 0, 1, 4)
        # buttons
        cancel_button = QtWidgets.QPushButton('Cancel')
        cancel_button.clicked.connect(self.close)
        self.layout().addWidget(cancel_button, 1, 1)
        apply_button = QtWidgets.QPushButton('Apply')
        apply_button.clicked.connect(self.apply_changes)
        self.layout().addWidget(apply_button, 1, 2)
        close_button = QtWidgets.QPushButton('Close')
        close_button.clicked.connect(self.apply_and_close)
        self.layout().addWidget(close_button, 1, 3)

    def apply_and_close(self):
        self.apply_changes()
        self.close()

    def apply_changes(self):
        self.component.obj.set_config(self.config)

class ComponentLink(QtWidgets.QGraphicsLineItem):
    def __init__(self, source, outbox, dest, inbox, **kwds):
        super(ComponentLink, self).__init__(**kwds)
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsSelectable)
        self.source = source
        self.outbox = outbox
        self.dest = dest
        self.inbox = inbox
        self.renew()

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemSceneHasChanged:
            if self.scene():
                self.redraw()
        elif change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
            pen = self.pen()
            if isinstance(value, QtCore.QVariant):
                value = value.toBool()
            if value:
                pen.setStyle(Qt.DashLine)
            else:
                pen.setStyle(Qt.SolidLine)
            self.setPen(pen)
        return super(ComponentLink, self).itemChange(change, value)

    def renew(self):
        self.source.connect(self.outbox, self.dest, self.inbox)

    def redraw(self):
        source_pos = self.source.out_pos(self.outbox, None)
        dest_pos = self.dest.in_pos(self.inbox, source_pos)
        source_pos = self.source.out_pos(self.outbox, dest_pos)
        self.setLine(QtCore.QLineF(source_pos, dest_pos))

class IOIcon(QtWidgets.QGraphicsRectItem):
    def __init__(self, name, **kwds):
        super(IOIcon, self).__init__(**kwds)
        self.name = name
        self.setAcceptDrops(True)
        # draw an invisible rectangle to define drag-and-drop area
        pen = self.pen()
        pen.setStyle(Qt.NoPen)
        self.setPen(pen)
        self.setRect(-3, -8, 13, 17)
        # draw a smaller visible triangle
        self.triangle = QtWidgets.QGraphicsPolygonItem(
            QtGui.QPolygonF([QtCore.QPointF(0, -5),
                             QtCore.QPointF(6, 0),
                             QtCore.QPointF(0, 5),
                             QtCore.QPointF(0, -5)]), self)
        self.label = QtWidgets.QGraphicsSimpleTextItem(
            name, parent=self.parentItem())
        font = self.label.font()
        font.setPointSizeF(font.pointSize() * 0.75)
        self.label.setFont(font)

    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        start_pos = event.buttonDownScreenPos(Qt.LeftButton)
        if (QtCore.QLineF(event.screenPos(), start_pos).length() <
                                        QtWidgets.QApplication.startDragDistance()):
            return
        start_pos = event.buttonDownScenePos(Qt.LeftButton)
        drag = QtGui.QDrag(event.widget())
        mimeData = QtCore.QMimeData()
        mimeData.setData(self.mime_type, cPickle.dumps(start_pos))
        drag.setMimeData(mimeData)
        dropAction = drag.exec_(Qt.LinkAction)

    def dragEnterEvent(self, event):
        event.setAccepted(event.mimeData().hasFormat(self.link_mime_type))

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
        else:
            source = self.parentItem()
            outbox = self.name
            dest = link_from.parentItem()
            inbox = link_from.name
        for link in self.scene().matching_items(ComponentLink):
            if (link.source == source and link.outbox == outbox and
                                link.dest == dest and link.inbox == inbox):
                self.scene().removeItem(link)
        link = ComponentLink(source, outbox, dest, inbox)
        self.scene().addItem(link)

class InputIcon(IOIcon):
    mime_type = _INPUT_MIMETYPE
    link_mime_type = _OUTPUT_MIMETYPE

    def setPos(self, ax, ay):
        br = self.label.boundingRect()
        self.label.setPos(ax + 8, ay - (br.height() / 2))
        super(InputIcon, self).setPos(ax, ay)

    def connect_pos(self):
        return self.scenePos()

class OutputIcon(IOIcon):
    mime_type = _OUTPUT_MIMETYPE
    link_mime_type = _INPUT_MIMETYPE

    def setPos(self, ax, ay):
        br = self.label.boundingRect()
        self.label.setPos(ax - 2 - br.width(), ay - (br.height() / 2))
        super(OutputIcon, self).setPos(ax, ay)

    def connect_pos(self):
        pos = self.scenePos()
        pos.setX(pos.x() + 6)
        return pos

class BasicComponentIcon(QtWidgets.QGraphicsPolygonItem):
    width = 100
    def __init__(self, name, klass, obj, **kwds):
        super(BasicComponentIcon, self).__init__(**kwds)
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable |
                      QtWidgets.QGraphicsItem.ItemIsSelectable |
                      QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
        self.name = name
        self.klass = klass
        self.obj = obj
        self.config_dialog = None
        # context menu actions
        self.context_menu_actions = [
            ('Rename',    self.rename_self),
            ('Delete',    self.delete_self),
            ('Configure', self.do_config),
            ]
        self.draw_icon()

    def draw_icon(self):
        # name label
        self.name_label = QtWidgets.QGraphicsSimpleTextItem(self.name, self)
        font = self.name_label.font()
        font.setBold(True)
        self.name_label.setFont(font)
        self.name_label.setPos(8, 8)
        # type label
        text = QtWidgets.QGraphicsSimpleTextItem(
            self.klass.__name__ + '()', self)
        font = text.font()
        font.setPointSizeF(font.pointSize() * 0.8)
        font.setItalic(True)
        text.setFont(font)
        text.setPos(8, 30)
        # inputs
        self.inputs = {}
        for idx, name in enumerate(self.obj.inputs):
            self.inputs[name] = InputIcon(name, parent=self)
            self.inputs[name].setPos(0, 100 + (idx * 20))
        # outputs
        self.outputs = {}
        for idx, name in enumerate(self.obj.outputs):
            self.outputs[name] = OutputIcon(name, parent=self)
            self.outputs[name].setPos(self.width, 100 + (idx * 20))

    def rename(self, name):
        self.name = name
        if self.config_dialog:
            self.config_dialog.setWindowTitle(
                '%s configuration' % self.name)
        self.name_label.setText(self.name)

    def in_pos(self, name, link_pos):
        return self.inputs[name].connect_pos()

    def out_pos(self, name, link_pos):
        return self.outputs[name].connect_pos()

    def connect(self, outbox, dest, inbox):
        if not self.isEnabled():
            return
        self.obj.connect(outbox, getattr(dest.obj, inbox))

    def renew(self):
        if not self.isEnabled():
            return
        config = self.obj.get_config()
        self.obj = self.klass()
        self.obj.set_config(config)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        actions = {}
        for label, method in self.context_menu_actions:
            actions[menu.addAction(label)] = method
        action = menu.exec_(event.screenPos())
        if action:
            actions[action]()

    def rename_self(self):
        self.scene().rename_component(self)

    def delete_self(self):
        self.scene().delete_child(self)

    def mouseDoubleClickEvent(self, event):
        self.do_config()

    def do_config(self):
        if not (self.config_dialog and self.config_dialog.isVisible()):
            self.config_dialog = ConfigDialog(self)
            self.config_dialog.show()
        self.config_dialog.raise_()
        self.config_dialog.activateWindow()

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            if isinstance(value, QtCore.QVariant):
                value = value.toPointF()
            value.setX(value.x() + 25 - ((value.x() + 25) % 50))
            value.setY(value.y() + 25 - ((value.y() + 25) % 50))
            return value
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged and self.scene():
            for link in self.scene().matching_items(ComponentLink):
                if link.source == self or link.dest == self:
                    link.redraw()
            self.scene().update_scene_rect(no_shrink=True)
        return super(BasicComponentIcon, self).itemChange(change, value)

class ComponentIcon(BasicComponentIcon):
    def draw_icon(self):
        super(ComponentIcon, self).draw_icon()
        height = 100 + (max(2, len(self.inputs), len(self.outputs)) * 20)
        self.setPolygon(QtGui.QPolygonF([QtCore.QPointF(0, 0),
                                         QtCore.QPointF(self.width, 0),
                                         QtCore.QPointF(self.width, height),
                                         QtCore.QPointF(0, height),
                                         QtCore.QPointF(0, 0)]))

class CompoundIcon(BasicComponentIcon):
    def __init__(self, name, klass, obj, **kwds):
        self.expanded = False
        self.child_comps = {}
        super(CompoundIcon, self).__init__(name, klass, obj, **kwds)
        self.context_menu_actions.append(
            ('Expand/contract', self.expand_contract))

    def expand_contract(self):
        old_w, old_h = self.width, self.height
        self.expanded = not self.expanded
        self.draw_icon()
        delta_x = self.width - old_w
        delta_y = self.height - old_h
        # move other components
        pos = self.scenePos()
        x = pos.x()
        y = pos.y()
        for child in self.scene().matching_items(BasicComponentIcon):
            if child == self or child in self.child_comps.values():
                continue
            pos = child.scenePos()
            if pos.x() >= x:
                child.moveBy(delta_x, 0)
            if pos.y() >= y + self.height:
                child.moveBy(0, delta_y)

    def draw_icon(self):
        # delete previous version
        for child in self.childItems():
            self.scene().removeItem(child)
        self.child_comps = {}
        if self.expanded:
            # position components according to linkages
            pos = {}
            # give all components the same start position
            for name in self.obj._compound_children:
                pos[name] = [50, 50]
            # move components down and/or right according to linkages
            while True:
                no_move = True
                for source in self.obj._compound_linkages:
                    src, outbox = source
                    targets = self.obj._compound_linkages[source]
                    if isinstance(targets[0], six.string_types):
                        # not a list of pairs, so make it into one
                        targets = zip(targets[0::2], targets[1::2])
                    for dest, inbox in targets:
                        if src == 'self' or dest == 'self':
                            continue
                        x = pos[src][0] + 150
                        if pos[dest][0] < x:
                            pos[dest][0] = x
                            no_move = False
                        y_off = (150 * (
                            self.obj._compound_children[dest].inputs.index(inbox) -
                            self.obj._compound_children[src].outputs.index(outbox)))
                        y = pos[src][1] - y_off
                        if pos[dest][1] < y:
                            pos[dest][1] = y
                            no_move = False
                        y = pos[dest][1] + y_off
                        if pos[src][1] < y:
                            pos[src][1] = y
                            no_move = False
                if no_move:
                    break
            x_min, y_min = pos[pos.keys()[0]]
            x_max, y_max = x_min, y_min
            for i in pos:
                x_min = min(x_min, pos[i][0])
                y_min = min(y_min, pos[i][1])
                x_max = max(x_max, pos[i][0])
                y_max = max(y_max, pos[i][1])
            for i in pos:
                pos[i][0] = 50 + pos[i][0] - x_min
                pos[i][1] = 50 + pos[i][1] - y_min
            # draw components
            for name, obj in self.obj._compound_children.items():
                child = self.scene().new_component(
                    name, obj.__class__, QtCore.QPointF(*pos[name]),
                    parent=self, obj=obj)
                child.setEnabled(False)
                self.child_comps[name] = child
            self.width = (x_max - x_min) + 200
            self.height = (y_max - y_min) + 230
        else:
            self.width = 100
            self.height = 100 + (
                20 * max(2, len(self.obj.inputs), len(self.obj.outputs)))
        # draw boundary
        self.setPolygon(QtGui.QPolygonF([QtCore.QPointF(0, 0),
                                         QtCore.QPointF(self.width, 0),
                                         QtCore.QPointF(self.width, self.height),
                                         QtCore.QPointF(0, self.height),
                                         QtCore.QPointF(0, 0)]))
        surround = QtWidgets.QGraphicsRectItem(
            -3, -3, self.width + 6, self.height + 6, self)
        pen = surround.pen()
        pen.setStyle(Qt.DashDotLine)
        surround.setPen(pen)
        # draw rest of icon, including inputs and outputs
        super(CompoundIcon, self).draw_icon()
        # draw linkages
        if self.expanded:
            for source in self.obj._compound_linkages:
                src, outbox = source
                targets = self.obj._compound_linkages[source]
                if isinstance(targets[0], six.string_types):
                    # not a list of pairs, so make it into one
                    targets = zip(targets[0::2], targets[1::2])
                for dest, inbox in targets:
                    if src == 'self':
                        source_pos = self.in_pos(outbox, None)
                        dest_pos = self.child_comps[dest].in_pos(inbox, source_pos)
                    elif dest == 'self':
                        dest_pos = self.out_pos(outbox, None)
                        source_pos = self.child_comps[src].out_pos(outbox, dest_pos)
                    else:
                        source_pos = self.child_comps[src].out_pos(outbox, None)
                        dest_pos = self.child_comps[dest].in_pos(inbox, source_pos)
                        source_pos = self.child_comps[src].out_pos(outbox, dest_pos)
                    line = QtWidgets.QGraphicsLineItem(QtCore.QLineF(
                        self.mapFromScene(source_pos), self.mapFromScene(dest_pos)
                        ), self)


class NetworkArea(QtWidgets.QGraphicsScene):
    min_size = QtCore.QRectF(0, 0, 800, 600)

    def __init__(self, **kwds):
        super(NetworkArea, self).__init__(**kwds)
        self.setSceneRect(self.min_size)

    def dragEnterEvent(self, event):
        if not event.mimeData().hasFormat(_COMP_MIMETYPE):
            return super(NetworkArea, self).dragEnterEvent(event)
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if not event.mimeData().hasFormat(_COMP_MIMETYPE):
            return super(NetworkArea, self).dragMoveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(_COMP_MIMETYPE):
            return super(NetworkArea, self).dropEvent(event)
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
        if isinstance(child, BasicComponentIcon):
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
            self.new_component(name, klass, position)

    def new_component(self, name, klass, position,
                      parent=None, obj=None, config={}):
        if not obj:
            obj = klass(config=config)
        elif config:
            cnf = obj.get_config()
            for key, value in config.items():
                cnf[key] = value
            obj.set_config(cnf)
        if isinstance(obj, Compound):
            component = CompoundIcon(name, klass, obj, parent=parent)
        else:
            component = ComponentIcon(name, klass, obj, parent=parent)
        component.setPos(position)
        if not parent:
            self.addItem(component)
        self.update_scene_rect()
        return component

    def rename_component(self, component):
        old_name = component.name
        component.name = None
        name = self.get_unique_name(old_name)
        component.name = old_name
        if name:
            component.rename(name)

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
        for child in self.matching_items(BasicComponentIcon):
            if child.name == name and child.isEnabled():
                return True
        return False

    def matching_items(self, klass):
        for child in self.items():
            if isinstance(child, klass):
                yield child

    def run_graph(self):
        # replace components with fresh instances
        for child in self.matching_items(BasicComponentIcon):
            if child.isEnabled():
                child.obj.stop()
                child.renew()
        # rebuild connections
        for child in self.matching_items(ComponentLink):
            child.renew()
        # run it!
        for child in self.matching_items(BasicComponentIcon):
            if child.isEnabled():
                child.obj.start()

    def stop_graph(self):
        for child in self.matching_items(BasicComponentIcon):
            if child.isEnabled():
                child.obj.stop()

    def load_script(self, file_name):
        global_vars = {}
        local_vars = {}
        with open(file_name) as f:
            code = compile(f.read(), file_name, 'exec')
            exec(code, global_vars, local_vars)
        if 'Network' not in local_vars:
            # not a recognised script
            logger.error('Script not recognised')
            return
        for child in self.items():
            self.removeItem(child)
        network = local_vars['Network']()
        comps = {}
        for name, comp in network.components.items():
            comps[name] = self.new_component(
                name, eval(comp['class']), QtCore.QPointF(*comp['pos']),
                config=eval(comp['config']))
        for source in network.linkages:
            src, outbox = source
            targets = network.linkages[source]
            if isinstance(targets[0], six.string_types):
                # not a list of pairs, so make it into one
                targets = zip(targets[0::2], targets[1::2])
            for dest, inbox in targets:
                link = ComponentLink(comps[src], outbox, comps[dest], inbox)
                self.addItem(link)
        self.views()[0].centerOn(self.itemsBoundingRect().center())

    def set_config(self, cnf, key, value):
        if isinstance(value, dict):
            for k, v in value.items():
                self.set_config(cnf[key], k, v)
        else:
            cnf[key] = value

    def save_script(self, file_name, needs_qt):
        components = {}
        modules = []
        linkages = defaultdict(list)
        with_qt = False
        for child in self.items():
            if isinstance(child, BasicComponentIcon) and child.isEnabled():
                mod = child.klass.__module__
                components[child.name] = {
                    'class' : '%s.%s' % (mod, child.klass.__name__),
                    'config' : repr(child.obj.get_config()),
                    'pos' : (child.pos().x(), child.pos().y()),
                    }
                if mod not in modules:
                    modules.append(mod)
                    with_qt = with_qt or needs_qt[mod]
            elif isinstance(child, ComponentLink):
                linkages[(child.source.name, child.outbox)].append(
                    (child.dest.name, child.inbox))
        linkages = dict(linkages)
        components = pprint.pformat(components, indent=4)
        linkages = pprint.pformat(linkages, indent=4)
        with open(file_name, 'w') as of:
            of.write("""#!/usr/bin/env python
# File written by pyctools-editor. Do not edit.

import argparse
import logging
from pyctools.core.compound import Compound
""")
            for module in modules:
                of.write('import %s\n' % module)
            of.write("""
class Network(object):
    components = \\
%s
    linkages = \\
%s

    def make(self):
        comps = {}
        for name, component in self.components.items():
            comps[name] = eval(component['class'])(config=eval(component['config']))
        return Compound(linkages=self.linkages, **comps)

if __name__ == '__main__':
""" % (components, linkages))
            if with_qt:
                of.write('    from pyctools.core.qt import Qt, QtWidgets\n' +
                         '    QtWidgets.QApplication.setAttribute(Qt.AA_X11InitThreads)\n' +
                         '    app = QtWidgets.QApplication([])\n')
            of.write("""
    comp = Network().make()
    cnf = comp.get_config()
    parser = argparse.ArgumentParser()
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
        data = idx.data(Qt.UserRole+1)
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
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        splitter.addWidget(self.view)
        splitter.setStretchFactor(1, 1)
        grid.addWidget(splitter, 0, 0, 1, 5)
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

    def load_script(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Load file', self.script_file, 'Python scripts (*.py)')
        if qt_version_info >= (5,):
            file_name = file_name[0]
        if file_name:
            self.set_window_title(file_name)
            self.network_area.load_script(file_name)

    def save_script(self):
        file_name = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save file', self.script_file, 'Python scripts (*.py)')
        if qt_version_info >= (5,):
            file_name = file_name[0]
        if file_name:
            self.set_window_title(file_name)
            self.network_area.save_script(
                file_name, self.component_list.needs_qt)

    def set_window_title(self, file_name):
        self.script_file = file_name
        self.setWindowTitle(
            "Pyctools graph editor - %s" % os.path.basename(file_name))

    def zoom_in(self):
        self.inc_zoom(1)

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

    def set_zoom(self):
        current_action = self.zoom_group.checkedAction()
        zoom = float(current_action.data()) / 100.0
        self.view.resetTransform()
        self.view.scale(zoom, zoom)

def main():
    # let PyQt handle its options (need at least one argument after options)
    sys.argv.append('xxx')
    QtWidgets.QApplication.setAttribute(Qt.AA_X11InitThreads)
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

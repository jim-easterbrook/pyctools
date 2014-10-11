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

import argparse
import cPickle as pickle
import pkgutil
import sys

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

import pyctools.components

_COMP_MIMETYPE = 'application/x-pyctools-component'
_INPUT_MIMETYPE = 'application/x-pyctools-component-input'
_OUTPUT_MIMETYPE = 'application/x-pyctools-component-output'

class ComponentLink(QtGui.QGraphicsLineItem):
    def __init__(self, source, dest, parent=None):
        super(ComponentLink, self).__init__(parent)
        self.source = source
        self.dest = dest
        self.redraw()

    def redraw(self):
        self.setLine(QtCore.QLineF(self.source.connect_pos(),
                                   self.dest.connect_pos()))

class IOIcon(QtGui.QGraphicsPolygonItem):
    def __init__(self, name, parent=None):
        super(IOIcon, self).__init__(parent)
        self.connected_to = []
        self.setPolygon(
            QtGui.QPolygonF(QtGui.QPolygon([0, -5, 6, 0, 0, 5, 0, -5])))
        self.setAcceptDrops(True)
        self.label = QtGui.QGraphicsSimpleTextItem(name, parent)
        font = self.label.font()
        font.setPointSizeF(font.pointSize() * 0.75)
        self.label.setFont(font)

    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        start_pos = event.buttonDownScreenPos(Qt.LeftButton)
        if (QtCore.QLineF(event.screenPos(), start_pos).length() <
                                        QtGui.QApplication.startDragDistance()):
            return
        start_pos = event.buttonDownScenePos(Qt.LeftButton)
        drag = QtGui.QDrag(event.widget())
        mimeData = QtCore.QMimeData()
        mimeData.setData(self.mime_type,
                         pickle.dumps(start_pos, pickle.HIGHEST_PROTOCOL))
        drag.setMimeData(mimeData)
        dropAction = drag.exec_(Qt.LinkAction)

    def dragEnterEvent(self, event):
        event.setAccepted(event.mimeData().hasFormat(self.link_mime_type))

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(self.link_mime_type):
            return super(IOIcon, self).dropEvent(event)
        start_pos = pickle.loads(event.mimeData().data(self.link_mime_type).data())
        source = self.scene().itemAt(start_pos)
        dest = self
        if isinstance(source, OutputIcon):
            source.connect_to(self)
        else:
            self.connect_to(source)

class InputIcon(IOIcon):
    mime_type = _INPUT_MIMETYPE
    link_mime_type = _OUTPUT_MIMETYPE

    def setPos(self, ax, ay):
        br = self.label.boundingRect()
        self.label.setPos(ax + 8, ay - (br.height() / 2))
        super(InputIcon, self).setPos(ax, ay)

    def redraw_connection(self):
        for partner in self.connected_to:
            if partner.connection:
                partner.connection.redraw()

    def connect_pos(self):
        pos = self.scenePos()
        return pos

class OutputIcon(IOIcon):
    mime_type = _OUTPUT_MIMETYPE
    link_mime_type = _INPUT_MIMETYPE

    def __init__(self, name, parent=None):
        super(OutputIcon, self).__init__(name, parent)
        self.connection = None

    def setPos(self, ax, ay):
        br = self.label.boundingRect()
        self.label.setPos(ax - 2 - br.width(), ay - (br.height() / 2))
        super(OutputIcon, self).setPos(ax, ay)

    def connect_to(self, other):
        if self.connection:
            self.scene().removeItem(self.connection)
            for partner in self.connected_to:
                self.connected_to.remove(partner)
                partner.connected_to.remove(self)
        self.connected_to.append(other)
        other.connected_to.append(self)
        self.connection = ComponentLink(self, other)
        self.scene().addItem(self.connection)

    def redraw_connection(self):
        if self.connection:
            self.connection.redraw()

    def connect_pos(self):
        pos = self.scenePos()
        pos.setX(pos.x() + 6)
        return pos

class ComponentIcon(QtGui.QGraphicsRectItem):
    def __init__(self, component, parent=None):
        super(ComponentIcon, self).__init__(parent)
        self.setFlags(QtGui.QGraphicsItem.ItemIsMovable |
                      QtGui.QGraphicsItem.ItemIsSelectable |
                      QtGui.QGraphicsItem.ItemSendsGeometryChanges)
        self.name = component.__name__
        self.setRect(0, 0, 100, 150)
        # create component
        self.component = component()
        # text label
        name = component.__name__
        self.text = QtGui.QGraphicsSimpleTextItem(name, self)
        self.text.setPos(10, 10)
        # inputs
        self.inputs = []
        for idx, name in enumerate(self.component.inputs):
            input = InputIcon(name, self)
            input.setPos(0, 100 + (idx * 20))
            self.inputs.append(input)
        # output
        self.outputs = []
        for idx, name in enumerate(self.component.outputs):
            output = OutputIcon(name, self)
            output.setPos(100, 100 + (idx * 20))
            self.outputs.append(output)

    def itemChange(self, change, value):
        if change == QtGui.QGraphicsItem.ItemPositionChange:
            pos = value.toPointF()
            pos.setX(pos.x() + 25 - ((pos.x() + 25) % 50))
            pos.setY(pos.y() + 25 - ((pos.y() + 25) % 50))
            return pos
        if change == QtGui.QGraphicsItem.ItemPositionHasChanged:
            for input in self.inputs:
                input.redraw_connection()
            for output in self.outputs:
                output.redraw_connection()
        return super(ComponentIcon, self).itemChange(change, value)

class NetworkArea(QtGui.QGraphicsScene):
    def __init__(self, parent=None):
        super(NetworkArea, self).__init__(parent)
        self.setSceneRect(0, 0, 800, 600)

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
        component = pickle.loads(data)
        icon = ComponentIcon(component)
        icon.setPos(event.scenePos())
        self.addItem(icon)
        self.update_scene_rect()

    def update_scene_rect(self):
        rect = self.itemsBoundingRect()
        rect.adjust(-150, -150, 150, 150)
        self.setSceneRect(rect.unite(self.sceneRect()))

class ComponentItemModel(QtGui.QStandardItemModel):
    def mimeTypes(self):
        return [_COMP_MIMETYPE]

    def mimeData(self, index_list):
        if len(index_list) != 1:
            return None
        idx = index_list[0]
        if not idx.isValid():
            return None
        data = idx.data(Qt.UserRole+1).toPyObject()
        if not data:
            return None
        result = QtCore.QMimeData()
        result.setData(_COMP_MIMETYPE,
                       pickle.dumps(data, pickle.HIGHEST_PROTOCOL))
        return result

class ComponentList(QtGui.QTreeView):
    def __init__(self, parent=None):
        super(ComponentList, self).__init__(parent)
        self.setModel(ComponentItemModel(self))
        self.setDragEnabled(True)
        self.setHeaderHidden(True)
        # get list of available components (and import them!)
        components = {}
        for module_loader, name, ispkg in pkgutil.walk_packages(
                path=pyctools.components.__path__,
                prefix='pyctools.components.'):
            parts = name.split('.')[2:]
            parent = components
            while parts:
                if parts[0] not in parent:
                    parent[parts[0]] = {}
                parent = parent[parts[0]]
                parts = parts[1:]
            mod = __import__(name, globals(), locals(), ['*'])
            if hasattr(mod, '__all__'):
                for comp in mod.__all__:
                    parent[comp] = getattr(mod, comp)
        # build tree from list
        root_node = self.model().invisibleRootItem()
        self.add_nodes(root_node, components)
        root_node.sortChildren(0)
        self.resizeColumnToContents(0)
        self.updateGeometries()

    def add_nodes(self, root_node, components):
        for name, item in components.iteritems():
            node = QtGui.QStandardItem(name)
            node.setEditable(False)
            root_node.appendRow(node)
            if isinstance(item, dict):
                self.add_nodes(node, item)
            else:
                node.setData(item)

class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("Pyctools network editor")
        # file menu
        file_menu = self.menuBar().addMenu('File')
        quit_action = QtGui.QAction('Quit', self)
        quit_action.setShortcuts(['Ctrl+Q', 'Ctrl+W'])
        quit_action.triggered.connect(
            QtGui.QApplication.instance().closeAllWindows)
        file_menu.addAction(quit_action)
        # main application area
        self.central_widget = QtGui.QSplitter(self)
        self.central_widget.setChildrenCollapsible(False)
        self.component_list = ComponentList(self)
        self.central_widget.addWidget(self.component_list)
        self.network_area = NetworkArea(self)
        view = QtGui.QGraphicsView(self.network_area)
        view.setAcceptDrops(True)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.central_widget.addWidget(view)
        self.central_widget.setStretchFactor(1, 1)
        self.setCentralWidget(self.central_widget)

def main():
    # let PyQt handle its options (need at least one argument after options)
    sys.argv.append('xxx')
    app = QtGui.QApplication(sys.argv)
    del sys.argv[-1]
    # get command args
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args(sys.argv[1:])
    # create GUI and run application event loop
    main = MainWindow()
    main.show()
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())

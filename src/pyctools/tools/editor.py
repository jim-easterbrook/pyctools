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
import logging
import cPickle as pickle
import pkgutil
import sys

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

import pyctools.components
from ..core.config import ConfigEnum, ConfigGrandParent, ConfigParent, ConfigInt, ConfigPath

_COMP_MIMETYPE = 'application/x-pyctools-component'
_INPUT_MIMETYPE = 'application/x-pyctools-component-input'
_OUTPUT_MIMETYPE = 'application/x-pyctools-component-output'

class ConfigPathWidget(QtGui.QPushButton):
    def __init__(self, config):
        super(ConfigPathWidget, self).__init__()
        self.config = config
        value = self.config.get()
        if value:
            self.setText(self.config.get())
        self.clicked.connect(self.get_value)

    def get_value(self):
        value = self.config.get()
        if value:
            directory = os.path.dirname(value)
        else:
            directory = ''
        value = str(QtGui.QFileDialog.getOpenFileName(
            self, 'Choose file', directory))
        if value:
            self.config.set(value)
            self.setText(value)

class ConfigIntWidget(QtGui.QSpinBox):
    def __init__(self, config):
        super(ConfigIntWidget, self).__init__()
        self.config = config
        self.setMinimum(max(self.config.min_value, -(2**31)))
        self.setMaximum(min(self.config.max_value,  (2**31)-1))
        self.setValue(self.config.get())
        self.valueChanged.connect(self.config.set)

class ConfigEnumWidget(QtGui.QComboBox):
    def __init__(self, config):
        super(ConfigEnumWidget, self).__init__()
        self.config = config
        for item in self.config.choices:
            self.addItem(item)
        self.setCurrentIndex(self.findText(self.config.get()))
        self.currentIndexChanged.connect(self.new_value)

    @QtCore.pyqtSlot(int)
    def new_value(self, idx):
        self.config.set(str(self.itemText(idx)))

class ConfigParentWidget(QtGui.QWidget):
    def __init__(self, config):
        super(ConfigParentWidget, self).__init__()
        self.config = config
        self.setLayout(QtGui.QFormLayout())
        for name, child in self.config.value.iteritems():
            widget = ConfigWidget(child)
            self.layout().addRow(name, widget)

class ConfigGrandParentWidget(QtGui.QTabWidget):
    def __init__(self, config):
        super(ConfigParentWidget, self).__init__()
        self.config = config
        for name, child in self.config.value.iteritems():
            widget = ConfigWidget(child)
            self.addTab(widget, name)

def ConfigWidget(config):
    if isinstance(config, ConfigGrandParent):
        return ConfigGrandParentWidget(config)
    elif isinstance(config, ConfigParent):
        return ConfigParentWidget(config)
    elif isinstance(config, ConfigPath):
        return ConfigPathWidget(config)
    elif isinstance(config, ConfigInt):
        return ConfigIntWidget(config)
    elif isinstance(config, ConfigEnum):
        return ConfigEnumWidget(config)
    else:
        raise RuntimeError('Unknown config type %s', config.__class__.__name__)

class ConfigDialog(QtGui.QDialog):
    def __init__(self, parent):
        super(ConfigDialog, self).__init__()
        self.setWindowTitle('%s configuration' % parent.id)
        self.component = parent.component
        self.config = self.component.get_config()
        self.setLayout(QtGui.QGridLayout())
        self.layout().setColumnStretch(0, 1)
        # central area
        main_area = ConfigWidget(self.config)
        self.layout().addWidget(main_area, 0, 0, 1, 4)
        # buttons
        cancel_button = QtGui.QPushButton('Cancel')
        cancel_button.clicked.connect(self.close)
        self.layout().addWidget(cancel_button, 1, 1)
        apply_button = QtGui.QPushButton('Apply')
        apply_button.clicked.connect(self.apply_changes)
        self.layout().addWidget(apply_button, 1, 2)
        close_button = QtGui.QPushButton('Close')
        close_button.clicked.connect(self.apply_and_close)
        self.layout().addWidget(close_button, 1, 3)

    def apply_and_close(self):
        self.apply_changes()
        self.close()

    def apply_changes(self):
        self.component.set_config(self.config)

class ComponentLink(QtGui.QGraphicsLineItem):
    def __init__(self, source, outbox, dest, inbox, parent=None):
        super(ComponentLink, self).__init__(parent)
        self.source = source
        self.outbox = outbox
        self.dest = dest
        self.inbox = inbox
        self.renew()
        self.redraw()

    def renew(self):
        self.source.component.bind(self.outbox, self.dest.component, self.inbox)

    def redraw(self):
        self.setLine(QtCore.QLineF(
            self.source.outputs[self.outbox].connect_pos(),
            self.dest.inputs[self.inbox].connect_pos()))

class IOIcon(QtGui.QGraphicsRectItem):
    def __init__(self, name, parent):
        super(IOIcon, self).__init__(parent)
        self.name = name
        self.setAcceptDrops(True)
        # draw an invisible rectangle to define drag-and-drop area
        pen = self.pen()
        pen.setStyle(Qt.NoPen)
        self.setPen(pen)
        self.setRect(-3, -8, 13, 17)
        # draw a smaller visible triangle
        self.triangle = QtGui.QGraphicsPolygonItem(
            QtGui.QPolygonF(QtGui.QPolygon([0, -5, 6, 0, 0, 5, 0, -5])), self)
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
        mimeData.setData(self.mime_type, pickle.dumps(start_pos))
        drag.setMimeData(mimeData)
        dropAction = drag.exec_(Qt.LinkAction)

    def dragEnterEvent(self, event):
        event.setAccepted(event.mimeData().hasFormat(self.link_mime_type))

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(self.link_mime_type):
            return super(IOIcon, self).dropEvent(event)
        start_pos = pickle.loads(event.mimeData().data(self.link_mime_type).data())
        source = self.scene().itemAt(start_pos)
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

    def connect_pos(self):
        return self.scenePos()

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

    def disconnect(self):
        if self.connection:
            self.scene().removeItem(self.connection)
            self.connection = None

    def connect_to(self, other):
        self.disconnect()
        self.connection = ComponentLink(
            self.parentItem(), self.name, other.parentItem(), other.name)
        self.scene().addItem(self.connection)

    def connect_pos(self):
        pos = self.scenePos()
        pos.setX(pos.x() + 6)
        return pos

class ComponentIcon(QtGui.QGraphicsRectItem):
    def __init__(self, comp_id, component_class, parent=None):
        super(ComponentIcon, self).__init__(parent)
        self.setFlags(QtGui.QGraphicsItem.ItemIsMovable |
                      QtGui.QGraphicsItem.ItemIsSelectable |
                      QtGui.QGraphicsItem.ItemSendsGeometryChanges)
        self.component_class = component_class
        self.name = self.component_class.__name__
        self.setRect(0, 0, 100, 150)
        self.config_dialog = None
        # create component
        self.id = comp_id
        self.component = self.component_class()
        # id label
        text = QtGui.QGraphicsSimpleTextItem(self.id, self)
        font = text.font()
        font.setBold(True)
        text.setFont(font)
        text.setPos(8, 8)
        # type label
        text = QtGui.QGraphicsSimpleTextItem(
            self.component.__class__.__name__ + '()', self)
        font = text.font()
        font.setPointSizeF(font.pointSize() * 0.8)
        font.setItalic(True)
        text.setFont(font)
        text.setPos(8, 30)
        # inputs
        self.inputs = {}
        for idx, name in enumerate(self.component.inputs):
            self.inputs[name] = InputIcon(name, self)
            self.inputs[name].setPos(0, 100 + (idx * 20))
        # output
        self.outputs = {}
        for idx, name in enumerate(self.component.outputs):
            self.outputs[name] = OutputIcon(name, self)
            self.outputs[name].setPos(100, 100 + (idx * 20))

    def renew(self):
        config = self.component.get_config()
        self.component = self.component_class()
        self.component.set_config(config)

    def mouseDoubleClickEvent(self, event):
        if self.config_dialog and self.config_dialog.isVisible():
            return
        self.config_dialog = ConfigDialog(self)
        self.config_dialog.show()
        self.config_dialog.raise_()
        self.config_dialog.activateWindow()

    def itemChange(self, change, value):
        if change == QtGui.QGraphicsItem.ItemPositionChange:
            pos = value.toPointF()
            pos.setX(pos.x() + 25 - ((pos.x() + 25) % 50))
            pos.setY(pos.y() + 25 - ((pos.y() + 25) % 50))
            return pos
        if change == QtGui.QGraphicsItem.ItemPositionHasChanged and self.scene():
            for item in self.scene().items():
                if not isinstance(item, ComponentLink):
                    continue
                if item.source == self or item.dest == self:
                    item.redraw()
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
        component_class = pickle.loads(data)
        self.add_component(component_class, event.scenePos())

    def update_scene_rect(self):
        rect = self.itemsBoundingRect()
        rect.adjust(-150, -150, 150, 150)
        self.setSceneRect(rect.unite(self.sceneRect()))

    def add_component(self, component_class, position):
        while True:
            base_name = filter(str.isupper, component_class.__name__).lower()
            comp_id = base_name
            n = 0
            while self.id_in_use(comp_id):
                comp_id = base_name + str(n)
                n += 1
            comp_id, OK = QtGui.QInputDialog.getText(
                self.views()[0], 'Component id',
                'Please enter a unique component id', text=comp_id)
            if not OK:
                return
            comp_id = str(comp_id)
            if not self.id_in_use(comp_id):
                break
        icon = ComponentIcon(comp_id, component_class)
        icon.setPos(position)
        self.addItem(icon)
        self.update_scene_rect()

    def id_in_use(self, comp_id):
        for child in self.items():
            if not isinstance(child, ComponentIcon):
                continue
            if child.id == comp_id:
                return True
        return False

    def run_graph(self):
        # replace components with fresh instances
        for child in self.items():
            if isinstance(child, ComponentIcon):
                child.component.stop()
                child.renew()
        # rebuild connections
        for child in self.items():
            if isinstance(child, ComponentLink):
                child.renew()
        # run it!
        for child in self.items():
            if isinstance(child, ComponentIcon):
                child.component.start()

    def stop_graph(self):
        for child in self.items():
            if isinstance(child, ComponentIcon):
                child.component.stop()

    def load_script(self, file_name):
        global_vars = {}
        local_vars = {}
        with open(file_name) as f:
            code = compile(f.read(), file_name, 'exec')
            exec(code, global_vars, local_vars)
        if 'Network' not in local_vars:
            # not a recognised script
            print 'Script not recognised'
            return
        network = local_vars['Network']()
        comps = {}
        for comp_id, comp in network.components.iteritems():
            comps[comp_id] = ComponentIcon(comp_id, eval(comp['class']))
            comps[comp_id].setPos(*comp['pos'])
            self.addItem(comps[comp_id])
            cnf = comps[comp_id].component.get_config()
            for key, value in eval(comp['config']).iteritems():
                cnf[key] = value
            comps[comp_id].component.set_config(cnf)
        for source, dest in network.linkages.iteritems():
            source, outbox = source
            dest, inbox = dest
            icon = ComponentLink(comps[source], outbox, comps[dest], inbox)
            self.addItem(icon)
        self.update_scene_rect()

    def save_script(self, file_name):
        components = {}
        modules = []
        linkages = {}
        for child in self.items():
            if isinstance(child, ComponentIcon):
                components[child.id] = {
                    'class' : '%s.%s' % (
                        child.component_class.__module__,
                        child.component_class.__name__),
                    'config' : repr(child.component.get_config()),
                    'pos' : (child.pos().x(), child.pos().y()),
                    }
                if child.component_class.__module__ not in modules:
                    modules.append(child.component_class.__module__)
            elif isinstance(child, ComponentLink):
                linkages[(child.source.id, child.outbox)] = (
                    child.dest.id, child.inbox)
        with open(file_name, 'w') as of:
            of.write("""#!/usr/bin/env python
# File written by pyctools-editor. Do not edit.

from PyQt4 import QtGui

from pyctools.core.compound import Compound

""")
            for module in modules:
                of.write('import %s\n' % module)
            of.write("""
class Network(object):
    def __init__(self):
        self.components = %s
        self.linkages = %s

    def make(self):
        comps = {}
        for comp_id, component in self.components.iteritems():
            comps[comp_id] = eval(component['class'])()
            cnf = comps[comp_id].get_config()
            for key, value in eval(component['config']).iteritems():
                cnf[key] = value
            comps[comp_id].set_config(cnf)
        return Compound(linkages=self.linkages, **comps)

if __name__ == '__main__':
    app = QtGui.QApplication([])
    comp = Network().make()
    comp.start()
    app.exec_()
    comp.stop()
    comp.join()
""" % (components, linkages))

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
        ## file menu
        file_menu = self.menuBar().addMenu('File')
        load_action = QtGui.QAction('Load script', self)
        load_action.setShortcuts(['Ctrl+L'])
        load_action.triggered.connect(self.load_script)
        file_menu.addAction(load_action)
        save_action = QtGui.QAction('Save script', self)
        save_action.setShortcuts(['Ctrl+S'])
        save_action.triggered.connect(self.save_script)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        quit_action = QtGui.QAction('Quit', self)
        quit_action.setShortcuts(['Ctrl+Q', 'Ctrl+W'])
        quit_action.triggered.connect(
            QtGui.QApplication.instance().closeAllWindows)
        file_menu.addAction(quit_action)
        ## main application area
        self.setCentralWidget(QtGui.QWidget())
        grid = QtGui.QGridLayout()
        grid.setColumnStretch(0, 1)
        self.centralWidget().setLayout(grid)
        # component list and network drawing area
        splitter = QtGui.QSplitter(self)
        splitter.setChildrenCollapsible(False)
        self.component_list = ComponentList(self)
        splitter.addWidget(self.component_list)
        self.network_area = NetworkArea(self)
        view = QtGui.QGraphicsView(self.network_area)
        view.setAcceptDrops(True)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        splitter.addWidget(view)
        splitter.setStretchFactor(1, 1)
        grid.addWidget(splitter, 0, 0, 1, 5)
        # buttons
        run_button = QtGui.QPushButton('run graph')
        run_button.clicked.connect(self.network_area.run_graph)
        grid.addWidget(run_button, 1, 3)
        stop_button = QtGui.QPushButton('stop graph')
        stop_button.clicked.connect(self.network_area.stop_graph)
        grid.addWidget(stop_button, 1, 4)

    def load_script(self):
        file_name = str(QtGui.QFileDialog.getOpenFileName(
            self, 'Load file', filter='Python scripts (*.py)'))
        if file_name:
            self.network_area.load_script(file_name)

    def save_script(self):
        file_name = str(QtGui.QFileDialog.getSaveFileName(
            self, 'Save file', filter='Python scripts (*.py)'))
        if file_name:
            self.network_area.save_script(file_name)

def main():
    logging.basicConfig(level=logging.DEBUG)
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

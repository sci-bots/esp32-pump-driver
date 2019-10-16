from __future__ import print_function, division
from collections import defaultdict
import logging
import os
logging.basicConfig(level=logging.INFO)

from PySide2 import QtGui, QtCore, QtWidgets

# For colors, see: https://gist.github.com/cfobel/fd939073cf13a309d7a9
light_blue = '#88bde6'
light_green = '#90cd97'



class FileDrop:
    copy_request = QtCore.Signal(list)

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.setDropAction(QtCore.Qt.CopyAction)
        event.accept()

    def dropEvent(self, event):
        event.setDropAction(QtCore.Qt.CopyAction)
        event.proposedAction()
        links = [u.url() for u in event.mimeData().urls()]
        # relative_root = tree.model().filePath(tree.rootIndex())
        self.copy_request.emit(links)


class HostFileTree(FileDrop, QtWidgets.QTreeView):
    pass


class RemoteFileList(FileDrop, QtWidgets.QListView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(QtCore.Qt.CopyAction)

    def mouseMoveEvent(self, e):
        mimeData = QtCore.QMimeData()
        drag = QtGui.QDrag(self)
        mimeData.setUrls(['remote://' + self.model().data(i) for i in self.selectedIndexes()])
        print(mimeData.urls())
        drag.setMimeData(mimeData)
        dropAction = drag.start(QtCore.Qt.CopyAction)


def host_tree(root_path='.'):
    tree = HostFileTree()
    model = QtWidgets.QFileSystemModel()
    model.setRootPath(root_path)
    tree.setModel(model)
    tree.setSortingEnabled(True)
    tree.setRootIndex(model.index(root_path))
    tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
    tree.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
    tree.setDropIndicatorShown(True)
    return tree


def copy(url, local_root):
    if url.startswith('remote://'):
        source = url[len('remote://'):]
        target = '/'.join([local_root, source[1:]
                           if source.startswith('/') else source])
        print('copy: `%s` to `%s`' % (url, target))
    elif url.startswith('file:///'):
        source = url[len('file:///'):]
        target = ('remote:///' +
                  os.path.relpath(source, local_root)).replace('\\', '/')
        print('copy: `%s` to `%s`' % (source, target))


def load_project_structure_(file_dict, tree):
    """
    Load Project structure tree
    :param startpath:
    :param tree:
    :return:
    """
    icon_provider = QtWidgets.QFileIconProvider()
    file_icon = icon_provider.icon(QtWidgets.QFileIconProvider.File)
    folder_icon = icon_provider.icon(QtWidgets.QFileIconProvider.Folder)

    for key, value in file_dict.items():
        if isinstance(value, dict):
            parent_itm = QtWidgets.QTreeWidgetItem(tree, [key])
            load_project_structure_(value, parent_itm)
            parent_itm.setIcon(0, folder_icon)
        else:
            for file in value:
                parent_itm = QtWidgets.QTreeWidgetItem(tree, [file])
                parent_itm.setIcon(0, file_icon)


FILE_MARKER = '<files>'


def attach(branch, trunk):
    '''
    Insert a branch of directories on its trunk.
    '''
    parts = branch.split('/', 1)
    if len(parts) == 1:  # branch is a file
        trunk[FILE_MARKER].append(parts[0])
    else:
        node, others = parts
        if node not in trunk:
            trunk[node] = defaultdict(dict, ((FILE_MARKER, []),))
        attach(others, trunk[node])


def list_to_tree(filenames):
    main_dict = defaultdict(dict, ((FILE_MARKER, []),))
    for filename in filenames:
        attach(filename, main_dict)
    return main_dict


class RemoteFileTree(FileDrop, QtWidgets.QTreeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(QtCore.Qt.CopyAction)

    def mouseMoveEvent(self, e):
        def filepath(item):
            name = item.data(0, 0)
            parents = []
            parent = item
            while True:
                parent = parent.parent()
                if parent is None:
                    break
                else:
                    parents.insert(0, parent.data(0, 0).rstrip('/'))
            result = '/'.join(parents + [name])
            if not result.startswith('/'):
                result = '/' + result
            return result

        mimeData = QtCore.QMimeData()
        drag = QtGui.QDrag(self)
        mimeData.setUrls(['remote://' + filepath(i) for i in self.selectedItems()])
        print(mimeData.urls())
        drag.setMimeData(mimeData)
        dropAction = drag.start(QtCore.Qt.CopyAction)

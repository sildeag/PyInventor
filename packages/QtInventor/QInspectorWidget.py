# QInspectorWidget class and helper classes implementation
# Author: Thomas Moeller
#
# Copyright (C) the PyInventor contributors. All rights reserved.
# This file is part of PyInventor, distributed under the BSD 3-Clause
# License. For full terms see the included COPYING file.
#
# Acknowledgements:
#   For the creation of the PyInventor scene graph editor the tutorials from Yasin Uludag's blog
#   on model view programming in Qt have been an indispensable resource. Thank you Yasin!
#   See also: http://www.yasinuludag.com/blog/?p=98
#

import inventor as iv
from PySide import QtCore, QtGui



class QSceneObjectProxy(QtCore.QObject):
    """
    This class wraps around actual Inventor scene objects and functions as a proxy
    for QtCore.QAbstractItemModel classes. While scene objects may have multiple
    parents, model nodes may not. Therefore an instance of QSceneObjectProxy is
    created for each child regardless of shared instances, thereby creating a one
    to one relationship between parents and children.
    """
    
    def __init__(self, sceneObject=None, parent=None, connectedFrom=None, connectedTo=None):
        """Initializes node instance (pass scene object and parent)"""
        super(QSceneObjectProxy, self).__init__()

        self._sceneObject = sceneObject
        self._name = ""
        self._children = []
        self._parent = parent
        self._connectedFrom = connectedFrom
        self._connectedTo = connectedTo
        
        if self._sceneObject is not None:
            self._name = sceneObject.get_name()

        if parent is not None:
            parent._children.append(self)

        if sceneObject is not None:
            self.initializeChildren(sceneObject)


    def createChildProxy(self, sceneObject, parent=None, connectedFrom=None, connectedTo=None):
        if not self.isInPath(sceneObject):
            node = QSceneObjectProxy(sceneObject, parent, connectedFrom, connectedTo)


    def isInPath(self, sceneObject):
        if self._sceneObject == sceneObject:
            return True
        if self.parent() is not None:
            return self.parent().isInPath(sceneObject)
        return False


    def initializeChildren(self, sceneObject, connectedFrom=None, connectedTo=None):
        if sceneObject is not None:
            # add all child nodes
            if isinstance(sceneObject, iv.Node):
                for child in sceneObject:
                    self.createChildProxy(child, self)

            # add nodekit parts
            if isinstance(sceneObject, iv.BaseKit):
                publicParts = [p["Name"] for p in sceneObject.get_nodekit_catalog() if p["Public"]]
                for part in publicParts:
                    if (sceneObject.get_field(part).value is not None):
                        self.createChildProxy(sceneObject.get_field(part).value, self, None, sceneObject.get_field(part))

            # add all objects connected through fields
            for field in sceneObject.get_field():
                for conn in field.get_connections():
                    if conn.get_container() is not None:
                        self.createChildProxy(conn.get_container(), self, conn, field)
                if field.get_connected_engine() is not None:
                    output = field.get_connected_engine()
                    self.createChildProxy(output.get_container(), self, output, field)


    def child(self, row):
        """Returns child node at given index"""
        return self._children[row]

    
    def childCount(self):
        """Returns number of children"""
        return len(self._children)

    
    def parent(self):
        """Returns parent node"""
        return self._parent

    
    def row(self):
        """Returns row index of this child relative to the parent node"""
        if self._parent is not None:
            return self._parent._children.index(self)

        return -1


    def isChildNode(self):
        return self._connectedFrom is None


    def title(self):
        """Returns the scene object display title"""
        title = ""

        if self._sceneObject is not None:
            title += self._sceneObject.get_type()
            if self._connectedFrom is not None:
                title += " " + self._connectedFrom.get_name()
            if self._connectedTo is not None:
                title += "->" + self._connectedTo.get_name()
        
        return title


    def type(self):
        """Returns the scene object type"""
        if self._sceneObject is None:
            return ""
        
        return self._sceneObject.get_type()


    def isGroup(self):
        """Returns True if the scene object is derived from Group"""
        if self._sceneObject is None:
            return False

        return self._sceneObject.check_type("Group")


    def name(self):
        """Returns scene object instance name"""
        if self._sceneObject is None:
            return ""

        return self._sceneObject.get_name()
    

    def setName(self, name):
        """Sets new scene object instance name"""
        if self._sceneObject is not None:
            self._sceneObject.set_name(name)
    

    def sceneObject(self):
        """Returns Inventor scene object represented by this proxy node"""
        return self._sceneObject


    def setSceneObject(self, node):
        """Sets a new Inventor scene object represented by this proxy node"""
        self._sceneObject = node


    def changeChildType(self, position, node):
        """Changes the type of a child node"""
        if (node is not None) and (position >= 0) and (position < len(self._children)):
            if isinstance(self._sceneObject, iv.BaseKit) and self._children[position]._connectedTo is not None:
                self._children[position]._connectedTo.value = node
            self._children[position].setSceneObject(node)
            if isinstance(self._sceneObject, iv.Group):
                self._sceneObject[position] = node
            self._children[position].initializeChildren(node)


    def insertChild(self, position, child):
        """Inserts a new child"""
        if position < 0 or position > len(self._children):
            return False

        self._children.insert(position, child)
        child._parent = self

        # insert child to scene object too
        if self._sceneObject is not None:
            if child._sceneObject is not None:
                self._sceneObject.insert(position, child._sceneObject)
            else:
                # insert label node as placeholder
                if isinstance(self._sceneObject, iv.Node):
                    self._sceneObject.insert(position, iv.Label())
            
        return True

    
    def removeChild(self, position):
        """Removes child"""
        if position < 0 or position > len(self._children):
            return False

        child = self._children.pop(position)
        child._parent = None

        if self._sceneObject is not None:
            # delete nodekit part
            if isinstance(self._sceneObject, iv.BaseKit):
                child._connectedTo.value = None
        
            # remove child from scene object
            if isinstance(self._sceneObject, iv.Group) and (position < len(self._sceneObject)):
                del self._sceneObject[position]


        # disconnect field if it was a field connection
        if (child._connectedFrom is not None) and (child._connectedTo is not None):
            child._connectedTo.disconnect(child._connectedFrom)
        
        return True
    
    
    def fields(self):
        """Returns field instances for this scene object"""
        if self._sceneObject is None:
            return []
        allFields = self._sceneObject.get_field()
        # remove private parts of node kit from field list
        if isinstance(self._sceneObject, iv.BaseKit):
            privateParts = [p["Name"] for p in self._sceneObject.get_nodekit_catalog() if not p["Public"]]
            for part in privateParts:
                field = next((f for f in allFields if f.get_name() == part), None)
                if field is not None:
                    allFields.remove(field)
        return allFields


    def fieldValue(self, index):
        """Returns field value at given index"""
        if self._sceneObject is None:
            return None

        fields = self.fields()
        if len(fields) > index:
            fieldName = fields[index].get_name()
            # don't serialize value if SFNode or MFNode field
            if "FNode" in fields[index].get_type():
                return "..."
            else:
                return self._sceneObject.get(fieldName)
        return None


    def setFieldValue(self, index, value):
        """Sets new value for field at given index"""
        if self._sceneObject is None:
            return None

        fields = self.fields()
        if len(fields) > index:
            fieldName = fields[index].get_name()
            if fields[index].get_type() == "SFNode":
                # this will create the part of a node kit if needed
                self._sceneObject.get(fieldName)
                if not value.startswith("..."):
                    fields[index].value = iv.create_object(value) if not value.startswith('"') else iv.create_object(name = value[1:-1])
                return True
            return self._sceneObject.set(fieldName, value)
        return None



class QSceneGraphModel(QtCore.QAbstractItemModel):
    """
    Model class whose items represent a scene graph.
    """

    sortRole   = QtCore.Qt.UserRole + 1
    filterRole = QtCore.Qt.UserRole + 2
    
    def __init__(self, root, parent=None):
        """Initializes scene graph model from scene object"""
        super(QSceneGraphModel, self).__init__(parent)

        self._rootNode = QSceneObjectProxy(root)
        self._draggedNodes = None


    def updateNodekit(self, field, parentIdx = QtCore.QModelIndex()):
        for i in range(0, self.rowCount(parentIdx)):
            idx = self.index(i, 0, parentIdx)
            sceneObject = idx.internalPointer()._sceneObject

            if isinstance(sceneObject, iv.BaseKit):
                publicParts = [p["Name"] for p in sceneObject.get_nodekit_catalog() if p["Public"]]
                if field in idx.internalPointer()._sceneObject.get_field() and not field in [c._connectedTo for c in idx.internalPointer()._children]:
                    if field.get_name() in publicParts and field.value is not None:
                        self.beginInsertRows(idx, 0, 0)
                        # only create, constructor already adds child to parent
                        childNode = QSceneObjectProxy(field.value, idx.internalPointer(), None, field)
                        self.endInsertRows()

            self.updateNodekit(field, idx)


    def updateFieldConnection(self, field, master, parentIdx = QtCore.QModelIndex()):
        for i in range(0, self.rowCount(parentIdx)):
            idx = self.index(i, 0, parentIdx)

            if (not idx.internalPointer().isChildNode()):
                if idx.internalPointer()._connectedTo == field:
                    # update connection of an exiting view model node
                    idx.internalPointer()._sceneObject = master.get_container()
                    idx.internalPointer()._connectedFrom = master
                    self.dataChanged.emit(idx, idx)

            if field in idx.internalPointer()._sceneObject.get_field() and not field in [c._connectedTo for c in idx.internalPointer()._children]:
                # no view model node for connection exists, create one
                self.beginInsertRows(idx, 0, 0)
                # only create, constructor already adds child to parent
                childNode = QSceneObjectProxy(master.get_container(), idx.internalPointer(), master, field)
                self.endInsertRows()

            self.updateFieldConnection(field, master, idx)
   

    def rootNode(self):
        """Returns model root node (QSceneObjectProxy)"""
        return self._rootNode

    
    def rowCount(self, parent):
        """Returns number of rows/children for given parent node"""
        if not parent.isValid():
            parentNode = self._rootNode
        else:
            parentNode = parent.internalPointer()
        
        return parentNode.childCount()
    

    def columnCount(self, parent):
        """Returns two as column count (type and name)"""
        return 2


    def mimeTypes(self):
        """Defines mime type for drag & drop"""
        return ["application/SceneGraphEditor.sceneObject"]


    def mimeData(self, indices):
        """Remembers nodes being dragged"""
        mimeData = QtCore.QMimeData()

        encodedData = QtCore.QByteArray()
        stream = QtCore.QDataStream(encodedData, QtCore.QIODevice.WriteOnly)

        # we simply reconnect the nodes rather than serializing them (performance)
        self._draggedNodes = []

        for index in indices:
            if index.isValid():
                if index.column() == 0:
                    text = self.data(index, QtCore.Qt.DisplayRole)
                    stream << text
                    self._draggedNodes.insert(0, index.internalPointer())

        mimeData.setData("application/SceneGraphEditor.sceneObject", encodedData);
        return mimeData;


    def dropMimeData(self, data, action, row, column, parent):
        """Inserts dragged nodes into scene graph"""
        if action is QtCore.Qt.IgnoreAction:
            return True
        if not data.hasFormat("application/SceneGraphEditor.sceneObject"):
            return False
        if column > 0:
            return False

        encodedData = data.data("application/SceneGraphEditor.sceneObject")
        stream = QtCore.QDataStream(encodedData, QtCore.QIODevice.ReadOnly)
        newItems = [];
        rows = 0
        while not stream.atEnd():
            text = stream.readQString()
            newItems.append(text)
            rows += 1

        if parent.isValid():
            if not parent.internalPointer().isGroup():
                row = parent.row()
                parent = parent.parent()
        
        beginRow = row;
        if (row is -1):
            if parent.isValid():
                beginRow = parent.internalPointer().childCount()
            else:
                beginRow = self._rootNode.childCount()

        if (self._draggedNodes is not None):
            # normal case, remember nodes when drag starts
            if parent.isValid() or not parent.isValid():
                parentNode = self.getProxyNodeFromIndex(parent)
                self.beginInsertRows(parent, beginRow, beginRow + len(self._draggedNodes) - 1)
                for n in self._draggedNodes:
                    success = parentNode.insertChild(beginRow, QSceneObjectProxy(n.sceneObject()))
                self.endInsertRows()
                self._draggedNodes = None
        else:
            # drag and drop between different instances is unsupported, only creates types but not values
            self.insertRows(beginRow, rows, parent)
            for text in newItems:
                idx = self.index(beginRow, 0, parent)
                self.setData(idx, text)
                beginRow += 1
        
        return True


    def data(self, index, role):
        """Returns type and name for scene objects"""
        if not index.isValid():
            return None
        
        node = index.internalPointer()
        if role == QtCore.Qt.UserRole:
            return index

        if role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            font.setItalic(not node.isChildNode())
            return font
        
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            if index.column() == 0:
                return node.title()
            if index.column() == 1:
                return node.name()
        
        if role == QSceneGraphModel.sortRole:
            return node.type()
        if role == QSceneGraphModel.filterRole:
            return node.type()
    
    
    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """Updates types or names of scene objects"""
        
        if index.isValid():
            node = index.internalPointer()
            
            if role == QtCore.Qt.EditRole:
                if (index.column() == 0) and (index.parent() is not None):
                    # type changes: need to call changeChildType on parent so old
                    # scene object can be replaced by new one

                    newSceneObject = iv.create_object(value) if not value.startswith('"') else iv.create_object(name = value[1:-1])
                    if newSceneObject is None:
                        return False

                    # add chilren from previous type
                    if index.internalPointer()._sceneObject is not None:
                        childNodes = index.internalPointer()._sceneObject[:]
                        if isinstance(newSceneObject, iv.Group):
                            newSceneObject += childNodes
                        else:
                            self.removeRows(0, len(childNodes), index)

                    parentGroup = self._rootNode
                    if index.parent().internalPointer() is not None:
                        parentGroup = index.parent().internalPointer()
                    parentGroup.changeChildType(index.row(), newSceneObject)
                
                if index.column() == 1:
                    node.setName(value)

                self.dataChanged.emit(index, index)
                return True

        return False
    
    
    def headerData(self, section, orientation, role):
        """Returns header titles for objects and names"""
        if role == QtCore.Qt.DisplayRole:
            if section == 0:
                return "Scene Object"
            else:
                return "Name"
    

    def supportedDropActions(self):
        """Returns move and copy as supported drop actions"""
        return QtCore.Qt.MoveAction | QtCore.Qt.CopyAction
    

    def flags(self, index):
        """Return flags if items can be selected and modified"""
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        if isinstance(index.internalPointer(), QSceneObjectProxy) and index.internalPointer().isChildNode():
            flags |= QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled

        if index.column() == 1:
            flags |= QtCore.Qt.ItemIsEditable

        return flags
  
    
    def parent(self, index):
        """Returns parent proxy node"""
        node = self.getProxyNodeFromIndex(index)
        parentNode = node.parent()

        if parentNode is None:
            return QtCore.QModelIndex()
        
        if parentNode == self._rootNode:
            return QtCore.QModelIndex()

        if parentNode.row() is None:
            return QtCore.QModelIndex()
        
        return self.createIndex(parentNode.row(), 0, parentNode)
    

    def index(self, row, column, parent = QtCore.QModelIndex()):
        """Returns a QModelIndex that corresponds to the given row, column and parent node"""
        parentNode = self.getProxyNodeFromIndex(parent)
        childItem = None
        if parentNode is not None:
            if row < parentNode.childCount():
                childItem = parentNode.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QtCore.QModelIndex()
    
    
    def getProxyNodeFromIndex(self, index):
        """Returns proxy node contained in index"""
        if index.isValid():
            node = index.internalPointer()
            if node:
                return node

        return self._rootNode
    

    def insertRows(self, position, rows, parent=QtCore.QModelIndex()):
        """Insert rows into model"""
        parentNode = self.getProxyNodeFromIndex(parent)
        self.beginInsertRows(parent, position, position + rows - 1)
        for row in range(rows):
            childCount = parentNode.childCount()
            childNode = QSceneObjectProxy()
            success = parentNode.insertChild(position, childNode)
        self.endInsertRows()
        
        return success
    
    
    def removeRows(self, position, rows, parent=QtCore.QModelIndex()):
        """Removes rows from model"""
        success = True
        parentNode = self.getProxyNodeFromIndex(parent)
        self.beginRemoveRows(parent, position, position + rows - 1)
        for row in range(rows):
            success = parentNode.removeChild(position)
        self.endRemoveRows()

        return success



class QFieldContainerModel(QtCore.QAbstractTableModel):
    """
    Model class whose items represent a fields of a scene object.
    """
    
    def __init__(self, root, parent=None):
        """Initializes model from a proxy node (QSceneObjectProxy)"""
        super(QFieldContainerModel, self).__init__(parent)
        self._rootNode = root
        self._connectionRequest = ()
    

    def rowCount(self, parent):
        """Returns number of rows / fields"""
        if not parent.isValid():
            parentNode = self._rootNode
        else:
            parentNode = parent.internalPointer()
        return len(parentNode.fields())
    

    def columnCount(self, parent):
        """Returns two as column count for field name and value"""
        return 3
    

    def data(self, index, role):
        """ Returns field names and values"""
        if not index.isValid():
            return None
        
        if role == QtCore.Qt.CheckStateRole and index.column() == 1:
            if self._rootNode.fields()[index.row()].get_type() == "SFBool":
                if self._rootNode.fieldValue(index.row()).startswith("TRUE"):
                    return QtCore.Qt.Checked
                else:
                    return QtCore.Qt.Unchecked

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            if index.column() == 0:
                return self._rootNode.fields()[index.row()].get_name()
            elif index.column() == 1:
                if self._rootNode.fields()[index.row()].get_type() != "SFBool":
                    return self._rootNode.fieldValue(index.row())
            else:
                text = ""
                field = self._rootNode.fields()[index.row()]
                master = None
                if field.get_connected_field() is not None:
                    master = field.get_connected_field()
                if field.get_connected_engine() is not None:
                    master = field.get_connected_engine()
                if master is not None:
                    if len(master.get_container().get_name()) > 0:
                        text = '"' + master.get_container().get_name() + '"'
                    else:
                        text = master.get_container().get_type()
                    text += " " + master.get_name()

                return text
       
        if role == QtCore.Qt.UserRole:
            if index.column() == 1:
                return self._rootNode.fields()[index.row()]
            if index.column() == 2:
                return self._connectionRequest


    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """Updates field values"""
        if index.isValid() and role == QtCore.Qt.EditRole:
            if index.column() == 1:
                self._rootNode.setFieldValue(index.row(), value)
                self.dataChanged.emit(index, index)
                return True
            elif index.column() == 2:
                objAndField = value.split(" ")
                if len(objAndField) > 0:
                    # trigger that connection field was edited to request the connection to be made
                    self._connectionRequest = (self._rootNode.fields()[index.row()], objAndField[0], objAndField[1] if len(objAndField) > 1 else "")
                    self.dataChanged.emit(index, index)
                    return True

        if role == QtCore.Qt.CheckStateRole:
            self._rootNode.setFieldValue(index.row(), ("FALSE", "", "TRUE")[value])
            return True
        
        return False


    def headerData(self, section, orientation, role):
        """Returns field name and value titles"""
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                if section == 0:
                    return "Field"
                elif section == 1:
                    return "Value"
                else:
                    return "Connection"
        return None


    def flags(self, index):
        """Values are editable but names aren't"""
        flags = QtCore.Qt.ItemIsEnabled

        if index.column() == 1:
            if self._rootNode.fields()[index.row()].get_type() == "SFBool":
                flags |= QtCore.Qt.ItemIsUserCheckable;
            else:
                flags |= QtCore.Qt.ItemIsEditable

        if index.column() == 2:
            flags |= QtCore.Qt.ItemIsEditable

        return flags


class QSceneGraphFilter(QtGui.QSortFilterProxyModel):
    """
    This class implements a custom filter that shows the path to all
    nodes in a tree model whose filter criteria are met. It can be used
    as a proxy between a view and the scene graph model.
    """
    def filterAcceptsRow(self, sourceRow, sourceParent):
        """Returns True if filter criteria is met by node or any of its children"""
        if super(QSceneGraphFilter, self).filterAcceptsRow(sourceRow, sourceParent):
            return True
        if self.filterAcceptsChildren(sourceRow, sourceParent):
            return True
        return False


    def filterAcceptsChildren(self, sourceRow, sourceParent):
        """Recursively checks if filter is met by any child"""
        index = self.sourceModel().index(sourceRow, 0, sourceParent);
        if not index.isValid():
            return False
        children = index.model().rowCount(index)
        for i in range(children):
            if super(QSceneGraphFilter, self).filterAcceptsRow(i, index):
                return True
            if self.filterAcceptsChildren(i, index):
                return True
        return False



class QSceneObjectTypeDelegate(QtGui.QStyledItemDelegate):
    """
    Item delegate for entering a scene object type. Available types are populated
    in a drop down box and input is validated against registered types in scene
    object database.
    """

    def __init__(self, parent=None):
        """Initializes delegate"""
        super(QSceneObjectTypeDelegate, self).__init__(parent)
        self.parent = parent
        self._wasUninitialized = False


    def createEditor(self, parent, option, index):
        """Creates combo box and populates it with all node types"""
        if not index.isValid():
            return False

        self.currentIndex=index  
        self.comboBox = QtGui.QComboBox(parent)
        self.comboBox.setInsertPolicy(QtGui.QComboBox.NoInsert)
        items = iv.classes("Node")
        items.sort()
        self.comboBox.addItems(items)
        self.comboBox.setEditable(True)

        return self.comboBox


    def setEditorData(self, editor, index):
        """Updates text in edit line"""
        value = index.data(QtCore.Qt.DisplayRole)
        editor.setCurrentIndex(editor.findText(value))
        editor.lineEdit().selectAll()
        self._wasUninitialized = (len(value) is 0)


    def setModelData(self, editor, model, index):
        """Updates scene graph model after input"""
        if not index.isValid():
            return False

        typeName = editor.currentText()
        if typeName.startswith('"') and typeName.endswith('"'):
            # if type name is in quotes, interpret as instance name
            sceneObject = iv.create_object(name = typeName[1:-1])
            if sceneObject is None:
                return False
        elif editor.findText(typeName) < 0:
            if self._wasUninitialized:
                # confirmed but invalid: remove row
                index.model().removeRow(index.row(), index.parent())
                return True
            # not a valid entry
            return False
        
        index.model().setData(index, typeName, QtCore.Qt.EditRole)
        self.parent.setCurrentIndex(index)
        
        return True


    def eventFilter(self, editor, event):
        """Deselect text on enter and 'commits' empty cells for removal from model"""
        if event.type() is QtCore.QEvent.KeyPress:
            if event.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
                # need to deselect any text so it is not cleared before saving to model
                editor.lineEdit().deselect()
                if len(editor.currentText()) is 0:
                    # do not allow confirmation with nothing selected
                    return False
            if event.key() in [QtCore.Qt.Key_Escape, QtCore.Qt.Key_Cancel]:
                if self._wasUninitialized:
                    # this was an uninitialized row: 
                    # trigger commit so setModelData() removes row
                    self.commitData.emit(editor)
        return super(QSceneObjectTypeDelegate, self).eventFilter(editor,event)    


    def sizeHint(self, option, index):
        """Returns default size for items, enlarged from default size for combo box"""
        return QtCore.QSize(200, 19)



class QFieldValueDelegate(QtGui.QStyledItemDelegate):
    """
    Item delegate for entering field values. A combo box is created if the
    field type is SFEnum. Otherwise a text input is used.
    """

    def createEditor(self, parent, option, index):
        """Creates field edit control depending on type."""
        editor = None
        field = index.model().data(index, QtCore.Qt.UserRole)

        if field.get_enums() is not None:
            editor = QtGui.QComboBox(parent)
            editor.setInsertPolicy(QtGui.QComboBox.NoInsert)
            editor.addItems(field.get_enums())
            if field.get_type() != "SFEnum":
                editor.setEditable(True)
        else:
            editor = QtGui.QLineEdit(parent)

        return editor


    def setEditorData(self, editor, index):
        """Updates text in edit line"""
        value = index.data(QtCore.Qt.DisplayRole)
        if isinstance(editor, QtGui.QComboBox):
            if editor.isEditable():
                editor.setEditText(value)
            else:
                editor.setCurrentIndex(editor.findText(value))
        else:
            editor.setText(value)


    def setModelData(self, editor, model, index):
        """Updates field value after input"""
        value = ""
        if isinstance(editor, QtGui.QComboBox):
            value = editor.currentText()
        else:
            value = editor.text()
        index.model().setData(index, value, QtCore.Qt.EditRole)
        return True

    

class QInspectorWidget(QtGui.QSplitter):
    """
    Widget for inspecting and editing scene grpahs. It shows the structure
    of a scene as a tree as well as a fields editor.
    """

    def __init__(self, parent=None):
        """Initializes inspector widget consisting of scene and field editor"""
        super(QInspectorWidget, self).__init__(QtCore.Qt.Vertical, parent)

        self._filterEdit = QtGui.QLineEdit()
        self._graphView = QtGui.QTreeView()
        self._fieldView = QtGui.QTableView()

        ctrlLayout = QtGui.QVBoxLayout()
        ctrlLayout.setContentsMargins(0, 0, 0, 0)
        ctrlLayout.setSpacing(1)

        self._filterEdit.setPlaceholderText("Search All Scene Objects")
        ctrlLayout.addWidget(self._filterEdit)
        ctrlLayout.addWidget(self._graphView)

        ctrlWidget = QtGui.QWidget()
        ctrlWidget.setLayout(ctrlLayout)
        self.addWidget(ctrlWidget)
        self.addWidget(self._fieldView)
        self.setStretchFactor(0, 2)

        self._proxyModel = QSceneGraphFilter(self)
        self._sceneModel = QSceneGraphModel(iv.Separator(), self)
        self._fieldsModel = None

        self._proxyModel.setSourceModel(self._sceneModel)
        self._proxyModel.setDynamicSortFilter(True)
        self._proxyModel.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self._proxyModel.setSortRole(QSceneGraphModel.sortRole)
        self._proxyModel.setFilterRole(QSceneGraphModel.filterRole)
        self._proxyModel.setFilterKeyColumn(0)
        
        self._graphView.setModel(self._proxyModel)
        self._graphView.setDragEnabled(True)
        self._graphView.setAcceptDrops(True)
        self._graphView.setDropIndicatorShown(True)
        self._graphView.setDragDropMode(QtGui.QAbstractItemView.DragDrop)
        self._graphView.setDefaultDropAction(QtCore.Qt.MoveAction)
        self._graphView.setItemDelegateForColumn(0, QSceneObjectTypeDelegate(self))
        self._graphView.setSelectionMode(QtGui.QAbstractItemView.SelectionMode.ExtendedSelection)

        self._fieldView.horizontalHeader().setStretchLastSection(True)
        self._fieldView.verticalHeader().setResizeMode(QtGui.QHeaderView.Fixed)
        self._fieldView.verticalHeader().setDefaultSectionSize(0.8 * self._fieldView.verticalHeader().defaultSectionSize())
        self._fieldView.verticalHeader().hide()
        self._fieldView.setAlternatingRowColors(True)
        self._fieldView.setWordWrap(False)
        self._fieldView.setShowGrid(False)
        self._fieldView.setItemDelegateForColumn(1, QFieldValueDelegate(self))

        QtCore.QObject.connect(self._graphView.selectionModel(), QtCore.SIGNAL("currentChanged(QModelIndex, QModelIndex)"), self.setSelection)
        QtCore.QObject.connect(self._filterEdit, QtCore.SIGNAL("textChanged(QString)"), self.setFilter)


    def attach(self, rootNode):
        """Attaches the scene and field editors to a scene graph"""
        if rootNode is not None:
            # reset old models
            self._proxyModel.setSourceModel(None)
            self._fieldView.setModel(None)

            # create new ones
            self._sceneModel = QSceneGraphModel(rootNode, self)
            self._proxyModel.setSourceModel(self._sceneModel)

            self._graphView.setColumnWidth(0, 360)
            self._graphView.setColumnWidth(1, 100)
            self._graphView.header().setStretchLastSection(True)
            self._graphView.expandAll()
            self._graphView.setFocus(QtCore.Qt.OtherFocusReason)
            

    def setFilter(self, filter):
        """Updates filter used in tree view, linked to filter edito box"""
        self._proxyModel.setFilterFixedString(filter)
        self._graphView.expandAll()
        self._graphView.scrollTo(self._graphView.currentIndex())


    def setCurrentIndex(self, index):
        """Sets current selection in scene graph tree view"""
        self._graphView.setCurrentIndex(index)


    def setSelection(self, current, old):
        """Updates field editor after selection in tree view changed"""
        if current.isValid() and current.data(QtCore.Qt.UserRole) is not None:
            isFirst = self._fieldsModel is None
            self._fieldsModel = QFieldContainerModel(current.data(QtCore.Qt.UserRole).internalPointer())
            self._fieldView.setModel(self._fieldsModel)
            QtCore.QObject.connect(self._fieldView.model(), QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"), self.fieldChanged)

            if isFirst:
                self._fieldView.setColumnWidth(0, 150)
                self._fieldView.setColumnWidth(1, 200)
                self._fieldView.setColumnWidth(2, 100)


    def addFieldConnection(self, field, typeName, masterName):
        sceneObject = None
        if typeName.startswith('"') and typeName.endswith('"'):
            # if type name is in quotes, interpret as instance name
            sceneObject = iv.create_object(name = typeName[1:-1])
        else:
            typeAndArgs = typeName.split("(")
            if len(typeAndArgs) > 1:
                # support initialization arguments in brackets for templated types (e.g. Gate)
                sceneObject = iv.create_object(type = typeAndArgs[0], init = typeAndArgs[1][:-1])
            else:
                # no round brackets means just type name is given

                # check for template types and add type argument based on field type
                initString = ""
                if typeName in ("Gate", "SelectOne", "Concatenate"):
                    initString = field.get_type().replace("SF", "MF", 1)
                if typeName in iv.classes("FieldContainer"):
                    sceneObject = iv.create_object(type = typeName, init = initString)

        if sceneObject is not None:
            master = None
            if isinstance(sceneObject, iv.Engine):
                master = sceneObject.get_output(masterName) if len(masterName) > 0 else sceneObject.get_output()[0] if len(sceneObject.get_output()) > 0 else None
            if master is None:
                master = sceneObject.get_field(masterName) if len(masterName) > 0 else sceneObject.get_field()[0] if len(sceneObject.get_field()) > 0 else None
            if field is not None and master is not None:
                if field.connect_from(master):
                    self._sceneModel.updateFieldConnection(field, master)
                    return True
        return False


    def fieldChanged(self, current, old):
        """Updates field editor after selection in tree view changed"""
        if current.isValid():
            if current.column() == 2:
                connectionDetail = current.data(QtCore.Qt.UserRole)
                self.addFieldConnection(connectionDetail[0], connectionDetail[1], connectionDetail[2])
            elif current.column() == 1:
                self._sceneModel.updateNodekit(current.data(QtCore.Qt.UserRole))


    def keyPressEvent(self, event):
        """Handles default keyboard events for insert and delete"""
        if event.key() in [QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace]:
            self.deleteObject()

        if event.key() in [QtCore.Qt.Key_Insert]:
            self.insertObject()

        if event.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
            self.appendObject()
        
        if event.modifiers():
            # allow insert with cursor keys while modifier key is pressed
            if event.key() == QtCore.Qt.Key_Up:
                self.insertObject()
            if event.key() == QtCore.Qt.Key_Down:
                self.appendObject()
                    
        super(QInspectorWidget, self).keyPressEvent(event)


    def sizeHint(self):
        """Returns default widget size"""
        return QtCore.QSize(512, 512)


    def deleteObject(self):
        """Deletes all scene objects currently selected in tree view"""
        indices = self._graphView.selectionModel().selectedIndexes()

        dataIndices = []
        parentNode = None
        
        for index in indices:
            if index.isValid():
                if index.column() is 0:
                    i = index.data(QtCore.Qt.UserRole)
                    parentNode = i.parent().internalPointer()
                    dataIndices.append(i)

        for index in reversed(dataIndices):
            if index.isValid():
                self._sceneModel.removeRow(index.row(), index.parent())
        

    def appendObject(self):
        """Appends a new scene object after current selection"""
        viewIndex = self._graphView.currentIndex()
        if viewIndex.isValid():
            dataIndex = viewIndex.data(QtCore.Qt.UserRole)
            if dataIndex.internalPointer().isChildNode():
                if self._sceneModel.insertRow(dataIndex.row() + 1, dataIndex.parent()):
                    viewIndex = viewIndex.sibling(viewIndex.row() + 1, viewIndex.column())
                    self._fieldView.setModel(None)
                    self._graphView.edit(viewIndex.sibling(viewIndex.row(), 0))
                    self._graphView.clearSelection()


    def insertObject(self):
        """Inserts a new scene object before current selection"""
        viewIndex = self._graphView.currentIndex()
        if viewIndex.isValid():
            dataIndex = viewIndex.data(QtCore.Qt.UserRole)
            if dataIndex.internalPointer().isChildNode():
                if self._sceneModel.insertRow(dataIndex.row(), dataIndex.parent()):
                    self._fieldView.setModel(None)
                    dataIndex = viewIndex.data(QtCore.Qt.UserRole)
                    self._graphView.edit(viewIndex.sibling(viewIndex.row(), 0))
                    self._graphView.clearSelection()



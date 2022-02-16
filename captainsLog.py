import json
import os.path
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
from typing import Union


class Entry:
    ID_GEN = 0

    def __init__(self, name: str = '', log='', children=None, date=''):
        self.name = name
        self.log = log
        self.children = []

        self.logID = Entry.ID_GEN
        Entry.ID_GEN += 1

        if children is not None:
            for c in children:
                self.children.append(Entry(**c))

        self.date = date

    def toDict(self):
        return {
            'name': self.name,
            'log': self.log,
            'children': [x.toDict() for x in self.children],
            'date': self.date
        }

    def getMangle(self) -> str:
        return f'{self.logID}_{self.name}'

    def addChild(self, e):
        self.children.append(e)


class TreeManager:
    def __init__(self, tree: ttk.Treeview, root: Entry):
        self.tree = tree

        tree.delete(*tree.get_children())

        self.root = root

        self.nodes = {root.getMangle(): root}

        self.loadTree('', self.root)

    def loadTree(self, parent: str, e: Entry):
        self.insertNode(parent, e)

        if len(e.children) > 0:
            for x in e.children:
                self.loadTree(e.getMangle(), x)


    def insertNode(self, parent: str, e: Entry, select=False):
        x = self.tree.insert(parent, 'end', e.getMangle(), text=e.name, values=[len(e.children)])
        self.nodes[e.getMangle()] = e

        if select:
            self.tree.see(x)



class CancelAction(Exception):
    pass


def destructive(func):
    def wrapper(self, *args, **kwargs):
        if self.needToSave:
            try:
                self.promptSave()
            except CancelAction:
                return

        func(self, *args, **kwargs)

    return wrapper


def askOpen():
    # noinspection PyArgumentList
    return filedialog.askopenfilename(multiple=False, filetypes=[("Captain's Log", '.capLog')])


def askSave():
    return filedialog.asksaveasfilename(confirmoverwrite=True, defaultextension='.capLog',
                                        filetypes=[("Captain's Log", '.capLog')])


def stripFN(filename) -> str:
    _, filename = os.path.split(filename)
    filename, _ = os.path.splitext(filename)
    return filename


class CaptainsLog(tk.Frame):

    def __init__(self, root: tk.Tk):
        super().__init__(root)

        self.treeMan: Union[None, TreeManager] = None

        self.needToSave = False
        self.curLogFilename = ''

        self.root = root
        self.root.title("Captain's Log")
        self.root.protocol("WM_DELETE_WINDOW", self.closeWindow)
        root.option_add('*tearOff', False)

        self.grid(row=0, column=0, sticky='nesw')

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # upperFrame = tk.LabelFrame(self, text='asdf')
        upperFrame = tk.Frame(self)
        upperFrame.grid(row=0, column=0, sticky='ewn', columnspan=2)
        for x in range(2):
            upperFrame.columnconfigure(x, weight=1)

        # Tree Frame
        treeFrame = tk.Frame(self)
        treeFrame.grid(row=1, column=0, sticky='nesw')

        treeFrame.rowconfigure(1, weight=1)

        treeButtonFrame = tk.Frame(upperFrame)
        treeButtonFrame.grid(row=0, column=0, sticky='new')

        tk.Button(upperFrame, text="Add New Entry", command=self.addNewEntryAtEnd).grid(row=0, column=0, sticky='nw')

        self.tree = ttk.Treeview(treeFrame, selectmode='browse', columns=('sublogs',))
        self.tree.column('sublogs', width=100)
        self.tree.heading('sublogs', text='Sub-Logs')
        self.tree.grid(row=1, column=0, sticky='news')

        self.tree.bind('<<TreeviewSelect>>', lambda e: self.selectEntry())

        # Text Frame

        textFrame = tk.Frame(self)
        textFrame.grid(row=1, column=1)

        entryDataFrame = tk.Frame(upperFrame)
        entryDataFrame.grid(row=0, column=1, sticky='new')

        entryDataFrame.columnconfigure(1, weight=1)

        self.entryNameVar = tk.StringVar()
        tk.Label(entryDataFrame, text='Name:').grid(row=0, column=0, sticky='nw')
        tk.Entry(entryDataFrame, textvariable=self.entryNameVar).grid(row=0, column=1, sticky='nwe')

        self.textArea = tk.Text(textFrame)
        self.textArea.grid(row=1, column=0, sticky='nesw')

        # Menu

        menu = tk.Menu(root)
        root['menu'] = menu

        fileMenu = tk.Menu(menu)
        menu.add_cascade(menu=fileMenu, label='File')
        fileMenu.add_command(label='New Log', command=self.newLogFile)
        fileMenu.add_separator()
        fileMenu.add_command(label='Save Log', command=self.saveLogFileMenuCmd)
        fileMenu.add_separator()
        fileMenu.add_command(label='Load Log', command=self.selectLogFile)

    @destructive
    def closeWindow(self):
        self.root.destroy()

    def promptSave(self):
        ret = messagebox.askyesnocancel('Save?', 'Save Current Log?')

        if ret is None:
            raise CancelAction()

        if ret:
            self.saveLogFile()

    @destructive
    def newLogFile(self):
        print('getting filename')
        ret = askSave()

        if ret is None or len(ret) == 0:
            return

        self.curLogFilename = ret

        filename = stripFN(ret)

        self.treeMan = TreeManager(self.tree, Entry(filename))

        self.needToSave = True

    @destructive
    def selectLogFile(self):
        ret = askOpen()

        if ret is None or len(ret) == 0:
            return

        self.curLogFilename = ret

        with open(self.curLogFilename, mode='r') as f:
            logs = json.load(f)

        self.treeMan = TreeManager(self.tree, Entry(**logs))

        self.needToSave = False

    def saveLogFileMenuCmd(self):
        try:
            self.saveLogFile()
        except CancelAction:
            pass

    def saveLogFile(self):
        if self.curLogFilename is None or len(self.curLogFilename) == 0:
            ret = askSave()

            if ret is None or len(ret) == 0:
                raise CancelAction

            self.curLogFilename = ret

        with open(self.curLogFilename, mode='w') as f:
            json.dump(self.treeMan.root.toDict(), f)

        self.needToSave = False

    def addNewEntryAtEnd(self):
        s = self.tree.selection()
        if len(s) == 0:
            return

        self.treeMan.insertNode(s[0], Entry('New Log'), select=True)

    def selectEntry(self):
        s = self.tree.selection()
        if len(s) == 0:
            return

        e = self.treeMan.nodes[s[0]]
        self.entryNameVar.set(e.name)


def main():
    x = tk.Tk()
    gui = CaptainsLog(x)
    gui.mainloop()


if __name__ == '__main__':
    main()

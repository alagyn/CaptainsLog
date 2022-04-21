import json
import os.path
import re
import sys
from tkinter import ttk
import tkinter as tk
from tkinter import messagebox, filedialog
from typing import Union, Dict
from configparser import ConfigParser


class EntryIter:
    def __init__(self, e: 'Entry'):
        self.cur = e

    def __iter__(self):
        return self

    def __next__(self) -> 'Entry':
        if self.cur is None:
            raise StopIteration

        out = self.cur
        self.cur = self.cur.nextEntry
        return out


class Entry:
    ID_GEN = 0

    def __init__(self, name: str = '', log='', children=None, date='', parent=None):
        self.name = name
        self.log = log
        self.childRoot: Union['Entry', None] = None
        self.childEnd: Union['Entry', None] = None

        self.numChildren = 0

        self.parent: 'Entry' = parent
        self.date = date

        self.logID: int = Entry.ID_GEN
        # print(f'Gen: {self.logID}, {self.name}')
        Entry.ID_GEN += 1

        if children is not None:
            for c in children:
                self.addChild(Entry(**c))

        self.prevEntry: Union['Entry', None] = None
        self.nextEntry: Union['Entry', None] = None
        self.idx = 0

    def toDict(self):
        return {
            'name': self.name,
            'log': self.log,
            'children': [x.toDict() for x in self],
            'date': self.date
        }

    def __iter__(self):
        return EntryIter(self.childRoot)

    def getMangle(self) -> str:
        return f'{self.logID}_'

    def addChild(self, e: 'Entry'):
        if self.childRoot is None:
            self.childRoot = e
            self.childEnd = e
        else:
            self.childEnd.nextEntry = e
            e.prevEntry = self.childEnd
            self.childEnd = e

        e.idx = self.numChildren
        self.numChildren += 1
        e.parent = self

    def unlink(self):
        if self.prevEntry is not None:
            self.prevEntry.nextEntry = self.nextEntry
        else:
            self.parent.childRoot = self.nextEntry

        if self.nextEntry is not None:
            self.nextEntry.prevEntry = self.prevEntry
        else:
            self.parent.childEnd = self.prevEntry

        self.parent.numChildren -= 1

        cur = self.nextEntry
        while cur is not None:
            cur.idx -= 1
            cur = cur.nextEntry

    def moveLeft(self):
        if self.prevEntry is None:
            return

        oldPrev = self.prevEntry
        oldNext = self.nextEntry

        self.prevEntry = oldPrev.prevEntry
        self.nextEntry = oldPrev

        oldPrev.prevEntry = self
        oldPrev.nextEntry = oldNext

        if oldNext is not None:
            oldNext.prevEntry = oldPrev
        else:
            self.parent.childEnd = oldPrev

        if self.prevEntry is None:
            self.parent.childRoot = self

        self.idx -= 1
        oldPrev.idx += 1

    def moveRight(self):
        if self.nextEntry is None:
            return

        oldPrev = self.prevEntry
        oldNext = self.nextEntry

        self.prevEntry = oldNext
        self.nextEntry = oldNext.nextEntry

        oldNext.prevEntry = oldPrev
        oldNext.nextEntry = self

        if oldPrev is not None:
            oldPrev.nextEntry = oldNext
        else:
            self.parent.childRoot = oldNext

        if self.nextEntry is None:
            self.parent.childEnd = self

        self.idx += 1
        oldNext.idx -= 1

    def moveTo(self, idx: int):
        if idx == self.idx:
            return

        while self.idx < idx and self.nextEntry is not None:
            self.moveRight()

        while self.idx > idx and self.prevEntry is not None:
            self.moveLeft()

    def __str__(self):
        return f'ID:{self.logID} #{self.idx} {self.name}'

TREE_T = 'tree'

class TreeManager:
    def __init__(self, tree: ttk.Treeview, root: Entry):
        self.tree = tree

        tree.delete(*tree.get_children())

        self.root = root

        self.nodes: Dict[str, Entry] = {root.getMangle(): root}

        self.loadTree('', self.root)
        self.updateSubLogCounts()

    def loadTree(self, parent: str, e: Entry):
        self.insertNode(parent, e)

        if e.numChildren > 0:
            for x in e:
                self.loadTree(e.getMangle(), x)

    def insertNode(self, parent: str, e: Entry, select=False):
        # print(f'P: {parent}, E:{e}')

        x = self.tree.insert(parent, 'end', e.getMangle(), text=e.name, values=[0], tags=(TREE_T, ))
        self.nodes[e.getMangle()] = e

        if select:
            self.tree.see(x)

    def insertNewNode(self, parent: str):
        e = Entry('New Log')
        self.insertNode(parent, e, True)

        if len(parent) > 0:
            self.nodes[parent].addChild(e)

        self.updateSubLogCounts()

    def setName(self, eid: str, name: str):
        e = self.nodes[eid]
        e.name = name

        self.tree.item(eid, text=name)

    def setNum(self, eid: str, num: int) -> int:
        e = self.nodes[eid]
        e.moveTo(num)

        self.tree.move(eid, e.parent.getMangle(), e.idx)

        return e.idx

    def select(self, eid: int):
        self.tree.item(f'{eid}_', open=True)

    def remove(self, eid: str):
        self.tree.delete(eid)
        e = self.nodes.pop(eid)
        e.unlink()
        self.updateSubLogCounts()

    def updateSubLogCounts(self):
        e = self.nodes[ROOT_ID]
        self.updateSubLogCountForItem(e)

    def updateSubLogCountForItem(self, e: Entry) -> int:
        s = 0
        for c in e:
            s += 1 + self.updateSubLogCountForItem(c)

        self.tree.item(e.getMangle(), values=[s])
        return s


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


INT_RE = re.compile(r'-?\d*')


def _intValidate(i: str) -> bool:
    return INT_RE.fullmatch(i) is not None


ROOT_ID = '0_'
HL_TAG = 'highlight'

START = 'start'
END = 'mend'
LIMIT = 'limit'



class CaptainsLog(ttk.Frame):

    def __init__(self, root: tk.Tk, config: ConfigParser, startingFile: Union[str, None] = None):
        super().__init__(root)

        self.treeMan: Union[None, TreeManager] = None

        self.needToSave = False
        self.ignoreTrace = False
        self.curLogFilename = ''
        self.curEntry: Union[None, Entry] = None

        # Style
        #region

        colors = config['Colors']

        def getColor(key) -> str:
            return f'#{colors[key]}'

        BG = getColor('BG')
        SELECT = getColor('Select')
        FG = getColor('FG')


        style = ttk.Style()

        style.theme_use('clam')

        style.configure('CLFrame.TFrame', background=BG)

        style.configure('CLTree.Treeview', background=[('selected', SELECT)],
                        foreground=FG, fieldbackground=BG)
        style.configure('CLTree.Treeview.Heading', background=BG)
        style.configure('CLTree.Treeview.Item', background=BG, foreground=FG)

        #endregion

        # ROOT
        # region
        self.root = root
        self.root.title("Captain's Log")
        self.root.protocol("WM_DELETE_WINDOW", self.closeWindow)
        root.option_add('*tearOff', False)

        self.grid(row=0, column=0, sticky='nesw')

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        # endregion

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)

        self['style'] = 'CLFrame.TFrame'

        # Upper Frame setup
        # region
        # upperFrame = ttk.LabelFrame(self, text='Upper')
        upperFrame = ttk.Frame(self, style='CLFrame.TFrame')
        upperFrame.grid(row=0, column=0, sticky='sewn')
        for x in range(2):
            upperFrame.columnconfigure(x, weight=1)

        upperFrame.rowconfigure(0, weight=1)

        # endregion

        # Button Frame
        # region
        # buttonFrame = ttk.LabelFrame(upperFrame, text='Btn')
        buttonFrame = ttk.Frame(upperFrame, style='CLFrame.TFrame')
        buttonFrame.grid(row=0, column=0, sticky='nwe')

        ttk.Button(buttonFrame, text="Add New Entry", command=self.addNewEntryAtEnd).grid(row=0, column=0, sticky='nw')
        ttk.Button(buttonFrame, text='Remove Selected', command=self.removeSelectedEntry).grid(row=0, column=1,
                                                                                               sticky='nw')
        # endregion

        # Lower Frame setup
        # region
        # lowerFrame = ttk.LabelFrame(self, text='lower')
        lowerFrame = ttk.Frame(self, style='CLFrame.TFrame')
        lowerFrame.grid(row=1, column=0, sticky='nesw')

        lowerFrame.columnconfigure(1, weight=1)
        lowerFrame.rowconfigure(0, weight=1)
        # endregion

        # Tree Frame
        # region
        # treeFrame = ttk.LabelFrame(lowerFrame, text='')
        treeFrame = ttk.Frame(lowerFrame, style='CLFrame.TFrame')
        treeFrame.grid(row=0, column=0, sticky='nesw')

        treeFrame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(treeFrame, selectmode='browse', columns=('sublogs',),
                                 style='CLTree.Treeview')
        self.tree.column('sublogs', width=100)
        self.tree.heading('#0', text='Name')
        self.tree.heading('sublogs', text='Sub-Logs')
        self.tree.grid(row=0, column=0, sticky='news')

        self.tree.bind('<<TreeviewSelect>>', lambda e: self.openSelectedEntry())

        self.tree.tag_configure(TREE_T, background=BG)

        treeScroll = ttk.Scrollbar(treeFrame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=treeScroll.set)
        treeScroll.grid(row=0, column=1, sticky='nes')
        # endregion

        # Text Frame
        # region
        textFrame = ttk.LabelFrame(lowerFrame, text='Log Entry')
        textFrame.grid(row=0, column=1, sticky='nesw')
        textFrame.rowconfigure(1, weight=1)
        textFrame.columnconfigure(0, weight=1)

        entryDataFrame = ttk.LabelFrame(textFrame, text='Data')
        entryDataFrame.grid(row=0, column=0, sticky='new')

        entryDataFrame.columnconfigure(3, weight=1)

        self.entryIdxVar = tk.IntVar()
        ttk.Label(entryDataFrame, text='#').grid(row=0, column=0, sticky='nw')

        v = self.register(_intValidate)

        self.numSpinbox = ttk.Spinbox(entryDataFrame, textvariable=self.entryIdxVar, increment=-1, from_=1, to=100,
                                      width=5,
                                      validatecommand=(v, '%P'))

        self.numSpinbox.grid(row=0, column=1)

        self.entryIdxVar.trace_add('write', self.modifiedNum)

        self.entryNameVar = tk.StringVar()
        ttk.Label(entryDataFrame, text='Name:').grid(row=0, column=2, sticky='nw')
        nameEntry = ttk.Entry(entryDataFrame, textvariable=self.entryNameVar)
        nameEntry.grid(row=0, column=3, sticky='nwe')
        self.entryNameVar.trace_add('write', self.modifiedName)
        # endregion

        # ENTRY AREA
        # region
        self.textArea = tk.Text(textFrame, wrap='word', font=config['Font']['Entry'],
                                bg=BG, fg=FG)
        self.textArea['state'] = 'disabled'
        self.textArea.grid(row=1, column=0, sticky='nesw')
        # self.textArea.bind('<<Modified>>', lambda e: self.modifiedText())

        self.textArea.tag_configure(HL_TAG, font=config['Font']['EntryHeader'])

        self.root.bind('<KeyRelease>', func=self.modifiedText, add=True)
        self.textArea.bind('<Control-KeyRelease-BackSpace->', lambda e: self.deleteWord(), add=False)
        self.root.bind('<Control-KeyRelease-s>', lambda e: self.saveLogFileMenuCmd(), add=False)

        textScroll = ttk.Scrollbar(textFrame, orient=tk.VERTICAL, command=self.textArea.yview)
        self.textArea.configure(yscrollcommand=textScroll.set)
        textScroll.grid(row=1, column=1, sticky='nes')
        # endregion

        # Menu
        # region
        menu = tk.Menu(root)
        root['menu'] = menu

        fileMenu = tk.Menu(menu)
        menu.add_cascade(menu=fileMenu, label='File')
        fileMenu.add_command(label='New Log', command=self.newLogFile)
        fileMenu.add_separator()
        fileMenu.add_command(label='Save Log', command=self.saveLogFileMenuCmd)
        # TODO save as
        fileMenu.add_separator()
        fileMenu.add_command(label='Load Log', command=self.selectLogFile)
        # endregion
        if startingFile is not None:
            self.loadLogFile(startingFile)

    @destructive
    def closeWindow(self):
        self.root.destroy()

    def setNeedToSave(self, v: bool):
        if v:
            self.root.title("Captain's Log *")
        else:
            self.root.title("Captain's Log")

        self.needToSave = v

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

        Entry.ID_GEN = 0

        self.curLogFilename = ret

        filename = stripFN(ret)

        self.treeMan = TreeManager(self.tree, Entry(filename))

        self.setNeedToSave(True)

        self.resetEntryFields()

    @destructive
    def selectLogFile(self):
        ret = askOpen()

        if ret is None or len(ret) == 0:
            return

        self.loadLogFile(ret)

    def loadLogFile(self, filename):
        self.curLogFilename = filename

        Entry.ID_GEN = 0

        with open(self.curLogFilename, mode='r') as f:
            x = f.read(1)
            f.seek(0, 0)
            if len(x) == 0:
                name = stripFN(filename)
                self.treeMan = TreeManager(self.tree, Entry(name))
            else:
                logs = json.load(f)
                self.treeMan = TreeManager(self.tree, Entry(**logs))

        self.treeMan.select(0)

        self.setNeedToSave(False)

        self.resetEntryFields()

        self.openSelectedEntry()

    def resetEntryFields(self):
        init = self.ignoreTrace
        self.ignoreTrace = True

        self.entryIdxVar.set(1)
        self.entryNameVar.set('')

        self.textArea.delete('0.0', 'end')

        self.update()
        self.ignoreTrace = init

    def saveLogFileMenuCmd(self):
        try:
            self.saveLogFile()
        except CancelAction:
            pass

    def saveLogFile(self):
        self.storeCurrentEntry()

        if self.curLogFilename is None or len(self.curLogFilename) == 0:
            ret = askSave()

            if ret is None or len(ret) == 0:
                raise CancelAction

            self.curLogFilename = ret

        with open(self.curLogFilename, mode='w') as f:
            json.dump(self.treeMan.root.toDict(), f)

        self.ignoreTrace = True
        self.textArea.edit_modified(False)
        self.update()
        self.ignoreTrace = False
        self.setNeedToSave(False)

    def getSel(self):
        s = self.tree.selection()
        if len(s) == 0:
            return None

        return s[0]

    def getEntry(self, s) -> Entry:
        return self.treeMan.nodes[s]

    def addNewEntryAtEnd(self):
        s = self.getSel()
        if self.treeMan is not None and s is not None:
            self.treeMan.insertNewNode(s)

            self.treeMan.updateSubLogCounts()
        elif self.treeMan is None:
            self.treeMan = TreeManager(self.tree, Entry('New Log'))

        self.setNeedToSave(True)

    def storeCurrentEntry(self):
        if self.curEntry is not None:
            self.curEntry.log = self.textArea.get('0.0', 'end').rstrip()

    def openSelectedEntry(self):
        s = self.getSel()

        if s is not None:
            e = self.treeMan.nodes[s]
            self.ignoreTrace = True

            self.storeCurrentEntry()

            self.textArea.delete('0.0', 'end')
            self.curEntry = e

            self.entryNameVar.set(e.name)
            self.entryIdxVar.set(e.idx + 1)

            self.textArea['state'] = 'normal'

            self.textArea.insert('1.0', e.log)
            self.textArea.edit_modified(False)

            self.highlighter()

            if s == ROOT_ID:
                self.numSpinbox['state'] = 'disabled'
            else:
                self.numSpinbox['state'] = 'normal'

            self.update_idletasks()
            self.update()
            self.ignoreTrace = False

    def removeSelectedEntry(self):
        s = self.getSel()

        if s is not None:
            if s == ROOT_ID:
                messagebox.showinfo('Invalid', 'Cannot Remove Initial Log')
                return

            e = self.treeMan.nodes[s]
            ret = messagebox.askyesno('Delete Entry?',
                                      f'Are you sure you want to remove entry: "{e.name}" and all it\'s sub-logs?')

            if not ret:
                return

            self.treeMan.remove(s)

            self.resetEntryFields()

            self.setNeedToSave(True)

    def deleteWord(self):
        index = self.textArea.index('insert - 1c wordstart')
        self.textArea.delete(index, 'insert')

    def modifiedText(self, event: tk.Event):
        if self.ignoreTrace:
            return

        if self.textArea['state'] == 'disabled':
            return

        # Ignore the control key
        if event.keycode == 17:
            return

        # print(event)

        self.update_idletasks()

        self.highlighter()
        # print(event)
        # if event.char == '\r':
        # self.indentNewLine()

        if self.curEntry is not None:
            self.setNeedToSave(True)

    def modifiedName(self, _a, _b, _c):
        if self.ignoreTrace:
            return

        s = self.getSel()
        if s is not None:
            self.treeMan.setName(s, self.entryNameVar.get())
            self.setNeedToSave(True)

    def modifiedNum(self, _a, _b, _c):
        if self.ignoreTrace:
            return

        s = self.getSel()
        if s is not None:
            if s == ROOT_ID:
                return

            try:
                x = self.entryIdxVar.get() - 1
            except tk.TclError:
                return

            newnum = self.treeMan.setNum(s, x)
            self.ignoreTrace = True
            self.entryIdxVar.set(newnum + 1)
            self.ignoreTrace = False
            self.setNeedToSave(True)

    def highlighter(self):

        self.textArea.mark_set(START, '0.0')
        self.textArea.mark_set(END, '0.0')
        self.textArea.mark_set(LIMIT, 'end')

        self.textArea.tag_remove(HL_TAG, '0.0', 'end')

        sizeVar = tk.IntVar()
        while True:
            index = self.textArea.search('#', END, LIMIT, count=sizeVar, regexp=False)

            if len(index) == 0 or sizeVar.get() == 0:
                break

            line, _ = index.split('.')
            line = int(line)

            self.textArea.mark_set(START, index)
            self.textArea.mark_set(END, f'{line}.0 lineend')

            self.textArea.tag_add(HL_TAG, START, END)

    def indentNewLine(self):
        newline = self.textArea.index('insert linestart')
        prevline = self.textArea.index(f'{newline} - 1l')

        print(newline)
        print(prevline)


def main():
    if len(sys.argv) < 2:
        f = None
    else:
        f = sys.argv[1]

    x = tk.Tk()

    config = ConfigParser()
    config.read(r'config/system.cfg')

    gui = CaptainsLog(x, config, f)
    gui.mainloop()


if __name__ == '__main__':
    main()

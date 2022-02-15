import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
from typing import List


class Entry:
    def __init__(self, name: str, log='', children=None, date=''):
        self.name = name
        self.log = log
        self.children = children or []
        self.date = date

    def toDict(self):
        return {
            'name': self.name,
            'log': self.log,
            'children': [x.toDict() for x in self.children],
            'date': self.date
        }


class CaptainsLog(tk.Frame):

    def __init__(self, root):
        super().__init__(root)

        self.logs: List[Entry] = []

        self.needToSave = False
        self.curLogFilename = ''

        self.root = root
        self.root.protocol("WM_DELETE_WINDOW", self.closeWindow)
        root.option_add('*tearOff', False)

        self.grid(row=0, column=0, sticky='nesw')

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Tree Frame
        treeFrame = tk.Frame(self)
        treeFrame.grid(row=0, column=0, sticky='nesw')

        self.tree = ttk.Treeview(treeFrame, selectmode='browse')
        self.tree.grid(row=1, column=0, sticky='news')

        tk.Button(treeFrame, text="Add New Log", command=self.addNewEntryAtEnd).grid(row=0, column=0)

        # Text Frame
        textFrame = tk.LabelFrame(self)
        textFrame.grid(row=0, column=1)

        self.textArea = tk.Text(textFrame)
        self.textArea.grid(row=0, column=0, sticky='nesw')

        # Menu

        menu = tk.Menu(root)
        root['menu'] = menu

        fileMenu = tk.Menu(menu)
        menu.add_cascade(menu=fileMenu, label='File')
        fileMenu.add_command(label='New', command=self.newLogFile)

    def closeWindow(self):
        self.root.destroy()

    def promptSave(self):
        ret = messagebox.askyesnocancel('Save?', 'Save Current Log?')

        if ret is None:
            # TODO asdf
            raise 'asdfasdfasd'

    def newLogFile(self):
        if self.needToSave:
            # TODO save
            pass

        ret = filedialog.asksaveasfilename(confirmoverwrite=True, defaultextension='.capLog',
                                           filetypes=[("Captain's Log", '.capLog')])

        if ret is None or len(ret) == 0:
            return

        self.curLogFilename = ret
        self.loadLogFile()

    def loadLogFile(self):
        pass

    def saveLogFile(self):
        pass

    def addNewEntryAtEnd(self):
        self.tree.insert('', 'end', text='ASDF')


def main():
    x = tk.Tk()
    gui = CaptainsLog(x)
    gui.mainloop()

if __name__ == '__main__':
    main()

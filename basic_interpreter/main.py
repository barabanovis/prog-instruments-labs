import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from lexer import Lexer, LexerError
from parser import Parser, ParseError
from interpreter import Interpreter, InterpreterError
from debugger import Debugger
from poliz import disassemble


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BASIC Interpreter — вариант 3-2-1-A")
        self.geometry("1200x700")
        self.interp = None
        self.dbg = None
        self._build_ui()

    def _build_ui(self):
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # левая панель — редактор
        left = ttk.Frame(paned)
        paned.add(left, weight=1)
        self.editor = tk.Text(left, wrap='none', font=('Consolas', 11))
        self.editor.pack(fill=tk.BOTH, expand=True)
        tb = ttk.Frame(left)
        tb.pack(fill=tk.X)
        ttk.Button(tb, text="Загрузить", command=self.load).pack(side=tk.LEFT)
        ttk.Button(tb, text="Сохранить", command=self.save).pack(side=tk.LEFT)
        ttk.Button(tb, text="Запустить", command=self.run).pack(side=tk.LEFT)
        ttk.Button(tb, text="Шаг", command=self.step).pack(side=tk.LEFT)
        ttk.Button(tb, text="Точка останова",
                   command=self.toggle_bp).pack(side=tk.LEFT)

        # правая панель — ПОЛИЗ + переменные + вывод
        right = ttk.Frame(paned)
        paned.add(right, weight=1)
        self.poliz_view = tk.Text(right, height=15, font=('Consolas', 10))
        self.poliz_view.pack(fill=tk.BOTH, expand=True)
        self.vars_view = ttk.Treeview(right, columns=(
            'name', 'type', 'value'), show='headings')
        for c in ('name', 'type', 'value'):
            self.vars_view.heading(c, text=c)
        self.vars_view.pack(fill=tk.BOTH, expand=True)
        self.out = tk.Text(right, height=8)
        self.out.pack(fill=tk.BOTH, expand=True)

        # статус
        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status,
                  relief=tk.SUNKEN).pack(fill=tk.X)

    def load(self):
        p = filedialog.askopenfilename(
            filetypes=[("BASIC", "*.bas"), ("All", "*.*")])
        if p:
            self.editor.delete('1.0', tk.END)
            self.editor.insert('1.0', open(p, encoding='utf-8').read())

    def save(self):
        p = filedialog.asksaveasfilename(defaultextension=".bas")
        if p:
            open(p, 'w', encoding='utf-8').write(self.editor.get('1.0', tk.END))

    def _compile(self):
        src = self.editor.get('1.0', tk.END)
        try:
            tokens = Lexer(src).tokenize()
            poliz, symtab = Parser(tokens).parse()
        except (LexerError, ParseError) as e:
            messagebox.showerror("Ошибка компиляции", str(e))
            return None
        self.interp = Interpreter(poliz, symtab)
        self.dbg = Debugger(self.interp)
        self._refresh()
        return True

    def run(self):
        if not self._compile():
            return
        try:
            self.interp.run()
        except InterpreterError as e:
            messagebox.showerror("Ошибка выполнения", str(e))
        self._refresh()

    def step(self):
        if self.interp is None:
            if not self._compile():
                return
        try:
            self.dbg.step()
        except InterpreterError as e:
            messagebox.showerror("Ошибка выполнения", str(e))
        self._refresh()

    def toggle_bp(self):
        if self.interp is None:
            if not self._compile():
                return
        self.dbg.toggle_breakpoint(self.interp.pc)
        self._refresh()

    def _refresh(self):
        if self.interp is None:
            return
        self.poliz_view.delete('1.0', tk.END)
        self.poliz_view.insert('1.0', disassemble(
            self.interp.poliz, self.interp.pc))
        self.vars_view.delete(*self.vars_view.get_children())
        for _, chain in self.interp.symtab.dump():
            for s in chain:
                self.vars_view.insert('', tk.END, values=(
                    s.name, s.vtype.value, s.value))
        self.out.delete('1.0', tk.END)
        self.out.insert('1.0', '\n'.join(self.interp.output))
        self.status.set(f"pc={self.interp.pc}  stack={self.interp.stack}")


if __name__ == '__main__':
    App().mainloop()

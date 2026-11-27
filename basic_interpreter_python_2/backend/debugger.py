"""
backend/debugger.py
===================
Обёртка над Interpreter: точки останова, пошаговое выполнение, снимок состояния.
"""


class Debugger:
    def __init__(self, interp):
        self.interp = interp
        self.breakpoints = set()

    def toggle_breakpoint(self, pc):
        if pc in self.breakpoints:
            self.breakpoints.remove(pc)
        else:
            self.breakpoints.add(pc)

    def run_until_breakpoint(self):
        while not self.interp.finished:
            if self.interp.pc in self.breakpoints:
                return 'breakpoint'
            self.interp.step()
        return 'finished'

    def step(self):
        return self.interp.step()

    def state(self):
        return {
            'pc': self.interp.pc,
            'stack': list(self.interp.stack),
            'vars': {s.name: s.value for _, chain in self.interp.symtab.dump()
                     for s in chain},
            'poliz': self.interp.poliz,
        }

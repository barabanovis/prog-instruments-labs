class Debugger:
    def __init__(self, interp):
        self.interp = interp

    def toggle_breakpoint(self, pc):
        if pc in self.interp.breakpoints:
            self.interp.breakpoints.remove(pc)
        else:
            self.interp.breakpoints.add(pc)

    def run_until_breakpoint(self):
        while not self.interp.finished:
            if self.interp.pc in self.interp.breakpoints:
                return 'breakpoint'
            self.interp.step()
        return 'finished'

    def step(self):
        return self.interp.step()

    def state(self):
        return {
            'pc': self.interp.pc,
            'stack': list(self.interp.stack),
            'vars': {s.name: s.value for s in
                     (self.interp.symtab.get(n) for n in self._all_names())
                     if s is not None},
            'poliz': self.interp.poliz,
        }

    def _all_names(self):
        names = set()
        for _, chain in self.interp.symtab.dump():
            for s in chain:
                names.add(s.name)
        return names

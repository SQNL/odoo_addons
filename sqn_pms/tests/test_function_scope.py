


class TestFunctionScope():
    def change_value(self, lines, value):
        lines.append(value)

    def controller(self):
        lines = []
        print(len(lines))

        self.change_value(lines, 1)
        print(len(lines))

        self.change_value(lines, 2)
        print(len(lines))

tfs = TestFunctionScope()
tfs.controller()

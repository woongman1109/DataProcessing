class Label:
    def __init__(self, lname, unit, axis='N', comments=""):
        self.lname = lname
        self.unit = unit
        self.axis = axis
        self.comments = comments

Tr = {
    'DrainI' : Label(r"\i(\b(I))\-(D)", 'A', 'Y'),
    'DrainV' : Label(r"\i(\b(V))\-(D)", 'V', 'X'),
    'SourceI' : Label(r"\i(\b(I))\-(S)", 'A', 'Y'),
    'SourceV' : Label(r"\i(\b(V))\-(S)", 'V', 'X'),
    'GateI' : Label(r"\i(\b(I))\-(G)", 'A', 'Y'),
    'GateV' : Label(r"\i(\b(V))\-(G)", 'V', 'X'),
    'SQRTID' : Label(r"\i(\b(I))\-(D)\+(1/2)", r"A\+(1/2)", 'Y'),
    'ABSID' : Label(r"|\i(\b(I))\-(D)|", 'A', 'Y'),
}
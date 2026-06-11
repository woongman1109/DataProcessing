# OriginWrapper.py
import originpro as op
import sys
from os.path import join

def init_Project(__path, __name):
    """
    Origin 프로젝트를 초기화하고 연결하는 Wrapper 함수
    """
    def origin_shutdown_exception_hook(exctype, value, traceback):
        """Ensures Origin gets shut down if an uncaught exception occurs"""
        op.exit()
        sys.__excepthook__(exctype, value, traceback)
    
    if op and op.oext:
        sys.excepthook = origin_shutdown_exception_hook

    # 이미 Origin이 실행 중이라면 attach, 아니라면 새로 실행
    op.attach()

    # 이미 다른 프로젝트가 열려 있으면 저장
    if op.get_lt_str('%G') != "UNTITLED":
        op.save()

    # Make Origin instance visible if external python
    if op.oext:
        op.set_show(True)
    
    opened_full = join(op.get_lt_str('%X'), op.get_lt_str('%G') + '.opju')
    passed_full = join(__path, __name)

    if __path == "" or __name == "" or passed_full == opened_full:
        op.attach()
        print("Connected to the opened OriginPro project ...")
    else:
        op.project.open(passed_full)
        print("Now opening:\n", passed_full)

    op.save()


def genBookName(name: str) -> str:
    """Book 이름을 Origin에서 사용되는 형식 '[BookName]'으로 생성"""
    return f'[{name}]'


def genSheetName(book_name: str, sheet_name: str) -> str:
    """Sheet 이름을 Origin에서 사용되는 형식 '[BookName]SheetName'으로 생성"""
    return genBookName(book_name) + sheet_name


def wrapBookFinder(sname: str, lname: str = ""):
    """
    특정 워크북(Book)을 찾는 Wrapper 함수.
    없으면 새로 생성한다.
    sname: Short Name
    lname: Long Name
    """
    __wb = (
        op.find_book(type='w', name=genBookName(sname))
        or op.find_book(type='w', name=genBookName(lname))
    )

    if __wb is None:
        print(f"Passed Book Name {sname}\nNo such Workbook found, creating new Workbook...")
        __wb = op.new_book(type='w', lname = sname)

    return __wb

def wrapBookGenerator(sname: str, lname: str = ""):
    """
    특정 워크북(Book)을 만드는 Wrapper 함수.
    이미 있는 이름이면 새로 생성한다.
    sname: Short Name
    lname: Long Name
    """
    __wb = (
        op.find_book(type='w', name=genBookName(sname))
        or op.find_book(type='w', name=genBookName(lname))
    )

    if __wb is not None:
        base_s, base_l = sname, lname
        n = 1
        while __wb is not None:
            sname = f"{base_s} ({n})"
            lname = f"{base_l} ({n})" if base_l else ""
            __wb = (
                op.find_book(type='w', name=genBookName(sname))
                or (op.find_book(type='w', name=genBookName(lname)) if lname else None)
            )
            n += 1
        print(f"Workbook '{base_s}' already exists, creating '{sname}'...")
        __wb = op.new_book(type='w', lname=sname)
    else:
        print(f"Passed Book Name {sname}\nNo such Workbook found, creating new Workbook...")
        __wb = op.new_book(type='w', lname=sname)

    return __wb

def wrapSheetFinder(WB=None, sheet_name: str = ""):
    """
    특정 워크시트(Sheet)을 찾는 Wrapper 함수.
    없으면 새로 생성한다.
    """
    __wb = WB or op.new_book(type='w')

    __wks = (
        op.find_sheet(type='w', ref=genSheetName(__wb.name, sheet_name))
        or op.find_sheet(type='w', ref=genSheetName(__wb.lname, sheet_name))
    )

    if __wks is None:
        print(f"Passed Sheet Name [{sheet_name}]\nNo such Worksheet found, creating new Worksheet...")
        __wks = __wb.add_sheet(name=sheet_name)

    return __wks


def move_col_by_longname(wks, long_name, new_index):
    """
    long_name 을 가진 컬럼을 찾아서 해당 컬럼을 new_index 위치로 이동합니다.
    """
    # 1) long_name과 일치하는 컬럼 인덱스 찾기
    old_index = None
    for col_idx in range(wks.cols):
        ln = wks.get_label(col_idx, 'L')
        if ln == long_name:
            old_index = col_idx
            break

    wks.move_cols(new_index-old_index, old_index, 1)
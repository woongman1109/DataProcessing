import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from Handler.OriginWrapper import init_Project

opj_path = r""
opj_name = ""


try:
    # 0) Origin 프로젝트 초기화
    init_Project(opj_path, opj_name)
    ##================================================================================================================================================
    ## ...


except Exception as e:
    print("An error occurred:", e)

finally:
    # Origin 프로젝트 저장 & detach
    import originpro as op
    op.save()
    op.detach()
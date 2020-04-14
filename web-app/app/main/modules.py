from flask import request
import math

def create_table(request, q, page = 1, per_page = 5):
    if "page" in request.args:
        page = int(request.args["page"])

    total_len = q.count()
    entries = []

    # if "sort_by" in request.args:
    #     sort_param = request.args["sort_by"]
    #     first = q.first()
    #     print(type(first))
    #     if type(first) != result:
    #         first = [first]

    #     for m in first:
    #         if sort_param in m.__dict__.keys():
    #             q.order_by(getattr(m, sort_param).asc())

    #     # q.sort


    print(q.first()[1].__dict__.keys())

    for p in q.offset((page-1)*per_page).limit(per_page).all():
        entries.append(p)

    max_page = math.ceil(total_len/per_page)

    return entries, total_len, max_page, page
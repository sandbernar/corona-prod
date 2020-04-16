from flask import request
import math

class TableModule:
    class WrongPageError(Exception):
        pass

    class WrongSortingParameterError(Exception):
        pass

    def __init__(self, request, q, table_head, print_entry_function, header_button = None, page = 1, per_page = 5):
        if "page" in request.args:
            try:
                page = int(request.args["page"])
            except ValueError:
                raise self.WrongPageError

        self.page = page
        self.per_page = per_page
        self.table_head_dict = table_head
        self.table_head = []
        self.request = request
        self.q = q
        self.header_button = header_button

        if page < 1:
            raise self.WrongPageError

        self.total_len = q.count()
        self.entries = []
        
        if self.total_len:
            self.sort_table()

            for p in self.q.offset((self.page-1)*self.per_page).limit(self.per_page).all():
                self.entries.append(print_entry_function(p))

        self.max_page = math.ceil(self.total_len/self.per_page)

    def sort_table(self):
        self.sort_by = None
        self.sort_by_asc = True
        # self.arrow = None
        
        if "sort_by_asc" in request.args:
            self.sort_by = request.args["sort_by_asc"]
            arrow = "↑"
        elif "sort_by_desc" in request.args:
            self.sort_by = request.args["sort_by_desc"]
            self.sort_by_asc = False
            arrow = "↓"

        for i, th in enumerate(self.table_head_dict):
            new_th = (th, th) if len(self.table_head_dict[th]) > 0 else th
            self.table_head.append(new_th)

        first = self.q.first()
        if len(self.q._entities) == 1:
            first = [first]
        
        if self.sort_by:
            for m in first:
                if self.sort_by in self.table_head_dict:
                    for s in self.table_head_dict[self.sort_by]:
                        if s in m.__dict__.keys():
                            param = getattr(type(m), s)
                            if self.sort_by_asc:
                                self.q = self.q.order_by(param.asc())
                            else:
                                self.q = self.q.order_by(param.desc())
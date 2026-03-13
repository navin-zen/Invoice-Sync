import abc
import datetime
import decimal
import functools
import os

import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

from cz_utils.decorators import ttl_cache

__all__ = (
    "Row",
    "Column",
    "Cell",
    "Formula",
    "HyperLink",
    "Cell12",
    "Cell13",
    "Cell14",
    "Cell15",
    "Cell16",
    "Cell17",
    "Cell18",
    "Cell19",
    "Cell21",
    "Cell31",
    "Cell41",
    "Cell51",
    "Cell61",
    "Cell71",
    "Cell81",
    "Cell91",
    "DropDown",
)


@ttl_cache(ttl=300)
def get_xlsxwriter_options():
    options = {
        "constant_memory": True,
    }
    tmpdir = os.environ.get("EFS_TMP_DIR")
    if tmpdir and os.path.exists(tmpdir) and os.path.isdir(tmpdir):
        options["tmpdir"] = tmpdir
    return options


class Box(metaclass=abc.ABCMeta):
    DATE_FORMAT = {"num_format": "yyyy-mm-dd"}
    # A special object to explicitly denote that we want an empty string
    # Otherwise, xlsxwriter writes a blank cell http://xlsxwriter.readthedocs.io/worksheet.html#write_blank
    EMPTY_STRING = object()
    BLANK = object()
    memoized_formats = {}  # Used by make_format()

    def __init__(
        self,
        width=None,
        height=None,
        format=None,
        level_opts=None,
        column_opts=None,
        merge_num_rows=None,
        merge_num_columns=None,
    ):
        """
        level_opts is used for collapsing rows.
        http://xlsxwriter.readthedocs.io/working_with_outlines.html#outlines

        column_opts is used for hiding columns.
        http://xlsxwriter.readthedocs.io/worksheet.html#set_column
        """
        self.height = height
        self.width = width
        self.level_opts = level_opts
        self.column_opts = column_opts
        self.merge_num_rows = merge_num_rows
        self.merge_num_columns = merge_num_columns
        if (format is None) or isinstance(format, dict):
            self.format = format
        elif isinstance(format, tuple):
            self.format = {}
            for f in format:
                self.format = Box.merge_dicts(self.format, f)
        else:
            raise TypeError("Invalid type for format")

    @abc.abstractmethod
    def render(
        self,
        workbook,
        worksheet,
        row,
        column,
        width=None,
        height=None,
        format=None,
        level_opts=None,
        column_opts=None,
        merge_num_rows=None,
        merge_num_columns=None,
    ):
        """
        Render contents into worksheet starting at (row, column).

        Returns the size of the rendered box (rows, columns).
        """
        pass

    @classmethod
    def make_format(cls, workbook, dictionary):
        """
        Create a Format object and attach it to workbook.

        We take a dictionary as input and create a xlsxwriter.format.Format
        object. This function memoizes its inputs and outputs. For the same
        input, the function will return the same output everytime.
        """
        if (dictionary is None) or isinstance(dictionary, xlsxwriter.format.Format):
            return dictionary
        if not isinstance(dictionary, dict):
            raise TypeError("In make_format, dictionary must be of type dict")
        key = (id(workbook), hash(frozenset(dictionary.items())))
        try:
            return cls.memoized_formats[key]
        except KeyError:
            return cls.memoized_formats.setdefault(key, workbook.add_format(dictionary))

    @classmethod
    def merge_dicts(self, a, b):
        """
        Merge dicts 'a' and 'b' and return the merged result.

        Keys in 'b' take precedence over those in 'a'.
        """
        a = (a or {}).copy()
        a.update(b or {})
        return a

    @classmethod
    def make_box(cls, o, format=None):
        """
        Try to make a Box out of o.
        """
        # Make a copy of format
        assert (format is None) or isinstance(format, dict)
        format = (format or {}).copy()
        # Handle various types, starting with 2-tuple
        if isinstance(o, tuple):
            try:
                (value, format) = o
                return cls.make_box(value, format=format)
            except ValueError:
                raise ValueError("Expecting a 2-tuple")
        elif isinstance(o, Box):
            return o
        elif o is Box.EMPTY_STRING:
            return Cell(o, format=format)
        elif o is Box.BLANK:
            return Cell(o, format=format)
        elif isinstance(o, str):
            return Cell(o, format=format)
        elif isinstance(o, int):
            return Cell(o, format=format)
        elif isinstance(o, (decimal.Decimal, float)):
            return Cell(o, format=format)
        elif isinstance(o, datetime.date):
            return Cell(o, format=(cls.DATE_FORMAT, format))
        elif isinstance(o, (datetime.datetime, datetime.timedelta)):
            return Cell(o, format=format)
        elif isinstance(o, list):
            return Row(o, format=format)
        else:
            raise TypeError(f"Unhandled type '{type(o)}' in Box.make_box()")


class Row(Box):
    """
    A Row in an Excel Worksheet.
    """

    def __init__(self, children, **kwargs):
        self.children = children
        super().__init__(**kwargs)

    def render(
        self,
        workbook,
        worksheet,
        row,
        column,
        width=None,
        height=None,
        format=None,
        level_opts=None,
        column_opts=None,
        merge_num_rows=None,
        merge_num_columns=None,
    ):
        """
        Render contents into worksheet starting at (row, column).

        Returns the size of the rendered box (rows, columns).
        """
        format = Box.merge_dicts(format, self.format)
        width = self.width or width
        height = self.height or height
        level_opts = self.level_opts or level_opts
        column_opts = self.column_opts or column_opts
        merge_num_rows = self.merge_num_rows or merge_num_rows
        merge_num_columns = self.merge_num_columns or merge_num_columns
        if (height is not None) or (level_opts is not None):
            worksheet.set_row(row, height=height, options=(level_opts or {}))
        (numrows, numcolumns) = (0, 0)
        for child in self.children:
            child = Box.make_box(child)
            (childrows, childcolumns) = child.render(
                workbook=workbook,
                worksheet=worksheet,
                row=row,
                column=(column + numcolumns),
                width=width,
                height=height,
                format=format,
                level_opts=level_opts,
                column_opts=column_opts,
                merge_num_rows=merge_num_rows,
                merge_num_columns=merge_num_columns,
            )
            numrows = max(numrows, childrows)
            numcolumns += childcolumns
        return (numrows, numcolumns)


class Column(Box):
    """
    A Column in an Excel Worksheet.
    """

    def __init__(self, children, **kwargs):
        self.children = children
        super().__init__(**kwargs)

    def render(
        self,
        workbook,
        worksheet,
        row,
        column,
        width=None,
        height=None,
        format=None,
        level_opts=None,
        column_opts=None,
        merge_num_rows=None,
        merge_num_columns=None,
    ):
        """
        Render contents into worksheet starting at (row, column).

        Returns the size of the rendered box (rows, columns).
        """
        format = Box.merge_dicts(format, self.format)
        width = self.width or width
        height = self.height or height
        column_opts = self.column_opts or column_opts
        merge_num_rows = self.merge_num_rows or merge_num_rows
        merge_num_columns = self.merge_num_columns or merge_num_columns
        if (width is not None) or (column_opts is not None):
            worksheet.set_column(column, column, width=width, options=(column_opts or {}))
        (numrows, numcolumns) = (0, 0)
        for child in self.children:
            child = Box.make_box(child)
            (childrows, childcolumns) = child.render(
                workbook=workbook,
                worksheet=worksheet,
                row=(row + numrows),
                column=column,
                format=format,
                level_opts=level_opts,
                column_opts=column_opts,
                width=width,
                height=height,
                merge_num_rows=merge_num_rows,
                merge_num_columns=merge_num_columns,
            )
            numrows += childrows
            numcolumns = max(numcolumns, childcolumns)
        return (numrows, numcolumns)


class Cell(Box):
    """
    A Cell in an Excel Worksheet.
    """

    def __init__(self, data, **kwargs):
        """
        Create a cell.

        The parameters are:
            data: the data to write in the cell
            format: any formatting to apply to the cell
            merge_num_rows: the number of rows to merge
            merge_num_columns: the number of columns to merge
        """
        self.data = data
        self.comment = kwargs.pop("comment", None)
        super().__init__(**kwargs)
        if isinstance(self.data, datetime.date):
            self.format = Box.merge_dicts(Box.DATE_FORMAT, self.format)

    def render(
        self,
        workbook,
        worksheet,
        row,
        column,
        width=None,
        height=None,
        format=None,
        level_opts=None,
        column_opts=None,
        merge_num_rows=None,
        merge_num_columns=None,
    ):
        """
        Render contents into worksheet starting at (row, column).

        Returns the size of the rendered box (rows, columns).
        """
        format = Box.merge_dicts(format, self.format)
        cell_format = self.make_format(workbook, format)
        width = self.width or width
        height = self.height or height
        level_opts = self.level_opts or level_opts
        column_opts = self.column_opts or column_opts
        merge_num_rows = self.merge_num_rows or merge_num_rows
        merge_num_columns = self.merge_num_columns or merge_num_columns
        if (height is not None) or (level_opts is not None):
            worksheet.set_row(row, height=height, options=(level_opts or {}))
        if (width is not None) or (column_opts is not None):
            worksheet.set_column(column, column, width=width, options=(column_opts or {}))
        if merge_num_rows or merge_num_columns:
            num_rows = merge_num_rows or 1
            num_columns = merge_num_columns or 1
            worksheet.merge_range(
                row,
                column,
                (row + num_rows - 1),
                (column + num_columns - 1),
                self.get_data(row, column),
                cell_format,
            )
            return (num_rows, num_columns)
        else:
            self.write_cell(worksheet, row, column, cell_format)
            return (1, 1)

    def get_data(self, row, column):
        """
        Get the data to be rendered at (row, column).

        This function does not use (row, column). However, the Formula
        subclass could return different values based on the curren
        position.
        """
        return self.data

    def write_cell(self, worksheet, row, column, cell_format):
        """
        Write a Cell of data.

        Mainly defined here to be overriden by sub-classes.
        """
        data = self.get_data(row, column)
        if data is Box.EMPTY_STRING:
            worksheet.write_string(row, column, "", cell_format)
        elif data is Box.BLANK:
            # By default, xlsxwriter writes None as blank, however we don't want to take any change
            worksheet.write_blank(row, column, None, cell_format)
        else:
            worksheet.write(row, column, data, cell_format)
        if self.comment:
            worksheet.write_comment(row, column, self.comment)


class HyperLink(Cell):
    """
    A Cell that contains a Hyperlink.

    This is a special case of Cell.

    The parameters are:
        data: The content to show in the cell
        url: The URL to link to
        ... any other parameters that Cell accepts.
    """

    def __init__(self, data, url, tip="", **kwargs):
        self.url = url
        self.tip = tip
        super().__init__(data, **kwargs)

    def write_cell(self, worksheet, row, column, cell_format):
        """
        Write a Cell of data.

        Mainly defined here to be overriden by sub-classes.
        """
        worksheet.write_url(row, column, self.url, cell_format, self.get_data(row, column), self.tip)


class DropDown(Cell):
    """
    A Cell that shows a dropdown of static/string values

    This is a special case of Cell.

    The parameters are:
        date: The content to show in the cell
        url: The URL to link to
        ... any other parameters that Cell accepts.
    """

    def __init__(self, data, choices, **kwargs):
        self.choices = choices
        super().__init__(data, **kwargs)

    def write_cell(self, worksheet, row, column, cell_format):
        """
        Write a Cell of data.

        Mainly defined here to be overriden by sub-classes.
        """
        dropdown_spec = {"validate": "list", "source": self.choices}
        super().write_cell(worksheet, row, column, cell_format)
        worksheet.data_validation(row, column, row, column, dropdown_spec)


class DropDownGroupedValidation(DropDown):
    def write_cell(self, worksheet, row, column, cell_format):
        """
        Write a Cell of data.

        Mainly defined here to be overriden by sub-classes.
        """
        dropdown_spec = (
            ("validate", "list"),
            ("source", self.choices),
        )
        super(DropDown, self).write_cell(worksheet, row, column, cell_format)
        worksheet.add_grouped_validation(dropdown_spec, row, column, row, column)


class Formula(Cell):
    """
    A Cell that contains a Formula.

    This is a special case of Cell.
    """

    def __init__(self, format_string, params, **kwargs):
        """
        Create a cell that hosts a formula.

        The parameters are:
            format_string: the formula text as a python format string.
                https://docs.python.org/2/library/string.html#format-string-syntax
            params: the params to apply to the format_string. params is a
                list of cell positions. Each cell position can either be a
                string "A3" in which case it will taken as it is.
                Alternatively, each cell position can be a (row_offset,
                col_offset) tuple, in which case the cell will be construed
                as being relative to the current cell being rendered.

        The other params are those that can be passed to Cell (pasted
        here for the sake of completeness).
            format: any formatting to apply to the cell
            merge_num_rows: the number of rows to merge
            merge_num_columns: the number of columns to merge
        """
        self.format_string = format_string
        self.params = params
        self.comment = kwargs.pop("comment", None)
        # IMPORTANT: We are calling Box.__init__ and not Cell.__init__ here
        super(Cell, self).__init__(**kwargs)

    def get_data(self, row, column):
        """
        Get the data to be rendered at (row, column).

        This function constructs the formula string.
        """
        if not self.params:
            return self.format_string
        elif isinstance(self.params, dict):
            params = {k: self.xl_cell_string(row, column, p) for (k, p) in self.params.items()}
            return self.format_string.format(**params)
        else:
            params = [self.xl_cell_string(row, column, p) for p in self.params]
            return self.format_string.format(*params)

    def xl_cell_string(self, row, column, c):
        """
        Return a cell name is Excel notation, for example: 'A3'.

        (row, column) is the cell location at which the cell defined by
        'c' is to be used.

        If 'c' is a string, it is returned as it is.

        If 'c' is a (row_offset, column_offet) tuple, it is added (row,
        column) and the resultant cell's notation is returned.

        If 'c' is a dict, it could have keys 'row', 'row_offset', 'column',
        'column_offet'.
            Exactly one of 'row' or 'row_offset' must be specified.
            Exactly one of 'column' or 'column_offet' must be specified.
            'row' indicates the absolute value of the row.
            'row_offset' indicates the offset from the row parameter of
                this function
            'column' indicates the absolute value of the column.
            'column_offset' indicates the offset from the column parameter of
                this function
        """
        if isinstance(c, str):
            return c
        elif isinstance(c, tuple):
            (row_offset, column_offet) = c
            return xl_rowcol_to_cell(row + row_offset, column + column_offet, row_abs=False, col_abs=False)
        elif isinstance(c, dict):
            check = (("row" in c) != ("row_offset" in c)) and (("column" in c) != ("column_offset" in c))
            if not check:
                raise ValueError("Invalid cell specifiction in Formula.xl_cell_string")
            if "row" in c:
                row = c["row"]
            else:
                row = row + c["row_offset"]
            if "column" in c:
                column = c["column"]
            else:
                column = column + c["column_offset"]
            return xl_rowcol_to_cell(row, column, row_abs=False, col_abs=False)
        else:
            raise TypeError("Unhandled cell specification in Formula.xl_cell_string")


Cell12 = functools.partial(Cell, merge_num_columns=2)
Cell13 = functools.partial(Cell, merge_num_columns=3)
Cell14 = functools.partial(Cell, merge_num_columns=4)
Cell15 = functools.partial(Cell, merge_num_columns=5)
Cell16 = functools.partial(Cell, merge_num_columns=6)
Cell17 = functools.partial(Cell, merge_num_columns=7)
Cell18 = functools.partial(Cell, merge_num_columns=8)
Cell19 = functools.partial(Cell, merge_num_columns=9)
Cell21 = functools.partial(Cell, merge_num_rows=2)
Cell31 = functools.partial(Cell, merge_num_rows=3)
Cell24 = functools.partial(Cell, merge_num_rows=2, merge_num_columns=4)
Cell34 = functools.partial(Cell, merge_num_rows=3, merge_num_columns=4)
Cell41 = functools.partial(Cell, merge_num_rows=4)
Cell51 = functools.partial(Cell, merge_num_rows=5)
Cell61 = functools.partial(Cell, merge_num_rows=6)
Cell71 = functools.partial(Cell, merge_num_rows=7)
Cell81 = functools.partial(Cell, merge_num_rows=8)
Cell91 = functools.partial(Cell, merge_num_rows=9)

import io

from django.http import HttpResponse

__all__ = ("XlsxResponseMixin",)


class XlsxResponseMixin:
    """
    A mixin to return an XLS file as response.

    Classes that extend this mixin must define a property named
    'xlsx_generator'. This property must contain a write method which
    accepts a file object as parameter and writes the XLS content to that
    file object.
    """

    xlsx_filename = "output.xlsx"

    @property
    def xlsx_generator(self):
        raise NotImplementedError("Sub-classes must override xlsx_generator.")

    def get(self, request, *args, **kwargs):
        return self.make_xls_response(self.xlsx_generator, self.xlsx_filename)

    @classmethod
    def make_xls_response(cls, xlsx_generator, xlsx_filename):
        """
        Returns an XLS response
        """
        output = io.BytesIO()
        xlsx_generator.write(output)
        return cls.make_xls_response_from_bytesio(output, xlsx_filename)

    @classmethod
    def make_xls_response_from_bytesio(cls, stream, xlsx_filename):
        """
        Make an XLSX response from an io.BytesIO object
        """
        stream.seek(0)
        response = HttpResponse(
            stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{xlsx_filename}"'
        return response

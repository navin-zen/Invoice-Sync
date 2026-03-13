"from django.utils.deconstruct import deconstructible"

"from storages.backends.s3boto3 import S3BotoStorage"


# @deconstructible
# class MyS3BotoStorage(S3BotoStorage):
#     def cz_url(self, name, response_headers):
#         """
#         Allow user to specify custom response headers while downloading the
#         file.

#         http://docs.aws.amazon.com/AmazonS3/latest/API/RESTObjectGET.html#RESTObjectGET-requests
#         """
#         name = self._normalize_name(self._clean_name(name))
#         if self.custom_domain:
#             return "%s//%s/%s" % (self.url_protocol, self.custom_domain, name)
#         return self.connection.generate_url(
#             self.querystring_expire,
#             method="GET",
#             bucket=self.bucket.name,
#             key=self._encode_name(name),
#             response_headers=response_headers,
#             query_auth=self.querystring_auth,
#             force_http=not self.secure_urls,
#         )


# PROTECTED_STORAGE = MyS3BotoStorage(
#     acl="private",
#     querystring_auth=True,
#     querystring_expire=600,  # expires in 10 minutes
#     host="s3.ap-south-1.amazonaws.com",
# )

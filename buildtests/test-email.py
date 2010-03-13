import sys

if sys.version_info >= (2,5):
    from email import utils
    from email.header import Header
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.nonmultipart import MIMENonMultipart
else:
    print "test-email skipped"

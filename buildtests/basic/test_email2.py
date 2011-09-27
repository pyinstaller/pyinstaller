# test case for ticket #316

import sys
if sys.version_info >= (2,5):
    from email.MIMEMultipart import MIMEMultipart
else:
    print "test_email2 skipped"

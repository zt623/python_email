# -*- coding: utf-8 -*-
import sys  
reload(sys)  
sys.setdefaultencoding('utf8') 

import smtplib
from email.mime.text import MIMEText
from email.encoders import encode_base64
from email.mime.base import MIMEBase
from email.header import Header
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart 
from email.utils import make_msgid , parseaddr , formataddr , formatdate
import datetime

MAIL_SERVER = ""
MAIL_USERNAME = ""
MAIL_PASSWORD = ""
MAIL_REPLY = ""

import os

def send_attachment_mail(attach,content,receiver,file_type = 'text/csv'):

    try:

        f = open(attach)

        msg = Message(content,MAIL_USERNAME,receiver)
        msg.body = content
        msg.html = content
        msg.reply_to = MAIL_REPLY 
        msg.recipients = receiver
        msg.attach(os.path.basename(attach),file_type,f.read())
        send_async_email(receiver,msg)

    except Exception,e:
        print e

def send_result_mail(content,receiver):

    try:

        msg = Message(content,MAIL_USERNAME,receiver)
        msg.body = content
        msg.html = content
        msg.reply_to = MAIL_REPLY 
        msg.recipients = receiver
        send_async_email(receiver,msg)

    except Exception,e:
        print e

def send_async_email(receiver,msg):
	smtp = smtplib.SMTP()
	smtp.connect(MAIL_SERVER)
	smtp.login(MAIL_USERNAME,MAIL_PASSWORD)
	smtp.sendmail(MAIL_USERNAME,receiver,msg.as_string())
	smtp.quit()


def force_text(s, encoding='utf-8', errors='stricts'):
    if isinstance(s, unicode):
        return s
    try:
        if not isinstance(s, basestring):
            if hasattr(s, '__unicode__'):
                s = s.__unicode__()
            else:
                s = unicode(bytes(s), encoding, errors)
        else:
            s = s.decode(encoding, errors)
    except UnicodeDecodeError, e:
        if not isinstance(s, Exception):
            raise FlaskMailUnicodeDecodeError(s, *e.args)
        else:
            s = ' '.join([force_text(arg, encoding, errors) for arg in s])
    return s

def sanitize_address(addr, encoding='utf-8'):
    if isinstance(addr, basestring):
        addr = parseaddr(force_text(addr))
    nm, addr = addr

    # This try-except clause is needed on Python 3 < 3.2.4
    # http://bugs.python.org/issue14291
    try:
        nm = Header(nm, encoding).encode()
    except UnicodeEncodeError:
        nm = Header(nm, 'utf-8').encode()

    try:
        addr.encode('ascii')
    except UnicodeEncodeError:  # IDN
        if '@' in addr:
            localpart, domain = addr.split('@', 1)
            localpart = str(Header(localpart, encoding))
            domain = domain.encode('idna').decode('ascii')
            addr = '@'.join([localpart, domain])
        else:
            addr = Header(addr, encoding).encode()
    return formataddr((nm, addr))


def sanitize_addresses(addresses):
    return map(lambda e: sanitize_address(e), addresses)

class Attachment(object):
    """Encapsulates file attachment information.

    :versionadded: 0.3.5

    :param filename: filename of attachment
    :param content_type: file mimetype
    :param data: the raw file data
    :param disposition: content-disposition (if any)
    """

    def __init__(self, filename=None, content_type=None, data=None,
                 disposition=None, headers=None):
        self.filename = filename
        self.content_type = content_type
        self.data = data
        self.disposition = disposition or 'attachment'
        self.headers = headers or {}

class Message(object):
    """Encapsulates an email message.

    :param subject: email subject header
    :param recipients: list of email addresses
    :param body: plain text message
    :param html: HTML message
    :param sender: email sender address, or **MAIL_DEFAULT_SENDER** by default
    :param cc: CC list
    :param bcc: BCC list
    :param attachments: list of Attachment instances
    :param reply_to: reply-to address
    :param date: send date
    :param charset: message character set
    :param extra_headers: A dictionary of additional headers for the message
    """

    def __init__(self, subject,
                 recipients=None,
                 body=None,
                 html=None,
                 sender=None,
                 cc=None,
                 bcc=None,
                 attachments=None,
                 reply_to=None,
                 date=None,
                 charset=None,
                 extra_headers=None):

        sender = sender

        if isinstance(sender, tuple):
            sender = "%s <%s>" % sender

        self.recipients = recipients or []
        self.subject = subject
        self.sender = sender
        self.reply_to = reply_to
        self.cc = cc or []
        self.bcc = bcc or []
        self.body = body
        self.html = html
        self.date = date
        self.msgId = make_msgid()
        self.charset = charset
        self.extra_headers = extra_headers
        self.attachments = attachments or []

    @property
    def send_to(self):
        return set(self.recipients) | set(self.bcc or ()) | set(self.cc or ())

    def _mimetext(self, text, subtype='plain'):
        """Creates a MIMEText object with the given subtype (default: 'plain')
        If the text is unicode, the utf-8 charset is used.
        """
        charset = self.charset or 'utf-8'
        return MIMEText(text, _subtype=subtype, _charset=charset)

    def as_string(self):
        """Creates the email"""

        attachments = self.attachments or []

        if len(attachments) == 0 and not self.html:
            # No html content and zero attachments means plain text
            msg = self._mimetext(self.body)
        elif len(attachments) > 0 and not self.html:
            # No html and at least one attachment means multipart
            msg = MIMEMultipart()
            msg.attach(self._mimetext(self.body))
        else:
            # Anything else
            msg = MIMEMultipart()
            alternative = MIMEMultipart('alternative')
            alternative.attach(self._mimetext(self.body, 'plain'))
            alternative.attach(self._mimetext(self.html, 'html'))
            msg.attach(alternative)

        msg['Subject'] = self.subject
        msg['From'] = sanitize_address(self.reply_to)
        msg['To'] = str(self.recipients)

        msg['Date'] = formatdate(self.date, localtime=True)
        # see RFC 5322 section 3.6.4.
        msg['Message-ID'] = self.msgId

        if self.cc:
            msg['Cc'] = ', '.join(list(set(sanitize_addresses(self.cc))))

        if self.reply_to:
            msg['Reply-To'] = sanitize_address(self.reply_to)

        if self.extra_headers:
            for k, v in self.extra_headers.iteritems():
                msg[k] = v

        for attachment in attachments:
            f = MIMEBase(*attachment.content_type.split('/'))
            f.set_payload(attachment.data)
            encode_base64(f)

            f.add_header('Content-Disposition', '%s;filename=%s' %
                         (attachment.disposition, attachment.filename))

            for key, value in attachment.headers:
                f.add_header(key, value)

            msg.attach(f)

        return msg.as_string()

    def __str__(self):
        return self.as_string()

    def has_bad_headers(self):
        """Checks for bad headers i.e. newlines in subject, sender or recipients.
        """

        reply_to = self.reply_to or ''
        for val in [self.subject, self.sender, reply_to] + self.recipients:
            for c in '\r\n':
                if c in val:
                    return True
        return False

    def is_bad_headers(self):
        from warnings import warn
        msg = 'is_bad_headers is deprecated, use the new has_bad_headers method instead.'
        warn(DeprecationWarning(msg), stacklevel=1)
        return self.has_bad_headers()

    def add_recipient(self, recipient):
        """Adds another recipient to the message.

        :param recipient: email address of recipient.
        """

        self.recipients.append(recipient)

    def attach(self,
               filename=None,
               content_type=None,
               data=None,
               disposition=None,
               headers=None):
        """Adds an attachment to the message.

        :param filename: filename of attachment
        :param content_type: file mimetype
        :param data: the raw file data
        :param disposition: content-disposition (if any)
        """

        self.attachments.append(
            Attachment(filename, content_type, data, disposition, headers))


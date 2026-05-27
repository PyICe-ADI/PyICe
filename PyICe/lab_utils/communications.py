"""Communications utility.

>>> from PyICe.lab_utils.communications import email

"""
import smtplib
import re
import os
from email.mime.text import MIMEText  # send email/sms message from script
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from PyICe.lab_utils.clean_unicode import clean_unicode


class email(object):
    '''Send email messages—including attachments—through an SMTP server.'''
    def __init__(self, destination, smtp_server, sender):
        """Configure the email transport with recipient, server, and sender addresses.
        Stores configuration in ``destination``, ``sender``, ``smtp_server``
        for use by other methods.

        Initializes 3 instance attributes that configure the object's behavior.


        >>> e = email("user@example.com", "smtp.example.com", "lab@example.com")
        >>> e.destination
        'user@example.com'
        >>> e.sender
        'lab@example.com'

        Args:
            destination: Recipient's email address (e.g. ``'user@example.com'``).
            smtp_server: Outgoing SMTP server address, optionally with port
                (e.g. ``'smtp.example.com:25'``).
            sender: ``From`` address shown in outgoing messages.
        """
        self.destination = destination
        self.smtp_server = smtp_server
        self.sender = sender
    def send_raw(self, body, subject=None, attachment_filenames=None,
                 attachment_MIMEParts=None, _subtype='html'):
        """Compose a MIME message from raw body text and send it via SMTP.

        Handles both simple (text-only) and multipart messages. File
        attachments are read from disk; pre-built ``MIMEBase`` objects can
        also be attached directly.


        >>> from PyICe.lab_utils.communications import email
        >>> hasattr(email, 'send_raw')
        True

        Args:
            body: Message body string (interpreted according to *_subtype*).
            subject: Email subject line, or ``None`` to omit.
            attachment_filenames: List of file paths to attach (read as
                binary). Defaults to ``[]``.
            attachment_MIMEParts: List of pre-encoded ``email.mime``
                objects to attach verbatim. Defaults to ``[]``.
            _subtype: MIME subtype for the body (``'html'`` or ``'plain'``).
        """
        if attachment_filenames is None:
            attachment_filenames = []
        if attachment_MIMEParts is None:
            attachment_MIMEParts = []
        if len(attachment_filenames) == 0 and len(attachment_MIMEParts) == 0:
            message = MIMEText(body, _subtype=_subtype, _charset="utf-8")
        else:
            message = MIMEMultipart('mixed')
            # _subtype = 'plain'?
            # https://docs.python.org/3/library/email.mime.html
            message.attach(MIMEText(body, _subtype=_subtype, _charset='utf-8'))
            for attachment in attachment_filenames:
                filebytes = open(attachment, "rb")
                Attachment = MIMEApplication(filebytes.read())
                Attachment.add_header(
                    'content-disposition',
                    'attachment',
                    filename=os.path.basename(attachment))
                message.attach(Attachment)
            for attachment in attachment_MIMEParts:
                # Assume any headers and MIME encoding have already been
                # completed elsewhere as necessary.
                message.attach(attachment)
        if (subject is not None):
            message['Subject'] = subject
        message['To'] = self.destination
        message['From'] = self.sender
        server = smtplib.SMTP(self.smtp_server)
        server.ehlo()
        server.sendmail(self.sender, self.destination, message.as_string())
        server.quit()

    def send(self, body, subject=None, attachment_filenames=None,
             attachment_MIMEParts=None):
        """Send an email using monospaced HTML formatting.

        Convenience method that delegates to ``send_html_monospace``.


        >>> from PyICe.lab_utils.communications import email
        >>> hasattr(email, 'send')
        True

        Args:
            body: Plain-text message body (will be rendered in monospace HTML).
            subject: Email subject line, or ``None`` to omit.
            attachment_filenames: List of file paths to attach.
            attachment_MIMEParts: List of pre-encoded ``email.mime`` objects
                to attach.
        """
        self.send_html_monospace(
            body=body,
            subject=subject,
            attachment_filenames=attachment_filenames,
            attachment_MIMEParts=attachment_MIMEParts)

    def send_html_monospace(self, body, subject=None,
                            attachment_filenames=None, attachment_MIMEParts=None):
        """Wrap a plain-text body in monospace HTML and send it as an email.

        Converts plain text to an HTML document styled with Courier New,
        replacing spaces with ``&nbsp;`` (outside of HTML tags) and
        preserving line breaks. Useful for sending lab reports or log output
        that must keep column alignment in the recipient's mail client.


        >>> from PyICe.lab_utils.communications import email
        >>> hasattr(email, 'send_html_monospace')
        True

        Args:
            body: Plain-text message body to be wrapped in monospace HTML.
            subject: Email subject line, or ``None`` to omit.
            attachment_filenames: List of file paths to attach. Defaults to
                ``[]``.
            attachment_MIMEParts: List of pre-encoded ``email.mime`` objects
                to attach. Defaults to ``[]``.
        """
        if attachment_filenames is None:
            attachment_filenames = []
        if attachment_MIMEParts is None:
            attachment_MIMEParts = []
        tag_pat = re.compile(pattern='(<[^<>]*?>)')
        html_body = '<html>\n'
        html_body += '<head>\n'
        html_body += '<!-- $Id$ -->\n'
        html_body += '<!-- $DateTime$ -->\n'
        html_body += '<!-- $Change$ -->\n'
        html_body += '<style>\n'
        html_body += 'body {\n'
        html_body += '  font-family: "Courier New", Courier, "Lucida Console", monospace;\n'
        html_body += '}\n'
        html_body += '</style>\n'
        html_body += '</head>\n'
        html_body += '<body>\n'
        # html_body += f'{body}\n'
        html_body += '<p>\n'
        for line in body.splitlines():
            nbspline = ''
            for idx, segment in enumerate(tag_pat.split(line)):
                if idx % 2:
                    # odd indices are separators (tags)
                    nbspline += segment
                else:
                    # even indices are outside tags
                    nbspline += segment.replace(" ", "&nbsp;")
            if nbspline.startswith("\t"):
                html_body += f'\t<span style="margin-left: 40px">{nbspline.lstrip()}</span><br/>\n'
            else:
                html_body += f'{nbspline}<br/>\n'
        html_body += '</p>\n'
        html_body += '</body>\n'
        html_body += '</html>\n'
        self.send_raw(
            body=html_body,
            subject=subject,
            attachment_filenames=attachment_filenames,
            attachment_MIMEParts=attachment_MIMEParts,
            _subtype='html')


class sms(email):
    '''Send SMS messages via carrier email-to-SMS gateways.

    >>> from PyICe.lab_utils.communications import sms
    >>> sms is not None
    True

    '''
    def __init__(self, mobile_number, carrier, smtp_server, sender):
        """Build the carrier-specific email address for SMS delivery.

        Strips non-digit characters and any leading country code from
        *mobile_number*, then appends the appropriate carrier gateway domain.


        >>> s = sms("(555) 123-4567", "verizon", "smtp.example.com", "lab@example.com")
        >>> s.destination
        '5551234567@vtext.com'
        >>> s2 = sms("1-800-555-0199", "tmobile", "smtp.example.com", "lab@example.com")
        >>> s2.destination
        '8005550199@tmomail.net'

        Args:
            mobile_number: 10-digit US phone number with area code.
                Dashes, dots, spaces, and a leading ``1`` are stripped
                automatically.
            carrier: Carrier name—one of ``'verizon'``, ``'tmobile'``
                (or ``'t-mobile'``), ``'att'`` (or ``'at&t'``),
                ``'sprint'``, or ``'nextel'`` (case-insensitive).
            smtp_server: Outgoing SMTP server address, optionally with port
                (e.g. ``'smtp.example.com:25'``).
            sender: ``From`` address shown in the outgoing message.

        Raises:
            Exception: If *mobile_number* does not resolve to exactly
                10 digits, or *carrier* is not recognised.
        """
        sms_email = ''
        for digit in str(mobile_number):
            if digit.isdigit():  # remove dashes, dots, spaces, and whatever other non-digits came in
                sms_email += digit
        sms_email = sms_email.lstrip('1')  # remove country code
        if (len(sms_email) != 10):
            raise Exception(
                'mobile_number argument must be a 10-digit phone number with area code')
        carrier = carrier.lower()
        if (carrier == 'verizon'):
            sms_email += '@vtext.com'
        elif (carrier == 't-mobile' or carrier == 'tmobile'):
            sms_email += '@tmomail.net'
        elif (carrier == 'att' or carrier == 'at&t'):
            sms_email += '@txt.att.net '
        elif (carrier == 'sprint'):
            sms_email += '@messaging.sprintpcs.com'
        elif (carrier == 'nextel'):
            sms_email += '@page.nextel.com'
        else:
            # look up additional sms email gateways here:
            # http://en.wikipedia.org/wiki/List_of_SMS_gateways
            raise Exception(
                'carrier argument must be "verizon", "t-mobile", "att", "sprint", or "nextel" unless you add your carrier to the list')
        email.__init__(self, sms_email, smtp_server, sender)
    def send(self, body, subject = None, attachments = []):
        """Send an SMS by emailing the carrier's gateway, cleaning Unicode first.

        Non-ASCII characters in *body* and *subject* are transliterated to
        their closest ASCII equivalents so they survive the SMS gateway.


        >>> from PyICe.lab_utils.communications import sms
        >>> hasattr(sms, 'send')
        True

        Args:
            body: Text message body (Unicode-safe).
            subject: Message subject, or ``None`` to omit.
            attachments: List of file paths to attach.
        """
        email.send(
            self,
            clean_unicode(body) if body is not None else None,
            clean_unicode(subject) if subject is not None else None,
            attachments)

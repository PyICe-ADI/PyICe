import smtplib, re, os
from email.mime.text import MIMEText #send email/sms message from script
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

class email(object):
    '''sends email to specified destination from ADI mail server. Only works on ADI trusted internal network.'''
    def __init__(self, destination): #ADI internal network only
        '''destination is the recipient's email address'''
        self.destination = destination
        self.sender = 'PyICe_noreply@analog.com'
    def send_raw(self, body, subject=None, attachment_filenames=[], attachment_MIMEParts=[], _subtype='html'):
        '''compose MIME message with proper headers and send'''
        if len(attachment_filenames) == 0 and len(attachment_MIMEParts) == 0:
            message = MIMEText(body, _subtype=_subtype, _charset="utf-8")
        else:
            message = MIMEMultipart('mixed')
            message.attach(MIMEText(body, _subtype=_subtype, _charset='utf-8')) #_subtype = 'plain'? https://docs.python.org/3/library/email.mime.html
            for attachment in attachment_filenames:
                filebytes = open(attachment, "rb")
                Attachment = MIMEApplication(filebytes.read())
                Attachment.add_header('content-disposition', 'attachment', filename = os.path.basename(attachment))
                message.attach(Attachment)
            for attachment in attachment_MIMEParts:
                #Assume any headers and MIME encoding have already been completed elsewhere as necessary.
                message.attach(attachment)
        if (subject is not None):
            message['Subject'] = subject
        message['To'] = self.destination
        message['From'] = self.sender
        server = smtplib.SMTP('mailhost.analog.com:25')
        server.ehlo()
        server.sendmail(self.sender, self.destination, message.as_string())
        server.quit()
    def send(self, body, subject=None, attachment_filenames=[], attachment_MIMEParts=[]):
        self.send_html_monospace(body=body, subject=subject, attachment_filenames=attachment_filenames, attachment_MIMEParts=attachment_MIMEParts)
    def send_html_monospace(self, body, subject=None, attachment_filenames=[], attachment_MIMEParts=[]):
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
            for idx,segment in enumerate(tag_pat.split(line)):
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
        self.send_raw(body=html_body, subject=subject, attachment_filenames=attachment_filenames, attachment_MIMEParts=attachment_MIMEParts, _subtype='html')

class sms(email):
    '''Extends email class to send sms messages through several carriers' email to sms gateways'''
    def __init__(self, mobile_number, carrier):
        '''carrier is 'verizon', 'tmobile', 'att', 'sprint', or 'nextel' '''
        sms_email = ''
        for digit in str(mobile_number):
            if digit.isdigit(): #remove dashes, dots, spaces, and whatever other non-digits came in
                sms_email += digit
        sms_email = sms_email.lstrip('1') #remove country code
        if (len(sms_email) != 10):
            raise Exception('mobile_number argument must be a 10-digit phone number with area code')
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
            #look up additional sms email gateways here: http://en.wikipedia.org/wiki/List_of_SMS_gateways
            raise Exception('carrier argument must be "verizon", "t-mobile", "att", "sprint", or "nextel" unless you add your carrier to the list')
        email.__init__(self, sms_email)
    def send(self, body, subject = None, attachments = []):
        email.send(self, clean_unicode(body) if body is not None else None, clean_unicode(subject) if subject is not None else None, attachments)
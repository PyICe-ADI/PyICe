"""Tests for email."""
from PyICe.lab_utils.communications import email
from email.mime.image import MIMEImage
import cairosvg  # pylint: disable=import-error; optional dependency required only for this test script

dave_mail = email('recipient@example.com', smtp_server='smtp.example.com:25', sender='noreply@example.com')


with open(r'path/to/example.svg', 'rb') as img:
    pic1_bytes = img.read()
    pic1 = MIMEImage(pic1_bytes, 'image/svg+xml')
    pic1.add_header('content-disposition', 'attachment; filename="foo.svg"')
with open(r'path/to/example.png', 'rb') as img:
    pic2 = MIMEImage(img.read(), 'image/png')
    pic2.add_header('Content-Disposition', 'inline')
    pic2.add_header('Content-ID', '<dice>')


pic3_bytes = cairosvg.svg2png(bytestring=pic1_bytes)
pic3 = MIMEImage(pic3_bytes, 'image/png')
# pic3.add_header('content-disposition', 'attachment; filename="baz.png"')
pic3.add_header('Content-Disposition', 'inline')
pic3.add_header('Content-ID', '<waves>')


# pic.add_header('Content-ID', '<myimg>')


# dave_mail.send('<html><body>asdf <img src="cid:myimg"\></body></html>', subject="image test", attachment_objects=[pic])
dave_mail.send(  # pylint: disable=unexpected-keyword-arg; test script uses outdated API - current API uses attachment_MIMEParts
    '<html><body>1<img src="cid:dice"/>2<img src="cid:waves"/></body></html>',
    subject="image test",
    attachment_objects=[
        pic1,
        pic2,
        pic3])

from PyICe import lab_utils
from email.mime.image import MIMEImage
import cairosvg

dave_mail = lab_utils.email('david.simmons@analog.com')


with open(r'C:\Users\DSimmons\projects\stowe_eval\tests\boost\ch0_ilim_waveforms\archive\boost_fib_DUT3_2020_07_09\ch0_ilim_waveforms_2020_07_09_14_40_53\plots\ch0_waveforms.svg', 'rb') as img:
    pic1_bytes = img.read()
    pic1 = MIMEImage(pic1_bytes, 'image/svg+xml')
    pic1.add_header('content-disposition', 'attachment; filename="foo.svg"')
with open(r'C:\Users\DSimmons\OneDrive - Analog Devices, Inc\Pictures\dados-png-2.png', 'rb') as img:
    pic2 = MIMEImage(img.read(), 'image/png')
    # pic2.add_header('content-disposition', 'attachment; filename="bar.png"')
    pic2.add_header('Content-Disposition', 'inline')
    pic2.add_header('Content-ID', '<dice>')


pic3_bytes = cairosvg.svg2png(bytestring=pic1_bytes)
pic3 = MIMEImage(pic3_bytes, 'image/png')
# pic3.add_header('content-disposition', 'attachment; filename="baz.png"')
pic3.add_header('Content-Disposition', 'inline')
pic3.add_header('Content-ID', '<waves>')




# pic.add_header('Content-ID', '<myimg>')


# dave_mail.send('<html><body>asdf <img src="cid:myimg"\></body></html>', subject="image test", attachment_objects=[pic])
dave_mail.send('<html><body>1<img src="cid:dice"/>2<img src="cid:waves"/></body></html>', subject="image test", attachment_objects=[pic1, pic2, pic3])
"""Tests for humanoid."""
from PyICe import lab_core
from PyICe.lab_utils.communications import email
from PyICe.virtual_instruments import instrument_humanoid

# import logging
# logging.basicConfig(level=logging.DEBUG)

m = lab_core.master()
em = email(destination='recipient@example.com', smtp_server='smtp.example.com:25', sender='noreply@example.com')
ih = instrument_humanoid(
    notification_function=lambda msg: em.send(
        msg,subject="Lab requires attention!"))
m.add(ih)
wc = ih.add_channel_write('write_channel')
rc = ih.add_channel_read('read_channel')
rc1 = ih.add_channel_read('integer_read_channel', integer_size=1)
rc1.add_preset('eleven', 11)
nc = ih.add_channel_notification_enable('enable_email_notifications')
m.write('enable_email_notifications', False)
m.background_gui()
print(type(m.read('read_channel')))
m.write('write_channel', 99)
foo = m.read_all_channels()
print(foo, {k: type(v) for k, v in foo.items()})
for ch in foo:
    print(ch, foo[ch], type(foo[ch]))

logger = lab_core.logger(m)
logger.new_table('manual_data', replace_table='copy')
for i in range(5):
    m.write('write_channel', i)
    print(logger.log())

from PyICe import virtual_instruments, lab_core

m = lab_core.master()
d = m.add_channel_dummy('dummy_ch')
d.write(5)
#e = virtual_instruments.expect(verbose_pass=True, err_msg_prefix='* Zach Broke It * ', pass_msg_prefix='* Zach Fixed It * ')
e = virtual_instruments.expect(verbose_pass=True)
m.add(e)

c = e.add_channel_expect_pct('comp', d, 0.01, en_immediate=True, en_assertion=True)
for i in [5, 5.04, 5.05, 5.051]:
    try:
        c.write(i)
    except Exception as exc:
        print(type(exc), exc)
    print(c.read())

c2 = e.add_channel_expect_pct('comp2', d, 0.01, en_immediate=False, en_assertion=True)
c2.write(5)
for i in range(200):
    d.write(4.9 + i/1000.)
    try:
        m.read_all_channels()
    except Exception as exc:
        print(type(exc), exc)

e.add_channel_tolerance('c2_tol', c2).write(0.02)
for i in range(200):
    d.write(4.9 + i/1000.)
    try:
        m.read_all_channels()
    except Exception as exc:
        print(type(exc), exc)

e.add_channel_enable('c2_enable', c2).write(False)
for i in range(200):
    d.write(4.9 + i/1000.)
    try:
        m.read_all_channels()
    except Exception as exc:
        print(type(exc), exc)

print(m.read_all_channels())
    
e.add_channel_expect_abs('comp3', d, 0.01, en_immediate=False, en_assertion=False).write(5)
for i in range(20):
    d.write(4.98 + i/1000.)
    print(m.read_all_channels())

#Use bound instance low-level compare methods
print(e.compare_exact(5,5))
print(e.compare_abs(5.02, 5, 0.025))
print(e.compare_abs(4.97, 5, 0.025))

#Use unbound class low-level compare methods
print(virtual_instruments.expect.compare_exact(5,5))
print(virtual_instruments.expect.compare_exact(5,4.999999))
print(virtual_instruments.expect.compare_abs(5.02, 5, 0.025))
print(virtual_instruments.expect.compare_abs(4.97, 5, 0.025))
print(virtual_instruments.expect.compare_pct(4.97, 5, 0.05))

#Use bound instance check methods
e.check_exact(5,5,en_assertion=False)
e.check_exact(5,4.999999,en_assertion=False, name='sig_foo')
e.check_abs(5.02, 5, 0.025,en_assertion=False, name='sig_bar')
try:
    e.check_abs(4.97, 5, 0.025,en_assertion=True)
    e.check_pct(4.97, 5, 0.05,en_assertion=True)
except virtual_instruments.ExpectException as exc:
        print(type(exc), exc)



m.gui()

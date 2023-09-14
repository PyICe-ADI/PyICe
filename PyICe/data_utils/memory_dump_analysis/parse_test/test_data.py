import objutils

sections = []
for i in range(16):
    sections.append(objutils.Section(start_address = i<<4, data=[i for i in range(i<<4, (i<<4)+0x10)]))
golden_img = objutils.Image(sections)
golden_img.hexdump()
#objutils.dump("srec", "golden.srec", golden_img)

test = objutils.load('srec', 'zero_to_ff.srec')

assert test == golden_img

stowe = objutils.load('srec', 'stowe.srec')
stowe.hexdump()
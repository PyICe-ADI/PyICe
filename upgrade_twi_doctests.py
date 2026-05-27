"""Upgrade twi_interface hasattr doctests to functional i2c_dummy tests."""
import ast, re

with open('PyICe/twi_interface.py', 'rb') as f:
    content = f.read()
eol = b'\r\n' if b'\r\n' in content else b'\n'

# Map: (class_name, method_name) -> new doctest lines
# 'R' prefix = needs redirect_stdout wrapping
UPGRADES = {
    # === twi_interface base class methods ===
    ('twi_interface', 'start'): [
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.start()',
        'True',
    ],
    ('twi_interface', 'restart'): [
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.restart()',
        'True',
    ],
    ('twi_interface', 'stop'): [
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.stop()',
        'True',
    ],
    ('twi_interface', 'write'): [
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.write(0xFF)',
        'True',
    ],
    ('twi_interface', 'set_frequency'): None,  # keep hasattr (raises on dummy)
    ('twi_interface', 'scan'): [
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> result = d.scan()',
        '>>> len(result)',
        '128',
        '>>> result[0]',
        '0',
        '>>> result[-1]',
        '254',
    ],
    ('twi_interface', 'quick_command_rd'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     d.quick_command_rd(0x48)',
    ],
    ('twi_interface', 'quick_command_wr'): [
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.quick_command_wr(0x48)',
    ],
    ('twi_interface', 'send_byte_pec'): [
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.send_byte_pec(addr7=0x48, data8=0xAB)',
    ],
    ('twi_interface', 'receive_byte_pec'): [
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d._cc_data[None] = 0xAB',
        '>>> d.receive_byte_pec(addr7=0x48)',
        '171',
    ],
    ('twi_interface', 'alert_response'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d._read_queue = [0x90]',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     d.alert_response()',
        '72',
    ],
    ('twi_interface', 'alert_response_pec'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> pec_val = d.pec([d.read_addr(0xC), 0x90])',
        '>>> d._read_queue = [0x90, pec_val]',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     d.alert_response_pec()',
        '72',
    ],
    ('twi_interface', 'process_call'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d._read_queue = [0x12, 0x34]',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     hex(d.process_call(0x48, 0x10, 0x5678))',
        "'0x3412'",
    ],
    ('twi_interface', 'process_call_pec'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> pec_val = d.pec([d.write_addr(0x48), 0x10, 0x78, 0x56,',
        '...                   d.read_addr(0x48), 0x12, 0x34])',
        '>>> d._read_queue = [0x12, 0x34, pec_val]',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     hex(d.process_call_pec(0x48, 0x10, 0x5678))',
        "'0x3412'",
    ],
    ('twi_interface', 'block_write'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     d.block_write(0x48, 0x10, [0xAA, 0xBB, 0xCC])',
    ],
    ('twi_interface', 'block_write_pec'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     d.block_write_pec(0x48, 0x10, [0xAA, 0xBB, 0xCC])',
    ],
    ('twi_interface', 'block_read'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d._read_queue = [3, 0xDE, 0xAD, 0xBE]',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     d.block_read(0x48, 0x10)',
        '[222, 173, 190]',
    ],
    ('twi_interface', 'block_read_pec'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> pec_val = d.pec([d.write_addr(0x48), 0x10,',
        '...                   d.read_addr(0x48), 3, 0xDE, 0xAD, 0xBE])',
        '>>> d._read_queue = [3, 0xDE, 0xAD, 0xBE, pec_val]',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     d.block_read_pec(0x48, 0x10)',
        '[222, 173, 190]',
    ],
    ('twi_interface', 'block_process_call'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d._read_queue = [2, 0xDE, 0xAD]',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     d.block_process_call(0x48, 0x10, [0x01, 0x02])',
        '[222, 173]',
    ],
    ('twi_interface', 'block_process_call_pec'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> pec_val = d.pec([d.write_addr(0x48), 0x10, 2, 0x01, 0x02,',
        '...                   d.read_addr(0x48), 2, 0xDE, 0xAD])',
        '>>> d._read_queue = [2, 0xDE, 0xAD, pec_val]',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     d.block_process_call_pec(0x48, 0x10, [0x01, 0x02])',
        '[222, 173]',
    ],
    ('twi_interface', '_read_x_list'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.write_register(0x48, 0x10, 0xAB, 8, False)',
        '>>> d.write_register(0x48, 0x20, 0xCD, 8, False)',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     result = d._read_x_list(0x48, [0x10, 0x20], d.read_byte)',
        '>>> result[0x10]',
        '171',
        '>>> result[0x20]',
        '205',
    ],
    ('twi_interface', 'read_byte_list'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.write_register(0x48, 0x10, 0xAB, 8, False)',
        '>>> d.write_register(0x48, 0x20, 0xCD, 8, False)',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     result = d.read_byte_list(0x48, [0x10, 0x20])',
        '>>> result[0x10]',
        '171',
    ],
    ('twi_interface', 'read_byte_list_pec'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.write_register(0x48, 0x10, 0xAB, 8, True)',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     result = d.read_byte_list_pec(0x48, [0x10])',
        '>>> result[0x10]',
        '171',
    ],
    ('twi_interface', 'read_word_list'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.write_register(0x48, 0x30, 0x1234, 16, False)',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     result = d.read_word_list(0x48, [0x30])',
        '>>> hex(result[0x30])',
        "'0x1234'",
    ],
    ('twi_interface', 'read_word_list_pec'): [
        '>>> import io, contextlib',
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.write_register(0x48, 0x30, 0x1234, 16, True)',
        '>>> with contextlib.redirect_stdout(io.StringIO()):',
        '...     result = d.read_word_list_pec(0x48, [0x30])',
        '>>> hex(result[0x30])',
        "'0x1234'",
    ],
    ('twi_interface', 'read_register_list'): [
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.write_register(0x48, 0x10, 0xAB, 8, False)',
        '>>> result = d.read_register_list(0x48, [0x10], data_size=8, use_pec=False)',
        '>>> result[0x10]',
        '171',
    ],

    # === i2c_dummy subclass methods ===
    ('i2c_dummy', 'start'): [
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.start()',
        'True',
    ],
    ('i2c_dummy', 'stop'): [
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.stop()',
        'True',
    ],
    ('i2c_dummy', 'write'): [
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.write(0xFF)',
        'True',
    ],
    ('i2c_dummy', 'read_register_list'): [
        '>>> d = i2c_dummy(delay=0, p_change=0, seed=42)',
        '>>> d.write_register(0x48, 0x10, 0xAB, 8, False)',
        '>>> result = d.read_register_list(0x48, [0x10], data_size=8, use_pec=False)',
        '>>> result[0x10]',
        '171',
    ],
}

# Parse and find all hasattr doctest blocks to replace
tree = ast.parse(content)
lines = content.split(eol)

replacements = []  # (start_idx, end_idx, new_lines)

for cls_node in ast.iter_child_nodes(tree):
    if not isinstance(cls_node, ast.ClassDef):
        continue
    cls_name = cls_node.name
    for m_node in ast.iter_child_nodes(cls_node):
        if not isinstance(m_node, ast.FunctionDef):
            continue
        ds = ast.get_docstring(m_node) or ''
        if '>>>' not in ds or 'hasattr' not in ds:
            continue
        key = (cls_name, m_node.name)
        if key not in UPGRADES:
            continue
        new_doctest = UPGRADES[key]
        if new_doctest is None:
            continue  # keep as-is

        # Find the hasattr doctest block in the source lines
        first_stmt = m_node.body[0]
        ds_start = first_stmt.lineno - 1
        ds_end = first_stmt.end_lineno - 1

        # Find the >>> hasattr line
        hasattr_line = None
        for k in range(ds_start, ds_end + 1):
            if b'>>> hasattr(' in lines[k] or b'>>> from PyICe' in lines[k]:
                hasattr_line = k
                break
        if hasattr_line is None:
            continue

        # Find block boundaries (blank line before, True/blank after)
        block_start = hasattr_line
        # Look backwards for import line
        if block_start > 0 and b'>>> from' in lines[block_start - 1]:
            block_start -= 1

        block_end = hasattr_line + 1
        if block_end <= ds_end and lines[block_end].strip() == b'True':
            block_end += 1

        # Include surrounding blank lines
        pre = block_start
        while pre > ds_start and lines[pre - 1].strip() == b'':
            pre -= 1
        pre = block_start  # keep one blank before

        post = block_end
        # skip one blank after
        if post <= ds_end and lines[post].strip() == b'':
            pass  # don't skip — we'll add our own

        # Determine indent from the hasattr line
        indent = lines[hasattr_line][:len(lines[hasattr_line]) - len(lines[hasattr_line].lstrip())]

        # Build new lines
        new_block = []
        for dl in new_doctest:
            new_block.append(indent + dl.encode())

        replacements.append((block_start, block_end, new_block))

# Apply replacements in reverse order
replacements.sort(key=lambda x: x[0], reverse=True)
for start, end, new_lines in replacements:
    lines[start:end] = new_lines

with open('PyICe/twi_interface.py', 'wb') as f:
    f.write(eol.join(lines))

print(f"Applied {len(replacements)} doctest upgrades")

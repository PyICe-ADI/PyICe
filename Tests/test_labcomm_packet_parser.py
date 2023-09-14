'''Tests for the LabComm packet parser.

Our starting point is the test cases Bobby used when developing the DC2038A Comm_GUI protocol. We have to adapt these cases to the LabComm protocol.

In the SVN DC2038A Rev 2443 comments, Bobby wrote the following test cases:

******************************************************************
b4,  56,  00,  02,  01,  02,  00,  02,  01,  02,  26,  9b, 
a1,  23,  00,  02,  01,  00,  0e,  04,  9c,  00,  02,  01,  02,  e3,  b7,  : CRC = e3b7, 
******************************************************************
Case BB001: Verify good packets can be received twice in a row.
b4,  56,  00,  02,  10,  02,  00,  02,  01,  02,  67,  98, 
a1,  23,  00,  02,  10,  00,  1d,  67,  20,  00,  02,  01,  02,  3a,  0d,  : CRC = 3a0d, 
******************************************************************
Case BB002: Verify aborted packet which results in one byte of Start of Command at the end does not prevent next good packet from being received.
b4,  56,  00,  02,  22,  02,  00,  02,  01,  02,  75,  b4,  56,  00,  02,  22,  02,  00,  02,  01,  02,  75,  9c, 
a1,  23,  00,  02,  22,  00,  2c,  bd,  e0,  00,  02,  01,  02,  b3,  73,  : CRC = b373, 
******************************************************************
Case BB003: Verify aborted packet which results in two bytes of Start of Command at the end does not prevent next good packet from being received.
b4,  56,  00,  02,  44,  02,  00,  03,  0a,  0b,  0c,  b4,  56,  00,  02,  44,  02,  00,  03,  0a,  0b,  0c,  04,  05, 
a1,  23,  00,  02,  44,  00,  3c,  14,  f8,  00,  02,  01,  02,  eb,  d9,  : CRC = ebd9, 
******************************************************************
Case BB004: Verify aborted packet which results in incomplete header at the end does not prevent next good packet from being received.
b4,  56,  00,  02,  00,  01,  00,  04,  aa,  bb,  cc,  dd, 
b4,  56,  00,  02,  00,  01,  00,  04,  aa,  bb,  cc,  dd,  b4,  56,  00,  02,  00,  01,  00,  04,  aa,  bb,  cc,  dd,  be,  f4, 
a1,  23,  00,  02,  00,  00,  4b,  68,  cc,  00,  02,  01,  02,  d7,  67,  : CRC = d767, 
******************************************************************
Case BB005: Verify aborted packet which results in complete header but incomplete data at the end does not prevent next good packet from being received.
b4,  56,  00,  02,  00,  01,  00,  04,  aa,  bb,  cc,  dd, 
b4,  56,  b4,  56,  00,  02,  00,  01,  00,  04,  aa,  bb,  cc,  dd,  be,  f4, 
a1,  23,  00,  02,  00,  00,  5a,  bc,  40,  00,  02,  01,  02,  1d,  65,  : CRC = 1d65, 
******************************************************************
Case BB006: Verify aborted packet which results in complete header and too much data at the end does not prevent next good packet from being received.
b4,  56,  00,  02,  00,  01,  00,  04,  aa,  bb,  cc,  dd, 
b4,  56,  00,  02,  00,  01,  b4,  56,  00,  02,  00,  01,  00,  04,  aa,  bb,  cc,  dd,  be,  f4,  b4,  56,  00,  02,  00,  01,  00,  04,  aa,  bb,  cc,  dd,  be,  f4, 
a1,  23,  00,  02,  00,  00,  6a,  35,  3c,  00,  02,  01,  02,  8d,  1b,  : CRC = 8d1b, 
a1,  23,  00,  02,  00,  00,  6a,  37,  d4,  00,  02,  01,  02,  78,  7a,  : CRC = 787a, 

And from Rev 2444, paraphrasing:

Case BB007: Tested with special FW that put Start-of-Packet extra bytes in front of each response and 2 extra garbage bytes at the end.

And from Rev 2451,

Case BB008: "the FW sends a bad Start of Response before every 10th good response, which results in a the timestamps as being interpretted as the number of bytes field.  Attached picture shows the GUI is correctly dropping 2 bytes every 10 responses."

'''

def infinite_bytestream(*bytes):
    '''Yield an infinite stream of bytes by
    infinitely looping through
    and returning each byte given as argument.
    For example:
        bstrm = infinite_bytestream(0x90, 0x0d, 0xf0, 0x0d)
        for b in bstrm:
            print " {:02x}".format(b),
            
    prints the following infinite sequence:
    
        90 0d f0 0d 90 0d f0 0d 90 0d f0 0d 90 0d f0 0d . . .'''
    for b in bytes:
        assert isinstance(b, int) and b >= 0 and b < 256
    while True:
        for b in bytes:
            yield b

import random, time
# random.seed(3141592653)
random.seed(time.time())
INITIAL_RNG_STATE = random.getstate()


def infinite_random_intstream(min_int, max_int):
    '''Create an infinite stream of random integers from min_int to max_int inclusive.
    Of course, if max_int < 256, the resulting stream can be considered a byte stream.'''
    assert isinstance(min_int, int) and min_int >= 0
    assert isinstance(max_int, int) and max_int > min_int
    while True:
        yield random.randint(min_int, max_int)
#
# A "chunk" is just a list or tuple of bytes.
# A "chunkstream" is a sequence of chunks.
#
def infinite_chunkstream(*bytelists):
    '''Given a set of byte lists, create an infinite stream
    that yields one byte list each time, in the order each list is
    given in the arguments.'''
    while True:
        for chunk in bytelists:
            yield chunk

def random_choice_chunkstream(*bytelists):
    '''Given a set of byte lists, create an infinite stream
    that yields one byte list each time, in random order.'''
    while True:
        yield bytelists[random.randint(0, len(bytelists)-1)]

def infinite_sequential_chunk_generator(start, step, stop=None):
    '''Generates a sequence of groups of bytes representing an ascending
    (or descending, for negative step values) sequence of integers
    encoded in as few bytes as possible, in big-endian format.

    For example, start=250, step=5 yields the following:

    >>> g = infinite_sequential_chunk_generator(250, 5)
    >>> for i in range(1,4+1):
            print i, " ".join("{:02x}".format(b) for b in g.next())
    1 fa
    2 ff
    3 01 04
    4 01 09
    '''
    import struct
    assert isinstance(start, int) and start > 0
    assert isinstance(step, int) and step > 0
    assert stop is None or (isinstance(stop, int) and stop >= start)
    i = start
    int_format = ("B", ">H", ">I", ">Q")
    fmt_ptr = 0
    while stop is None or i <= stop:
        fmt = int_format[fmt_ptr]
        result = bytearray(struct.calcsize(fmt))
        try:
            struct.pack_into(fmt, result, 0, i)
        except struct.error:
            if fmt_ptr == len(int_format) - 1:
                break  # while True: ...  We stop generating
                       # when struct doesn't know how to convert
                       # i to bytes anymore because i is too large.
            fmt_ptr = (fmt_ptr + 1) % len(int_format)
            continue
        yield result
        i += step

def infinite_random_chunkstream(max_size, min_size=0, max_int=255, min_int=0):
    for v in (min_int, max_int, min_size, max_size):
        assert isinstance(v, int) and v >= 0
    assert max_int >= min_int
    assert max_size >= min_size
    rnd_bstrm = infinite_random_intstream(min_int=min_int, max_int=max_int)
    size_strm = infinite_random_intstream(min_int=min_size, max_int=max_size)
    while True:
        yield get_this_many(howmany=next(size_strm),
                            stream=rnd_bstrm)

def chunkstream_to_bytestream(*chunkstreams):
    while True:
        for chunkstrm in chunkstreams:
            chunk = next(chunkstrm)
            for byte in chunk:
                yield byte
#
# Abstract stream utilities. These work on both bytestreams and chunkstreams.
#
def mux_streams(selection_sequence, *streams):
    '''Creates a stream that yields elements chosen from the argument streams per the given selection sequence.
    Given N argument streams, the selection sequence must be a sequence of integers 0 to N-1 that indicate
    which stream should the next element come from.
    If selection_sequence has finite length, it is repeated indefinitely.'''
    import collections
    assert isinstance(selection_sequence, collections.Iterable)
    while True:
        for select in selection_sequence:
            yield next(streams[select])

def get_this_many(howmany, stream):
    "Get exactly this many elements from the given stream."
    assert isinstance(howmany, int) and howmany >= 0
    i = howmany
    while i > 0:
        yield next(stream)
        i = i - 1
#
# LabComm packet constructor
#
from PyICe import labcomm
def chunkstream_to_labcomm_packet_stream(input_chnkstrm, src_id, dest_id):
    '''Given an input chunkstream, wrap each chunk as the payload of a LabComm packet
    and return the stream of these LabComm packets. Use the given source and destination IDs.'''
    for chunk in input_chnkstrm:
        pkt = labcomm.packet(src_id=src_id, dest_id=dest_id,
                             length=len(chunk), data=chunk, crc=None)
        print("[Created {}]".format(pkt))
        yield pkt.to_byte_array()

if __name__=='__main__':
    MY_ID = 0xabcd
    from PyICe.lab_utils import print_hex_bytes
    #
    # Create a stream of valid LabComm packets (pkt_strm) that we'll expect the
    # parser to receive properly.
    #
    START = 65500
    NUMBER_OF_INTENTIONAL_PACKETS = 100
    STEP = 7
    payload_strm = infinite_sequential_chunk_generator(start=START, step=STEP, stop=START+STEP*(NUMBER_OF_INTENTIONAL_PACKETS-1))
    pkt_strm = chunkstream_to_labcomm_packet_stream(input_chnkstrm=payload_strm,
                                                    src_id=0x0020, dest_id=MY_ID)
    #
    # Create a stream of distractors consisting of start-of-packet (SOP) marks.
    #
    sop_strm = random_choice_chunkstream([0x4c, 0x54],
                                         [0x4c, 0x54, 0x4c, 0x54],
                                         [0x4c, 0x54, 0x4c, 0x54, 0x4c, 0x54],
                                         [0x4c, 0x54, 0x4c, 0x54, 0x4c, 0x54, 0xff, 0xff],
                                         [0x4c, 0x4c, 0x4c, 0x4c, 0x54, 0x4c, 0x4c, 0x4c])
    #
    # Create a stream of distractors made of random quantities of random bytes.
    #
    rndburst_strm = infinite_random_chunkstream(max_size=128)
    #
    # Randomly mux the packet stream with the distractors, so we'll get a random chunkstream like this:
    # [valid packet][random bytes][SOP][SOP][valid packet][SOP][random bytes][random_bytes][valid packet]......
    #
    # where [SOP] and [random bytes] are distractors.
    #
    streamlist = [pkt_strm, sop_strm, rndburst_strm]
    sel_strm = infinite_random_intstream(min_int=0, max_int=len(streamlist)-1)
    pkts_and_distractors_strm = mux_streams(sel_strm, *streamlist)
    #
    # Serialize the mixed stream into bytes.
    #
    bstrm = chunkstream_to_bytestream(pkts_and_distractors_strm)
    #
    # Print a sample of pkts_and_distractors_strm and bstrm, for understanding
    # and debug purposes.
    #
    # num_sample_chunks = 10
    # print ("Here are {} sample chunks from "
    #        "the pkts_and_distractors generator:").format(num_sample_chunks)
    # for i in range(num_sample_chunks):
    #     print_hex_bytes(pkts_and_distractors_strm.next(),
    #                     number_of_bytes_per_line=8,
    #                     prefix="  ", show_offsets=True)
    #     print
    # print
    # print "=" * 78
    # print "A 30-byte sample of the chunkstream serialized as a bytestream:"
    # print
    # for i in range(30):
    #     print_hex_bytes(get_this_many(16, bstrm), None, None)
    print("=" * 78)
    from PyICe import lab_core, lab_interfaces
    print("Instantiate a PyICe master and create a hardware-free serial test-harness interface.")
    m = lab_core.master()
    #
    # Have the serial harness fetch bytes from the mixed bytestream created above.
    #
    test_ser = m.get_interface_test_harness_serial(serial_port_name="TEST_PORT_1", bytestream=bstrm,
                                                   max_bytes_returned_per_read=32)
    # num_reads = 5
    # read_size = 20
    # print ("Reading {} times from serial harness, "
           # "asking for {} bytes each time:").format(num_reads, read_size)
    # for i in xrange(num_reads):
        # bytes_read = test_ser.read(read_size)
        # # print ("test_ser({})-> {:3d} bytes: {}"
               # # ).format(read_size, len(bytes_read),
                        # # " ".join("{:02x}".format(b) for b in bytes_read))
        # print_hex_bytes(bytes_read, number_of_bytes_per_line=None,
                        # prefix=("test_ser({})-> {:3d} bytes: "
                                # ).format(read_size, len(bytes_read)))
    print("Successfully created the serial harness.")
    print("=" * 78)
    def print_junk_bytes(junk_bytes):
        print_hex_bytes(the_bytes=junk_bytes, prefix="JUNKED bytes ", show_offsets=True)
    lc_intf = lab_interfaces.interface_labcomm_raw_serial(raw_serial_interface=test_ser, 
                                                          junk_bytes_dump=print_junk_bytes,
                                                          debug=True)
    print("Created a LabComm interface that reads bytes from the serial harness.")
    num_recv_calls = 500
    print("Attempt to call recv_packet() {} times:".format(num_recv_calls))
    print()
    for i in range(num_recv_calls):
        pkt = lc_intf.recv_packet(dest_id=MY_ID, timeout=0.2)
        print("{:>4d}: {}".format(i+1, pkt))

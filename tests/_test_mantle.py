import fault
from bit_vector import BitVector
from abc import ABC, abstractmethod
import magma as m
m.set_mantle_target("coreir")
import mantle  # nopep8


def ref_add(I0, I1, width):
    return I0 + I1


# def test_add_random(I0 : fault.Random(BitVector(width)),
#                     I1 : fault.Random(BitVector(width))):
width = 16


@fault.test_case(combinational=True, num_tests=1)
def test_add_random(Add: mantle.DefineAdd(width),
                    I0: fault.Random(width),
                    I1: fault.Random(width)):
    # Add = mantle.DefineAdd(16)
    #
    # Add.I0 = fault.Random(width=16)
    # Add.I1 = fault.Random(width=16)
    Add.I0 = I0
    Add.I1 = I1

    Add.eval()

    assert Add.O == ref_add(I0, I1, width)
    # assert Add.O == BitVector(Add.I0, 16) + BitVector(Add.I1, 16)


class TFF(m.Circuit):
    name = "TFF"
    IO = ["O", m.Out(m.Bit)] + m.ClockInterface()

    @classmethod
    def definition(cls):
        # instance a dff to hold the state of the toggle flip-flop - this needs
        # to be done first
        ff = mantle.DFF()

        # compute the next state as the not of the old state ff.O
        ff(~ff.O)
        m.wire(ff.O, cls.O)


@fault.test_case
def test_tff(TFF: TFF):
    TFF.eval()
    for i in range(0, 8):
        assert TFF.O == i % 2
        TFF.next()


def check_memory_address(memory, addr, expected):
    memory.RADDR = addr
    memory.advance(2)
    assert memory.RDATA == expected


@fault.test_case
def test_RAM(RAM: mantle.coreir.memory.DefineRAM(height=4, width=4)):
    expected = {}
    for i in range(4):
        addr = BitVector(i, 2)
        data = fault.Random(width=4)
        expected[addr.as_int()] = data
        RAM.WDATA = data
        RAM.WADDR = addr
        RAM.WE = 1
        RAM.next()
        RAM.WE = 0

        # check_memory_address(RAM, addr, data)
        RAM.RADDR = addr
        RAM.next()
        assert RAM.RDATA == data, dict(iter=i, rdata=RAM.RDATA, data=data)

    for addr, data in expected.items():
        # check_RAM(RAM, addr, data)
        RAM.RADDR = BitVector(addr, 2)
        RAM.next()
        assert RAM.RDATA == data, dict(iter=addr, rdata=RAM.RDATA, data=data)


class Memory(ABC):
    @abstractmethod
    def read(self, addr):
        raise NotImplementedError()

    @abstractmethod
    def write(self, addr, data):
        raise NotImplementedError()

class RAMModel(Memory):
    def __init__(self, height, width):
        self.mem = [BitVector(width) for _ in range(height)]

    def read(self, addr):
        return self.mem[addr]

    def write(self, addr, data):
        self.mem[addr] = data


class RAM(Memory):
    def __init__(self, ram):
        self.ram = ram

    def read(self, addr):
        self.ram.RADDR = addr
        self.next()
        return self.ram.RDATA

    def write(self, addr, data):
        RAM.WDATA = data
        RAM.WADDR = addr
        RAM.WE = 1
        RAM.next()
        RAM.WE = 0


# @fault.test_case
# def test_RAM_raw(
#         ram : RAM(mantle.coreir.memory.DefineRAM(height=4, width=4)),
#         ram_model : RAMModel(4, 4), addr : fault.Random(2),
#         data : fault.Random(4)):
#     ram_model.write(addr, data)
#     ram.write(addr, data)
#     assert ram.read(addr) == ram_model.read(addr) == data
#
# @fault.test_case
# def test_RAM_raw_x2(
#         ram : RAM(mantle.coreir.memory.DefineRAM(height=4, width=4)),
#         ram_model : RAMModel(4, 4),
#         addr : fault.Random(2),
#         data0 : fault.Random(4),
#         data1 : fault.Random(4)):
#     ram_model.write(addr, data0)
#     ram.write(addr, data0)
#     ram_model.write(addr, data1)
#     ram.write(addr, data1)
#     assert ram.read(addr) == ram_model.read(addr) == data1
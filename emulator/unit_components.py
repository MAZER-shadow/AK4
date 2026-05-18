import unittest

from cpu.components import DataBus, MemoryUnit, Register, MultiPlex, ALU, SimpleAction, BiAction, VectorStateLogic
from cpu.modules import ExternalDevice1, ExternalDevice2
from cpu.utils import SharedMemory


class MemoryUnitTestCase(unittest.TestCase):
    def setUp(self):
        b_ar = DataBus(4)
        b_mem_out = DataBus(4)
        b_data_op = DataBus(1)
        b_alu_out = DataBus(4)
        mem = SharedMemory()
        self.data_memory_unit = MemoryUnit(b_data_op, b_ar, b_alu_out, b_mem_out, mem)
        l_ctrl = self.data_memory_unit.get_control_latch()
        self.exec = l_ctrl.perform
        self.perf = lambda: b_mem_out.get_data()
        self.addr = (0).to_bytes(4)
        self.inp = (0).to_bytes(4)
        self.op = (0).to_bytes(1)
        b_ar.bind_provider(lambda: self.addr)
        b_alu_out.bind_provider(lambda: self.inp)
        b_data_op.bind_provider(lambda: self.op)


    def test_rw(self):
        self.addr = (215).to_bytes(4)
        self.op = (1).to_bytes(1)
        self.inp = (1023).to_bytes(4)
        self.exec()
        self.op = (0).to_bytes(1)
        self.exec()
        self.assertEqual(1023, int.from_bytes(self.perf()))
        self.addr = (216).to_bytes(4)
        self.exec()
        self.assertEqual( 261888, int.from_bytes(self.perf()))

    def test_zero(self):
        self.exec()
        self.assertEqual(0, int.from_bytes(self.perf()))

    def ioSetUp(self):
        self.ex1 = ExternalDevice1(self.data_memory_unit.get_input_latch())
        self.ex2 = ExternalDevice2()
        self.data_memory_unit.bind_input_io(self.ex1.b_io_d_1, self.ex1.b_io_r_1)
        self.data_memory_unit.bind_output_io(self.ex2.b_io_d_2, self.ex2.b_io_r_2, self.ex2.l_io_out)
        self.b_int_allow = DataBus(1)
        self.b_int_got = DataBus(1)
        self.data_memory_unit.bind_int_buses(self.b_int_got, self.b_int_allow)

    def test_output_to_io(self):
        self.ioSetUp()
        self.addr = (0x0001).to_bytes(4)
        self.op = (0b11).to_bytes(1)
        self.inp = (1023).to_bytes(4)
        self.exec()
        self.assertEqual(1023, int.from_bytes(self.ex2.cu.get_data(), signed=True))

    def test_output_to_io_massive(self):
        self.ioSetUp()
        self.addr = (0x0001).to_bytes(4)
        self.op = (0b11).to_bytes(1)
        self.inp = (-5646854).to_bytes(4, signed=True)
        self.exec()
        self.assertEqual(-5646854, int.from_bytes(self.ex2.cu.get_data(), signed=True))
        self.inp = (123).to_bytes(4, signed=True)
        self.exec()
        self.inp = (486865).to_bytes(4, signed=True)
        self.exec()
        self.assertEqual(123, int.from_bytes(self.ex2.cu.get_data(), signed=True))
        self.assertEqual(486865, int.from_bytes(self.ex2.cu.get_data(), signed=True))
        self.assertEqual(None, self.ex2.cu.get_data())

    def test_input_from_io(self):
        self.ioSetUp()
        self.b_int_allow.bind_provider(lambda: (1^int.from_bytes(self.b_int_got.get_data())).to_bytes(1))
        self.addr = (0x0000).to_bytes(4)
        self.op = (0b10).to_bytes(1)
        self.ex1.cu.post_data()
        self.ex1.cu.post_data()
        self.ex1.cu.post_data()
        self.assertEqual(0, int.from_bytes(self.b_int_got.get_data(), signed=True))
        self.ex1.cu.post_data((486865).to_bytes(4, signed=True))
        self.assertEqual(1, int.from_bytes(self.b_int_got.get_data(), signed=True))
        self.ex1.cu.post_data((-89952).to_bytes(4, signed=True))
        self.assertEqual(1, int.from_bytes(self.b_int_got.get_data(), signed=True))
        self.exec()
        self.assertEqual( 486865, int.from_bytes(self.perf(), signed=True))
        self.assertEqual(0, int.from_bytes(self.b_int_got.get_data(), signed=True))
        self.ex1.cu.post_data()
        self.ex1.cu.post_data()
        self.ex1.cu.post_data()
        self.assertEqual(1, int.from_bytes(self.b_int_got.get_data(), signed=True))
        self.exec()
        self.assertEqual(-89952, int.from_bytes(self.perf(), signed=True))
        self.assertEqual(0, int.from_bytes(self.b_int_got.get_data(), signed=True))
        self.ex1.cu.post_data()
        self.ex1.cu.post_data()
        self.ex1.cu.post_data()
        self.assertEqual(0, int.from_bytes(self.b_int_got.get_data(), signed=True))

    def test_full_io(self):
        self.ioSetUp()
        self.b_int_allow.bind_provider(lambda: (1 ^ int.from_bytes(self.b_int_got.get_data())).to_bytes(1))
        self.addr = (0x0000).to_bytes(4)
        self.op = (0b10).to_bytes(1)
        self.ex1.cu.post_data((682394678).to_bytes(4, signed=True))
        self.assertEqual(1, int.from_bytes(self.b_int_got.get_data(), signed=True))
        self.exec()
        self.inp = self.perf()
        self.assertEqual(0, int.from_bytes(self.b_int_got.get_data(), signed=True))
        self.addr = (0x0001).to_bytes(4)
        self.op = (0b11).to_bytes(1)
        self.exec()
        self.assertEqual(682394678, int.from_bytes(self.ex2.cu.get_data(), signed=True))


class RegisterTestCase(unittest.TestCase):
    def setUp(self):
        b_alu_out = DataBus(4)
        b_alu_ac = DataBus(4)
        ac = Register(b_alu_out, b_alu_ac,4)
        l_ctrl = ac.get_control_latch()
        self.exec = l_ctrl.perform
        self.inp = (0).to_bytes(4)
        b_alu_out.bind_provider(lambda: self.inp)
        self.perf = lambda: b_alu_ac.get_data()

    def test_rw(self):
        self.inp = (-8956432).to_bytes(4,signed = True)
        self.exec()
        self.assertEqual(-8956432, int.from_bytes(self.perf(), signed=True))

    def test_zero(self):
        self.exec()
        self.assertEqual(0, int.from_bytes(self.perf(), signed=True))

class MultiPlexTestCase(unittest.TestCase):
    def setUp(self):
        b_alu_choice = DataBus(2)
        b_alu_inp2 = DataBus(4)
        b_ar = DataBus(4)
        b_mem_out = DataBus(4)
        b_cr_arg = DataBus(4)
        mx = MultiPlex(b_alu_choice, b_alu_inp2, 4)
        self.inp1 = (125).to_bytes(4,signed = True)
        self.inp2 = (-125).to_bytes(4,signed = True)
        self.inp3 = (145656).to_bytes(4,signed = True)
        self.choice = (0).to_bytes(2)
        self.perf = b_alu_inp2.get_data
        b_ar.bind_provider(lambda: self.inp1)
        b_mem_out.bind_provider(lambda: self.inp2)
        b_cr_arg.bind_provider(lambda: self.inp3)
        b_alu_choice.bind_provider(lambda: self.choice)
        mx.bind_inp(0, b_ar)
        mx.bind_inp(1, b_mem_out)
        mx.bind_inp(2, b_cr_arg)

    def test_choice0(self):
        self.choice = (0).to_bytes(2)
        self.assertEqual(125, int.from_bytes(self.perf(), signed=True))

    def test_choice1(self):
        self.choice = (1).to_bytes(2)
        self.assertEqual(-125, int.from_bytes(self.perf(),signed=True))

    def test_choice2(self):
        self.choice = (2).to_bytes(2)
        self.assertEqual(145656, int.from_bytes(self.perf(), signed=True))

    def test_change(self):
        self.inp1 = (5).to_bytes(4,signed = True)
        self.inp2 = (9).to_bytes(4,signed = True)
        self.choice = (0).to_bytes(2)
        self.assertEqual(5, int.from_bytes(self.perf(), signed=True))
        self.choice = (1).to_bytes(2)
        self.assertEqual(9, int.from_bytes(self.perf(), signed=True))

class ALUTestCase(unittest.TestCase):

    def setUp(self):
        b_alu_ac = DataBus(4)
        b_alu_inp2 = DataBus(4)
        b_alu_op = DataBus(1)
        b_alu_flag = DataBus(1)
        b_alu_out = DataBus(4)
        ALU(b_alu_op, b_alu_ac, b_alu_inp2, b_alu_flag, b_alu_out)
        self.inp1 = (1025).to_bytes(4,signed = True)
        self.inp2 = (-333).to_bytes(4, signed=True)
        self.op = (0b00000000).to_bytes(4, signed=True)
        b_alu_ac.bind_provider(lambda: self.inp1)
        b_alu_inp2.bind_provider(lambda: self.inp2)
        b_alu_op.bind_provider(lambda: self.op)
        self.perf = lambda: (int.from_bytes(b_alu_out.get_data(), signed=True), int.from_bytes(b_alu_flag.get_data()))

    def test_add(self):
        self.inp1 = (5).to_bytes(4,signed = True)
        self.inp2 = (-2).to_bytes(4,signed = True)
        self.op = (0b00000000).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b1000, res[1])
        self.assertEqual(3, res[0])

    def test_add_neg(self):
        self.inp1 = (5).to_bytes(4, signed=True)
        self.inp2 = (36).to_bytes(4, signed=True)
        self.op = (0b11000000).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0010, res[1])
        self.assertEqual(-41, res[0])

    def test_add_over(self):
        self.inp1 = (2147483647).to_bytes(4, signed=True)
        self.inp2 = (2).to_bytes(4, signed=True)
        self.op = (0b00000000).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0110, res[1])
        self.assertEqual(-2147483647, res[0])

    def test_sub(self):
        self.inp1 = (-1).to_bytes(4, signed=True)
        self.inp2 = (50).to_bytes(4, signed=True)
        self.op = (0b00000001).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b1010, res[1])
        self.assertEqual(-51, res[0])

    def test_sub_zero(self):
        self.inp1 = (-1).to_bytes(4, signed=True)
        self.inp2 = (-1).to_bytes(4, signed=True)
        self.op = (0b00000001).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b1001, res[1])
        self.assertEqual(0, res[0])

    def test_mul(self):
        self.inp1 = (32543).to_bytes(4, signed=True)
        self.inp2 = (567).to_bytes(4, signed=True)
        self.op = (0b00000101).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0000, res[1])
        self.assertEqual(18451881, res[0])

    def test_mul_over(self):
        self.inp1 = (32543).to_bytes(4, signed=True)
        self.inp2 = (567000).to_bytes(4, signed=True)
        self.op = (0b00000101).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0100, res[1])
        self.assertEqual(1272011816, res[0])

    def test_rem(self):
        self.inp1 = (151515).to_bytes(4, signed=True)
        self.inp2 = (23).to_bytes(4, signed=True)
        self.op = (0b00000110).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0000, res[1])
        self.assertEqual(14, res[0])

    def test_div(self):
        self.inp1 = (151515).to_bytes(4, signed=True)
        self.inp2 = (23).to_bytes(4, signed=True)
        self.op = (0b00000100).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0000, res[1])
        self.assertEqual(6587, res[0])

    def test_div_neg_vals(self):
        self.inp1 = (-151515).to_bytes(4, signed=True)
        self.inp2 = (-24).to_bytes(4, signed=True)
        self.op = (0b00000100).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0000, res[1])
        self.assertEqual(6313, res[0])

    def test_left(self):
        self.inp1 = (-151515).to_bytes(4, signed=True)
        self.inp2 = (-24).to_bytes(4, signed=True)
        self.op = (0b00000111).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0010, res[1])
        self.assertEqual(-151515, res[0])

    def test_right(self):
        self.inp1 = (-151515).to_bytes(4, signed=True)
        self.inp2 = (-24).to_bytes(4, signed=True)
        self.op = (0b00001000).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0010, res[1])
        self.assertEqual(-24, res[0])

    def test_right_flags(self):
        self.inp1 = (-151515).to_bytes(4, signed=True)
        self.inp2 = (-24).to_bytes(4, signed=True)
        self.op = (0b11101000).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0000, res[1])
        self.assertEqual(23, res[0])

    def test_shift_l_simple(self):
        self.inp1 = (2).to_bytes(4, signed=True)
        self.inp2 = (2).to_bytes(4, signed=True)
        self.op = (0b00000010).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0000, res[1])
        self.assertEqual(8, res[0])


    def test_shift_l_neg(self):
        self.inp1 = (-18).to_bytes(4, signed=True)
        self.inp2 = (5).to_bytes(4, signed=True)
        self.op = (0b00000010).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b1010, res[1])
        self.assertEqual(-576, res[0])

    def test_shift_r_simple(self):
        self.inp1 = (128).to_bytes(4, signed=True)
        self.inp2 = (5).to_bytes(4, signed=True)
        self.op = (0b00000011).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0000, res[1])
        self.assertEqual(4, res[0])

    def test_shift_r_neg(self):
        self.inp1 = (-100).to_bytes(4, signed=True)
        self.inp2 = (5).to_bytes(4, signed=True)
        self.op = (0b00000011).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0010, res[1])
        self.assertEqual(-4, res[0])

    def test_and(self):
        self.inp1 = (-1895).to_bytes(4, signed=True)
        self.inp2 = (41535).to_bytes(4, signed=True)
        self.op = (0b00001001).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0000, res[1])
        self.assertEqual(40985, res[0])

    def test_or(self):
        self.inp1 = (-1895).to_bytes(4, signed=True)
        self.inp2 = (41535).to_bytes(4, signed=True)
        self.op = (0b00001010).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0010, res[1])
        self.assertEqual(-1345, res[0])

    def test_xor(self):
        self.inp1 = (-1895).to_bytes(4, signed=True)
        self.inp2 = (41535).to_bytes(4, signed=True)
        self.op = (0b00001011).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0010, res[1])
        self.assertEqual(-42330, res[0])

    def test_inc4(self):
        self.inp1 = (-1895).to_bytes(4, signed=True)
        self.inp2 = (41535).to_bytes(4, signed=True)
        self.op = (0b00001100).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0010, res[1])
        self.assertEqual(-1891, res[0])

    def test_dec4(self):
        self.inp1 = (-1895).to_bytes(4, signed=True)
        self.inp2 = (41535).to_bytes(4, signed=True)
        self.op = (0b00001101).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0010, res[1])
        self.assertEqual(-1899, res[0])

    def test_inc4_r(self):
        self.inp1 = (-1895).to_bytes(4, signed=True)
        self.inp2 = (41535).to_bytes(4, signed=True)
        self.op = (0b00001110).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0000, res[1])
        self.assertEqual(41539, res[0])

    def test_dec4_r(self):
        self.inp1 = (-1895).to_bytes(4, signed=True)
        self.inp2 = (41535).to_bytes(4, signed=True)
        self.op = (0b00001111).to_bytes(1)
        res = self.perf()
        self.assertEqual(0b0000, res[1])
        self.assertEqual(41531, res[0])


class SimpleActionTestCase(unittest.TestCase):
    def setUp(self):
        self.inp = (0).to_bytes(4, signed=True)
        self.bus_in = DataBus(4)
        self.bus_out = DataBus(4)
        self.bus_in.bind_provider(lambda: self.inp)

    def testInc(self):
        sa = SimpleAction(self.bus_in, self.bus_out, lambda x: (int.from_bytes(x, signed=True)+1).to_bytes(4, signed=True))
        self.inp = (55).to_bytes(4, signed=True)
        self.assertEqual(56, int.from_bytes(self.bus_out.get_data(), signed=True))
        self.inp = (-33).to_bytes(4, signed=True)
        self.assertEqual(-32, int.from_bytes(self.bus_out.get_data(), signed=True))

class BiActionTestCase(unittest.TestCase):
    def setUp(self):
        self.inp1 = (0).to_bytes(4, signed=True)
        self.inp2 = (0).to_bytes(4, signed=True)
        self.bus_in1 = DataBus(4)
        self.bus_in2 = DataBus(4)
        self.bus_out = DataBus(4)
        self.bus_in1.bind_provider(lambda: self.inp1)
        self.bus_in2.bind_provider(lambda: self.inp2)

    def testSum(self):
        ba = BiAction(self.bus_in1, self.bus_in2, self.bus_out, lambda x, y: (int.from_bytes(x, signed=True)+int.from_bytes(y, signed=True)).to_bytes(4, signed=True))
        self.inp1 = (55).to_bytes(4, signed=True)
        self.inp2 = (45456).to_bytes(4, signed=True)
        self.assertEqual(45511, int.from_bytes(self.bus_out.get_data(), signed=True))
        self.inp1 = (-33).to_bytes(4, signed=True)
        self.inp2 = (362).to_bytes(4, signed=True)
        self.assertEqual(329, int.from_bytes(self.bus_out.get_data(), signed=True))

class VectorStateLogicTestCase(unittest.TestCase):
    def setUp(self):
        self.inp = (0).to_bytes(4)
        self.b_in = DataBus(4)
        self.b_in.bind_provider(lambda: self.inp)
        self.b_out = DataBus(1)
        self.state_logic = VectorStateLogic(self.b_in, self.b_out)

    def test_simple(self):
        self.inp = (0x00000000).to_bytes(4)
        self.assertEqual("00", self.b_out.get_data().hex())
        self.inp = (0x00000001).to_bytes(4)
        self.assertEqual("01", self.b_out.get_data().hex())
        self.inp = (0x00000080).to_bytes(4)
        self.assertEqual("03", self.b_out.get_data().hex())
        self.inp = (0x80000000).to_bytes(4)
        self.assertEqual("09", self.b_out.get_data().hex())

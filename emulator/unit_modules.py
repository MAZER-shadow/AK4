import unittest

from cpu.modules import ExternalDevice1, ExternalDevice2, MainDataPath, MainControlUnit, VectorExecModule
from cpu.utils import SharedMemory
from cpu.components import DataBus, Register
from cpu.modules import ExtensionModule


class IODevicesTestCase(unittest.TestCase):
    def setUp(self):
        self.device_out = ExternalDevice2()
        self.device_in = ExternalDevice1(self.device_out.l_io_out)
        self.device_in.b_io_r_1.bind_provider(self.device_out.b_io_r_2.get_data)
        self.device_out.b_io_d_2.bind_provider(self.device_in.b_io_d_1.get_data)

    def test_simple_io(self):
        self.device_in.cu.post_data((123).to_bytes(4))
        self.assertEqual(123,int.from_bytes(self.device_out.cu.get_data()))

    def test_three_values_io(self):
        self.device_in.cu.post_data((-123).to_bytes(4, signed=True))
        self.assertEqual(-123, int.from_bytes(self.device_out.cu.get_data(), signed=True))
        self.device_in.cu.post_data((145654234).to_bytes(4))
        self.assertEqual(145654234, int.from_bytes(self.device_out.cu.get_data()))
        self.device_in.cu.post_data((0).to_bytes(4))
        self.assertEqual(0, int.from_bytes(self.device_out.cu.get_data()))

    def test_unbind_and_wait(self):
        self.device_in.b_io_r_1.unbind_provider()
        self.device_in.b_io_r_1.bind_provider(lambda: (0).to_bytes(1))
        self.device_in.cu.post_data((11).to_bytes(4, signed=True))
        self.assertEqual(None, self.device_out.cu.get_data())
        self.device_in.cu.post_data((34214).to_bytes(4, signed=True))
        self.assertEqual(None, self.device_out.cu.get_data())
        self.device_in.cu.post_data((8990).to_bytes(4, signed=True))
        self.assertEqual(None, self.device_out.cu.get_data())
        self.device_in.b_io_r_1.unbind_provider()
        self.device_in.b_io_r_1.bind_provider(lambda: (1).to_bytes(1))
        self.device_in.cu.post_data()
        self.device_in.cu.post_data()
        self.assertEqual(11, int.from_bytes(self.device_out.cu.get_data(), signed=True))
        self.assertEqual(34214, int.from_bytes(self.device_out.cu.get_data(), signed=True))
        self.assertEqual(None, self.device_out.cu.get_data())
        self.device_in.cu.post_data()
        self.assertEqual(8990, int.from_bytes(self.device_out.cu.get_data(), signed=True))
        self.assertEqual(None, self.device_out.cu.get_data())
        self.device_in.cu.post_data()
        self.assertEqual(None, self.device_out.cu.get_data())

class MainDataPathTestCase(unittest.TestCase):
    def setUp(self):
        self.mem = SharedMemory()
        self.dp = MainDataPath(self.mem)

        self.b_alu_op = (0).to_bytes(1, signed=False)
        self.b_cr_arg = (0).to_bytes(4, signed=True)
        self.b_data_op = (0).to_bytes(1, signed=False)
        self.b_alu_choice = (0).to_bytes(1, signed=False)
        self.latch_ac = self.dp.l_ac.perform
        self.latch_ar = self.dp.l_ar.perform
        self.latch_data = self.dp.l_data.perform

        self.dp.b_alu_op.bind_provider(lambda: self.b_alu_op)
        self.dp.b_cr_arg.bind_provider(lambda: self.b_cr_arg)
        self.dp.b_data_op.bind_provider(lambda: self.b_data_op)
        self.dp.b_alu_choice.bind_provider(lambda: self.b_alu_choice)


    def test_inc(self):
        self.b_alu_op = (8).to_bytes(1, signed=False)
        self.b_cr_arg = (4567829).to_bytes(4, signed=True)
        self.b_alu_choice = (0).to_bytes(1, signed=False)
        self.latch_ac()
        self.assertEqual(4567829, int.from_bytes(self.dp.b_alu_ac.get_data(), signed=True))

        self.b_alu_op = (12).to_bytes(1, signed=False)
        self.latch_ac()
        self.assertEqual(4567833, int.from_bytes(self.dp.b_alu_ac.get_data(), signed=True))

        self.b_alu_op = (8).to_bytes(1, signed=False)
        self.b_cr_arg = (0x0001).to_bytes(4, signed=True)
        self.b_alu_choice = (0).to_bytes(1, signed=False)
        self.latch_ar()
        self.assertEqual(0x0001, int.from_bytes(self.dp.b_ar.get_data(), signed=False))

        self.b_alu_op = (7).to_bytes(1, signed=False)
        self.b_data_op = (0b11).to_bytes(1, signed=False)
        self.latch_data()
        self.assertEqual(4567833, int.from_bytes(self.dp.ex2.cu.get_data(), signed=True))

        self.b_alu_op = (0b00100111).to_bytes(1, signed=False)
        self.latch_ac()
        self.assertEqual(4567834, int.from_bytes(self.dp.b_alu_ac.get_data(), signed=True))

        self.b_alu_op = (7).to_bytes(1, signed=False)
        self.b_data_op = (0b11).to_bytes(1, signed=False)
        self.latch_data()
        self.assertEqual(4567834, int.from_bytes(self.dp.ex2.cu.get_data(), signed=True))

    def load_mem_cr_addr(self, addr: int):
        self.b_alu_op = (8).to_bytes(1, signed=False)
        self.b_cr_arg = addr.to_bytes(4, signed=True)
        self.b_alu_choice = (0).to_bytes(1, signed=False)
        self.latch_ar()
        self.b_data_op = (0).to_bytes(1, signed=False)
        self.latch_data()

    def test_store_plus(self):
        self.mem.arr[0x0050:0x0054] = (0x00000060).to_bytes(4, signed=True)
        self.dp.b_int_allow.bind_provider(lambda: (1 ^ int.from_bytes(self.dp.b_int_got.get_data())).to_bytes(1))
        self.dp.ex1.cu.post_data((4686).to_bytes(4, signed=True))
        self.dp.ex1.cu.post_data((-785432).to_bytes(4, signed=True))

        self.load_mem_cr_addr(0x0000)
        # read from input port (port-mode read: b_data_op = 0b10)
        self.b_data_op = (0b10).to_bytes(1, signed=False)
        self.latch_data()
        self.b_alu_op = (8).to_bytes(1, signed=False)
        self.b_alu_choice = (1).to_bytes(1, signed=False)
        self.latch_ac()
        self.assertEqual(4686, int.from_bytes(self.dp.b_alu_ac.get_data(), signed=True))

        self.load_mem_cr_addr(0x0050)

        self.b_alu_op = (8).to_bytes(1, signed=False)
        self.b_alu_choice = (1).to_bytes(1, signed=False)
        self.latch_ar()
        self.assertEqual(0x0060, int.from_bytes(self.dp.b_ar.get_data(), signed=True))

        self.b_alu_op = (7).to_bytes(1, signed=False)
        self.b_data_op = (1).to_bytes(1, signed=False)
        self.latch_data()
        self.assertEqual(4686, int.from_bytes(self.mem.arr[0x0060:0x0064] , signed=True))

        self.load_mem_cr_addr(0x0050)

        self.b_alu_op = (14).to_bytes(1, signed=False)
        self.b_alu_choice = (1).to_bytes(1, signed=False)
        self.b_data_op = (1).to_bytes(1, signed=False)
        self.latch_data()
        self.assertEqual(0x0064, int.from_bytes(self.mem.arr[0x0050:0x0054], signed=True))

class MainControlUnitTestCase(unittest.TestCase):
    def setUp(self):
        self.mem = SharedMemory()
        self.dp = MainDataPath(self.mem)
        self.vex = ExtensionModule(self.mem,self.dp.b_cr_arg)
        self.cmem = SharedMemory()
        self.cu = MainControlUnit(self.dp, self.vex, self.cmem)

    def doTick(self):
        if self.cu.id.stop:
            return
        self.cu.id.tick()
        print(f"ac: {self.dp.b_alu_ac.get_data().hex()} ar: {self.dp.b_ar.get_data().hex()} pc: {self.cu.b_pc.get_data().hex()} cr: {self.cu.b_cmd.get_data().hex()}")

    def test_simple(self):
        self.cmem.arr[0:5] = [0x40, 0x11, 0x22, 0x33, 0x44]
        self.cmem.arr[5:6] = [0x01]
        self.doTick()
        self.doTick()
        self.doTick()
        self.doTick()
        self.doTick()
        self.doTick()
        self.assertEqual("11223345",self.dp.b_alu_ac.get_data().hex())

    def test_mem(self):
        self.cmem.arr[0:5] = [0x40, 0x11, 0x22, 0x33, 0x44]
        self.cmem.arr[5:6] = [0x01]
        self.cmem.arr[6:11] = [0x6B, 0x00, 0x00, 0x00, 0x10]
        self.cmem.arr[11:16] = [0x40, 0x00, 0x00, 0x00, 0x00]
        self.cmem.arr[16:21] = [0x60, 0x00, 0x00, 0x00, 0x10]
        for i in range(16):
            self.doTick()
        self.assertEqual("11223345",self.dp.b_alu_ac.get_data().hex())

    def test_cycle(self):
        self.cmem.arr[0:5] =   [0x40, 0x00, 0x00, 0x00, 0x0A] #LD 10
        self.cmem.arr[5:10] =  [0x6B, 0x00, 0x00, 0x00, 0x10] #ST 0x10
        self.cmem.arr[10:15] = [0x40, 0x00, 0x00, 0x04, 0x00] #LD 1024
        self.cmem.arr[15:20] = [0x6B, 0x00, 0x00, 0x00, 0x30] #ST 0x30
        self.cmem.arr[20:25] = [0x60, 0x00, 0x00, 0x00, 0x30] #LD 0x30
        self.cmem.arr[25:30] = [0x42, 0x00, 0x00, 0x00, 0x7D] #SUB 125
        self.cmem.arr[30:35] = [0x6B, 0x00, 0x00, 0x00, 0x30] #ST 0x30
        self.cmem.arr[35:40] = [0x60, 0x00, 0x00, 0x00, 0x10] #LD 0x10
        self.cmem.arr[40:41] = [0x02]                         #DEC
        self.cmem.arr[41:46] = [0x6B, 0x00, 0x00, 0x00, 0x10] #ST 0x10
        self.cmem.arr[46:51] = [0x4D, 0x00, 0x00, 0x00, 0x14] #JNZ 20
        self.cmem.arr[51:56] = [0x60, 0x00, 0x00, 0x00, 0x30] #LD 0x30
        self.cmem.arr[56:61] = [0x6F, 0x00, 0x00, 0x00, 0x01] #OUT 1
        self.cmem.arr[61:62] = [0x07]                         #HALT
        for i in range(300):
            self.doTick()
        self.assertEqual("ffffff1e", self.mem.arr[0x30:0x34].hex())
        self.assertEqual("ffffff1e", self.dp.ex2.cu.get_data().hex())

    def test_ind(self):
        data = [
            [0x40, 0x00, 0x00, 0x00, 0xC0],
            [0x6B, 0x00, 0x00, 0x00, 0x90],
            [0x40, 0x00, 0x00, 0xFE, 0xFF],
            [0x6D, 0x00, 0x00, 0x00, 0x90],
            [0x60, 0x00, 0x00, 0x00, 0xC0],
            [0x07]
        ]
        self.cmem.load_to_mem(data)
        for i in range(70):
            self.doTick()
        self.assertEqual("0000feff", self.dp.b_alu_ac.get_data().hex())


    def test_rel(self):
        data = [
            [0x40, 0x00, 0x00, 0x00, 0xCC],
            [0x42, 0x00, 0x00, 0x00, 0x15],
            [0x82, 0xFF, 0xF8],
            [0x07]
        ]
        self.cmem.load_to_mem(data)
        for i in range(70):
            self.doTick()
        self.assertEqual("fffffffa", self.dp.b_alu_ac.get_data().hex())


class VectorExecModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mem= SharedMemory()
        self.cv = (0).to_bytes(1)
        self.var = (0).to_bytes(4)
        b_cv_part = DataBus(1)
        self.b_vec1 = DataBus(4)
        self.b_vec2 = DataBus(4)
        self.b_vec3 = DataBus(4)
        b_var= DataBus(4)
        b_out = DataBus(4)
        vec1 = Register(b_out, self.b_vec1, 4)
        vec2 = Register(b_out, self.b_vec2, 4)
        vec3 = Register(b_out, self.b_vec3, 4)
        b_cv_part.bind_provider(lambda: self.cv)
        b_var.bind_provider(lambda: self.var)
        self.vem = VectorExecModule(self.mem, b_cv_part,
                                    vec1.get_control_latch(),
                                    vec2.get_control_latch(),
                                    vec3.get_control_latch(),
                                    self.b_vec1, self.b_vec2, self.b_vec3, b_var)
        b_out.bind_provider(self.vem.vdp.b_vec_alu_out.get_data)

    def test_ld_add_st(self):
        self.mem.arr[0x50:0x54] = (0x1245485).to_bytes(4)
        self.var = (0x50).to_bytes(4)
        self.cv = (0x80).to_bytes(1)
        self.vem.l_cu_latch.perform()
        self.vem.l_cu_latch.perform()
        self.assertEqual('01245485', self.b_vec1.get_data().hex())
        self.var = (0x51).to_bytes(4)
        self.cv = (0x81).to_bytes(1)
        self.vem.l_cu_latch.perform()
        self.vem.l_cu_latch.perform()
        self.assertEqual('01245485', self.b_vec1.get_data().hex())
        self.assertEqual('24548500', self.b_vec2.get_data().hex())
        self.cv = (0x10).to_bytes(1)
        self.vem.l_cu_latch.perform()
        self.assertEqual('2578d985', self.b_vec3.get_data().hex())
        self.cv = (0x85).to_bytes(1)
        self.var = (0x60).to_bytes(4)
        self.vem.l_cu_latch.perform()
        self.assertEqual('2578d985', self.mem.arr[0x60:0x64].hex())

    def test_cmp(self):
        self.mem.arr[0x50:0x54] = (0xf1245485).to_bytes(4)
        self.var = (0x50).to_bytes(4)
        self.cv = (0x82).to_bytes(1)
        self.vem.l_cu_latch.perform()
        self.vem.l_cu_latch.perform()
        self.assertEqual('f1245485', self.b_vec3.get_data().hex())
        self.cv = (0x0a).to_bytes(1)
        self.vem.l_cu_latch.perform()
        self.assertEqual('00000002', self.b_vec3.get_data().hex())

class ExtensionModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.mem = SharedMemory()
        self.b_cr_arg = DataBus(4)

        self.vex = ExtensionModule(self.mem, self.b_cr_arg)

        self.cv_nxt = (0).to_bytes(1)
        self.vex.b_cv_nxt.bind_provider(lambda: self.cv_nxt)

        self.cr_arg = (0).to_bytes(4)
        self.b_cr_arg.bind_provider(lambda: self.cr_arg)

        self.l_cu1 = self.vex.l_cu_1
        self.l_cu2 = self.vex.l_cu_2
        self.l_cu3 = self.vex.l_cu_3
        self.l_cu4 = self.vex.l_cu_4
        self.l_var = self.vex.l_var
        self.l_cv = self.vex.l_cv

    def testLoad(self):
        self.mem.arr[50:54] = (0x01245485).to_bytes(4)
        self.mem.arr[54:58] = (0x6546468a).to_bytes(4)
        self.mem.arr[58:62] = (0x0affcd56).to_bytes(4)
        self.mem.arr[62:66] = (0x0123456c).to_bytes(4)
        self.cr_arg = (50).to_bytes(4)
        self.l_var.perform()
        self.cv_nxt = (0x80).to_bytes(1)
        self.l_cv.perform()
        self.assertEqual('00000080', self.vex.b_cv.get_data().hex())
        self.cv_nxt = (0x00).to_bytes(1)

        self.l_cu1.perform()
        self.l_cu1.perform()
        self.assertEqual('01245485', self.vex.b_vec1_1.get_data().hex())

        self.l_cv.perform()
        self.assertEqual('00008000', self.vex.b_cv.get_data().hex())

        self.l_cu2.perform()
        self.l_cu2.perform()
        self.assertEqual('6546468a', self.vex.b_vec1_2.get_data().hex())

        self.l_cv.perform()
        self.assertEqual('00800000', self.vex.b_cv.get_data().hex())

        self.l_cu3.perform()
        self.l_cu3.perform()
        self.assertEqual('0affcd56', self.vex.b_vec1_3.get_data().hex())

        self.l_cv.perform()
        self.assertEqual('80000000', self.vex.b_cv.get_data().hex())

        self.l_cu4.perform()
        self.l_cu4.perform()
        self.assertEqual('0123456c', self.vex.b_vec1_4.get_data().hex())

    def test_line(self):
        self.mem.arr[50:54] = (500).to_bytes(4)
        self.mem.arr[54:58] = (360).to_bytes(4)
        self.mem.arr[58:62] = (-1).to_bytes(4, signed=True)
        self.mem.arr[62:66] = (69).to_bytes(4)

        self.cr_arg = (50).to_bytes(4)
        self.l_var.perform()

        cv = [0x82, 0x01, 0x02, 0x10, 0, 0, 0]

        for i in range(len(cv)):
            self.cv_nxt = (cv[i]).to_bytes(1)
            self.l_cv.perform()
            self.l_cu1.perform()
            self.l_cu2.perform()
            self.l_cu3.perform()
            self.l_cu4.perform()
            state = int.from_bytes(self.vex.b_cv_state.get_data()) >> 1
            if state == 1:
                self.l_cu1.perform()
            elif state == 2:
                self.l_cu2.perform()
            elif state == 3:
                self.l_cu3.perform()
            elif state == 4:
                self.l_cu4.perform()

        self.assertEqual('000003e8', self.vex.b_vec3_1.get_data().hex())
        self.assertEqual('000002d0', self.vex.b_vec3_2.get_data().hex())
        self.assertEqual('fffffffe', self.vex.b_vec3_3.get_data().hex())
        self.assertEqual('0000008a', self.vex.b_vec3_4.get_data().hex())









from cpu.components import DataBus, Register, MultiPlex, ALU, DeviceControlUnitInput, Latch, \
    DeviceControlUnitOutput, \
    MemoryUnit, SimpleAction, BiAction, InstructionDecoder, ImmediateValue, FourPartRegister, VectorStateLogic
from cpu.utils import SharedMemory

from cpu.components import SimpleExtender, VectorControlUnit


class ExternalDevice1:
    def __init__(self, l_io_in: Latch):
        self.l_io_in = l_io_in
        self.b_io_d_1 = DataBus(4)
        self.b_io_r_1 = DataBus(1)
        self.b_to_reg = DataBus(4)
        self.data1 = Register(self.b_to_reg, self.b_io_d_1, 4)
        self.l_reg = self.data1.get_control_latch()
        self.cu = DeviceControlUnitInput(self.b_to_reg, self.l_reg, self.b_io_r_1, self.l_io_in)

class ExternalDevice2:
    def __init__(self):
        self.b_io_d_2 = DataBus(4)
        self.b_io_r_2 = DataBus(1)
        self.b_from_reg = DataBus(4)
        self.data2 = Register(self.b_io_d_2, self.b_from_reg, 4)
        self.l_reg = self.data2.get_control_latch()
        self.cu = DeviceControlUnitOutput(self.b_from_reg, self.l_reg, self.b_io_r_2)
        self.l_io_out = self.cu.get_control_latch()

class MainDataPath:
    def __init__(self, mem: SharedMemory):
        self.b_alu_ac = DataBus(4)
        self.b_alu_op = DataBus(1)
        self.b_alu_inp2 = DataBus(4)
        self.b_alu_flag = DataBus(1)
        self.b_alu_out = DataBus(4)
        self.b_alu_choice = DataBus(1)
        self.b_ar = DataBus(4)
        self.b_mem_out = DataBus(4)
        self.b_cr_arg = DataBus(4)
        self.b_data_op = DataBus(1)
        self.b_flg = DataBus(1)

        self.ac = Register(self.b_alu_out, self.b_alu_ac, 4)
        self.ar = Register(self.b_alu_out, self.b_ar, 4)
        self.flg = Register(self.b_alu_flag, self.b_flg, 1)

        self.l_ac = self.ac.get_control_latch()
        self.l_ar = self.ar.get_control_latch()
        self.l_flg = self.flg.get_control_latch()

        self.mux = MultiPlex(self.b_alu_choice,self.b_alu_inp2, 4)
        self.mux.bind_inp(0, self.b_cr_arg)
        self.mux.bind_inp(1, self.b_mem_out)
        self.mux.bind_inp(2, self.b_ar)

        self.alu = ALU(self.b_alu_op, self.b_alu_ac, self.b_alu_inp2, self.b_alu_flag, self.b_alu_out)

        self.mu = MemoryUnit(self.b_data_op, self.b_ar, self.b_alu_out, self.b_mem_out, mem)
        self.l_data = self.mu.get_control_latch()

        self.ex1 = ExternalDevice1(self.mu.get_input_latch())
        self.ex2 = ExternalDevice2()
        self.mu.bind_input_io(self.ex1.b_io_d_1, self.ex1.b_io_r_1)
        self.mu.bind_output_io(self.ex2.b_io_d_2, self.ex2.b_io_r_2, self.ex2.l_io_out)

        self.b_int_got = DataBus(1)
        self.b_int_allow = DataBus(1)
        self.mu.bind_int_buses(self.b_int_got, self.b_int_allow)



class VectorDataPath:
    def __init__(self, mem: SharedMemory, b_vec1: DataBus, b_vec2: DataBus, b_vec3: DataBus, b_var: DataBus):
        self.b_vec1 = b_vec1
        self.b_vec2 = b_vec2
        self.b_vec3 = b_vec3

        self.b_alu_inp_choice_1 = DataBus(1)
        self.b_alu_inp_choice_2 = DataBus(1)
        self.b_alu_out_choice = DataBus(1)
        self.b_alu_op_vec = DataBus(1)

        self.b_vec_alu_out = DataBus(4)
        self.b_var = b_var
        self.b_data = DataBus(4)
        self.b_data_op = DataBus(1)
        self.b_inp_1 = DataBus(4)
        self.b_inp_2 = DataBus(4)
        self.b_out = DataBus(4)
        self.b_flg = DataBus(1)
        self.b_flg_ext = DataBus(4)

        self.alu = ALU(self.b_alu_op_vec, self.b_inp_1, self.b_inp_2, self.b_flg, self.b_out)

        self.ext = SimpleExtender(self.b_flg, self.b_flg_ext, 4)

        self.mux1 = MultiPlex(self.b_alu_inp_choice_1, self.b_inp_1, 4)
        self.mux1.bind_inp(0, self.b_vec3)
        self.mux1.bind_inp(1, self.b_vec2)
        self.mux1.bind_inp(2, self.b_vec1)

        self.mux2 = MultiPlex(self.b_alu_inp_choice_2, self.b_inp_2, 4)
        self.mux2.bind_inp(0, self.b_vec3)
        self.mux2.bind_inp(1, self.b_vec2)
        self.mux2.bind_inp(2, self.b_vec1)
        self.mux2.bind_inp(3, self.b_data)

        self.mux_out = MultiPlex(self.b_alu_out_choice, self.b_vec_alu_out, 4)
        self.mux_out.bind_inp(0, self.b_flg_ext)
        self.mux_out.bind_inp(1, self.b_out)

        self.mu = MemoryUnit(self.b_data_op, self.b_var, self.b_vec_alu_out, self.b_data, mem)
        self.l_data = self.mu.get_control_latch()

class VectorExecModule:
    def __init__(self, mem: SharedMemory, b_cv_part: DataBus,
                 l_vec1: Latch, l_vec2: Latch, l_vec3: Latch,
                 b_vec1: DataBus, b_vec2: DataBus, b_vec3: DataBus, b_var: DataBus):
        self.vdp = VectorDataPath(mem, b_vec1, b_vec2, b_vec3, b_var)
        self.b_cv_part = b_cv_part
        self.l_vec1 = l_vec1
        self.l_vec2 = l_vec2
        self.l_vec3 = l_vec3

        self.vcu = VectorControlUnit(self.b_cv_part,
                                     self.vdp.b_alu_inp_choice_1,
                                     self.vdp.b_alu_inp_choice_2,
                                     self.vdp.b_alu_op_vec,
                                     self.vdp.b_alu_out_choice,
                                     self.vdp.b_data_op,
                                     self.vdp.l_data,
                                     self.l_vec1,
                                     self.l_vec2,
                                     self.l_vec3
                                     )
        self.l_cu_latch = self.vcu.get_control_latch()

class ExtensionModule:
    def __init__(self, mem: SharedMemory, b_cr_arg: DataBus):
        self.b_cr_arg = b_cr_arg
        self.b_cv_nxt = DataBus(1)
        self.b_cv_state = DataBus(1)

        self.b_cv_n = DataBus(4)
        self.b_cv = DataBus(4)
        self.b_var = DataBus(4)
        self.b_var_1  = DataBus(4)
        self.b_var_2 = DataBus(4)
        self.b_var_3 = DataBus(4)
        self.b_var_4 = DataBus(4)
        self.b_cv_1 = DataBus(1)
        self.b_cv_2 = DataBus(1)
        self.b_cv_3 = DataBus(1)
        self.b_cv_4 = DataBus(1)

        self.b_vec1_1 = DataBus(4)
        self.b_vec1_2 = DataBus(4)
        self.b_vec1_3 = DataBus(4)
        self.b_vec1_4 = DataBus(4)
        self.b_vec2_1 = DataBus(4)
        self.b_vec2_2 = DataBus(4)
        self.b_vec2_3 = DataBus(4)
        self.b_vec2_4 = DataBus(4)
        self.b_vec3_1 = DataBus(4)
        self.b_vec3_2 = DataBus(4)
        self.b_vec3_3 = DataBus(4)
        self.b_vec3_4 = DataBus(4)

        self.b_out_1 = DataBus(4)
        self.b_out_2 = DataBus(4)
        self.b_out_3 = DataBus(4)
        self.b_out_4 = DataBus(4)

        self.var = Register(self.b_cr_arg, self.b_var, 4)
        self.l_var = self.var.get_control_latch()
        self.cv = Register(self.b_cv_n, self.b_cv, 4)
        self.l_cv = self.cv.get_control_latch()
        self.vec1 = FourPartRegister(self.b_out_1, self.b_out_2, self.b_out_3, self.b_out_4,
                                     self.b_vec1_1, self.b_vec1_2, self.b_vec1_3, self.b_vec1_4, 4)
        self.vec2 = FourPartRegister(self.b_out_1, self.b_out_2, self.b_out_3, self.b_out_4,
                                     self.b_vec2_1, self.b_vec2_2, self.b_vec2_3, self.b_vec2_4, 4)
        self.vec3 = FourPartRegister(self.b_out_1, self.b_out_2, self.b_out_3, self.b_out_4,
                                     self.b_vec3_1, self.b_vec3_2, self.b_vec3_3, self.b_vec3_4, 4)

        self.sa_cv_1 = SimpleAction(self.b_cv, self.b_cv_1, lambda x: x[3:4])
        self.sa_cv_2 = SimpleAction(self.b_cv, self.b_cv_2, lambda x: x[2:3])
        self.sa_cv_3 = SimpleAction(self.b_cv, self.b_cv_3, lambda x: x[1:2])
        self.sa_cv_4 = SimpleAction(self.b_cv, self.b_cv_4, lambda x: x[0:1])

        self.sa_var_1 = SimpleAction(self.b_var, self.b_var_1, lambda x: x)
        self.sa_var_2 = SimpleAction(self.b_var, self.b_var_2, lambda x: int.to_bytes(int.from_bytes(x)+4, 4))
        self.sa_var_3 = SimpleAction(self.b_var, self.b_var_3, lambda x: int.to_bytes(int.from_bytes(x)+8, 4))
        self.sa_var_4 = SimpleAction(self.b_var, self.b_var_4, lambda x: int.to_bytes(int.from_bytes(x)+12, 4))

        self.vsl = VectorStateLogic(self.b_cv, self.b_cv_state)

        self.bi_cv = BiAction(self.b_cv, self.b_cv_nxt, self.b_cv_n, lambda a,b: bytes.fromhex(a[1:4].hex()+b[0:1].hex()))

        self.vem1 = VectorExecModule(mem, self.b_cv_1,
                                    self.vec1.get_control_latch_1(),
                                    self.vec2.get_control_latch_1(),
                                    self.vec3.get_control_latch_1(),
                                    self.b_vec1_1, self.b_vec2_1, self.b_vec3_1, self.b_var_1)

        self.vem2 = VectorExecModule(mem, self.b_cv_2,
                                     self.vec1.get_control_latch_2(),
                                     self.vec2.get_control_latch_2(),
                                     self.vec3.get_control_latch_2(),
                                     self.b_vec1_2, self.b_vec2_2, self.b_vec3_2, self.b_var_2)

        self.vem3 = VectorExecModule(mem, self.b_cv_3,
                                     self.vec1.get_control_latch_3(),
                                     self.vec2.get_control_latch_3(),
                                     self.vec3.get_control_latch_3(),
                                     self.b_vec1_3, self.b_vec2_3, self.b_vec3_3, self.b_var_3)

        self.vem4 = VectorExecModule(mem, self.b_cv_4,
                                     self.vec1.get_control_latch_4(),
                                     self.vec2.get_control_latch_4(),
                                     self.vec3.get_control_latch_4(),
                                     self.b_vec1_4, self.b_vec2_4, self.b_vec3_4, self.b_var_4)

        self.b_out_1.bind_provider(self.vem1.vdp.b_vec_alu_out.get_data)
        self.b_out_2.bind_provider(self.vem2.vdp.b_vec_alu_out.get_data)
        self.b_out_3.bind_provider(self.vem3.vdp.b_vec_alu_out.get_data)
        self.b_out_4.bind_provider(self.vem4.vdp.b_vec_alu_out.get_data)

        self.l_cu_1 = self.vem1.vcu.get_control_latch()
        self.l_cu_2 = self.vem2.vcu.get_control_latch()
        self.l_cu_3 = self.vem3.vcu.get_control_latch()
        self.l_cu_4 = self.vem4.vcu.get_control_latch()


class MainControlUnit:
    def __init__(self, datapath: MainDataPath, vex: ExtensionModule, cmem: SharedMemory):
        self.dp = datapath
        self.l_cv = vex.l_cv
        self.b_cv_nxt = vex.b_cv_nxt
        self.b_cv_state = vex.b_cv_state
        self.l_var = vex.l_var

        self.b_pc_choice = DataBus(1)
        self.b_cr_choice = DataBus(1)
        self.b_pc = DataBus(4)
        self.b_pc_new = DataBus(4)
        self.b_cmd = DataBus(5)
        self.b_cdata = DataBus(5)
        self.b_ra = DataBus(4)
        self.b_int_addr = DataBus(4)

        self.ra = Register(self.b_pc, self.b_ra, 4)
        self.pc = Register(self.b_pc_new, self.b_pc, 4)
        self.cr = Register(self.b_cdata, self.b_cmd, 5)

        self.l_ra = self.ra.get_control_latch()
        self.l_pc = self.pc.get_control_latch()
        self.l_cr = self.cr.get_control_latch()

        const_0_1 = DataBus(1)
        const_0_1.bind_provider(lambda: (0).to_bytes(1))
        const_0_5 = DataBus(5)
        const_0_5.bind_provider(lambda: (0).to_bytes(5))
        self.cmu = MemoryUnit(const_0_1, self.b_pc, const_0_5, self.b_cdata, cmem, 5)
        self.l_cdata = self.cmu.get_control_latch()

        b_pc_2 = DataBus(4)
        b_pc_1 = DataBus(4)
        b_pc_0 = DataBus(4)
        self.sa_pc_0 = SimpleAction(self.b_pc, b_pc_0,
                                    lambda x: (int.from_bytes(x, signed=False) + 5).to_bytes(4, signed=False))
        self.sa_pc_1 = SimpleAction(self.b_pc, b_pc_1,
                                    lambda x: (int.from_bytes(x, signed=False) + 3).to_bytes(4, signed=False))
        self.sa_pc_2 = SimpleAction(self.b_pc, b_pc_2,
                                    lambda x: (int.from_bytes(x, signed=False) + 1).to_bytes(4, signed=False))
        self.iv_pc_5 = ImmediateValue(self.b_int_addr, (0x05).to_bytes(4, signed=False))

        self.mux_pc = MultiPlex(self.b_pc_choice, self.b_pc_new, 4)
        self.mux_pc.bind_inp(0, b_pc_0)
        self.mux_pc.bind_inp(1, b_pc_1)
        self.mux_pc.bind_inp(2, b_pc_2)
        self.mux_pc.bind_inp(3, self.b_ra)
        self.mux_pc.bind_inp(4, self.dp.b_cr_arg)
        self.mux_pc.bind_inp(5, self.b_int_addr)

        b_cr_arg_0 = DataBus(4)
        b_cr_arg_1 = DataBus(4)

        self.sa_cr_1 = SimpleAction(self.b_cmd, b_cr_arg_1, lambda x: x[1:5])
        self.ba_cr_0 = BiAction(self.b_pc, self.b_cmd, b_cr_arg_0, lambda a, b: (
                    int.from_bytes(a, signed=False) + int.from_bytes(b[1:3], signed=True)).to_bytes(4, signed=False))

        self.mx_cr_arg = MultiPlex(self.b_cr_choice, self.dp.b_cr_arg, 4)
        self.mx_cr_arg.bind_inp(0, b_cr_arg_0)
        self.mx_cr_arg.bind_inp(1, b_cr_arg_1)

        self.id = InstructionDecoder(
            self.l_pc,
            self.l_cdata,
            self.l_cr,
            self.l_ra,
            self.dp.l_data,
            self.dp.l_ac,
            self.dp.l_ar,
            self.dp.l_flg,
            self.l_var,
            self.l_cv,
            vex.l_cu_1,
            vex.l_cu_2,
            vex.l_cu_3,
            vex.l_cu_4,
            self.b_cmd,
            self.b_pc_choice,
            self.b_cr_choice,
            self.dp.b_alu_choice,
            self.dp.b_alu_op,
            self.dp.b_data_op,
            self.dp.b_int_got,
            self.dp.b_int_allow,
            self.b_cv_nxt,
            self.b_cv_state,
            self.dp.b_flg
        )








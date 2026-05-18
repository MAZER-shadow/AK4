import queue
from typing import Callable

from .utils import WrongImplementationError, ALUOperations, ForbiddenAddress, SharedMemory, CUState


class Latch:

    def __init__(self, callfunc: Callable[[], None]):
        self.__callfunc = callfunc

    def perform(self) -> None:
        self.__callfunc()



class DataBus:
    __provider: Callable[[], bytes]|None

    def __init__(self, size: int):
        self.__provider = None
        self.__size = size

    def get_data(self) -> bytes:
        if self.__provider is None:
            raise WrongImplementationError("Bus not connected")
        data = self.__provider()
        if len(data) != self.__size:
            raise WrongImplementationError("Buffer size: " + str(self.__size) + " does not equals " + str(len(data)))
        return data

    def bind_provider(self, provider: Callable[[], bytes]) -> None:
        if self.__provider is not None:
            raise WrongImplementationError("Bus already connected")
        self.__provider = provider

    def unbind_provider(self) -> None:
        self.__provider = None

    def get_size(self) -> int:
        return self.__size


class MemoryUnit:
    __data_arr: bytearray
    __io_in_data: DataBus
    __io_in_r: DataBus
    __io_out_data: DataBus
    __io_out_r: DataBus
    __io_out_l: Latch
    __b_inp_got: DataBus
    __b_inp_allow: DataBus
    __input_data: bytes|None
    __out_io_val: bytes

    def __init__(self, bus_op: DataBus, bus_address: DataBus, bus_in: DataBus, bus_out: DataBus, data_arr: SharedMemory, bus_size: int = 4):
        self.__data_arr = data_arr.arr
        self.__bus_op = bus_op
        self.__bus_address = bus_address
        self.__bus_in = bus_in
        self.__bus_out = bus_out
        self.__size_bus = bus_size
        self.__io_mode = False
        self.__inp_got = False
        # if self.__bus_address.get_size() != self.__size_bus:
        #     raise WrongImplementationError("Addr bus size: " + str(self.__bus_address.get_size()) + " does not equals " + str(self.__size_bus))
        if self.__bus_in.get_size() != self.__size_bus:
            raise WrongImplementationError(
                "In bus size: " + str(self.__bus_in.get_size()) + " does not equals " + str(self.__size_bus))
        if self.__bus_out.get_size() != self.__size_bus:
            raise WrongImplementationError(
                "In bus size: " + str(self.__bus_out.get_size()) + " does not equals " + str(self.__size_bus))
        self.__bus_out.bind_provider(self.get_value)



    out_val: bytes

    def get_control_latch(self) -> Latch:
        return Latch(self.__perform_change)

    def __perform_change(self) -> None:
        addr = int.from_bytes(self.__bus_address.get_data())
        op = self.__bus_op.get_data()
        rw = op[0] & 1 != 0
        port_mode = op[0] & 2 != 0
        if port_mode:
            if not self.__io_mode:
                raise ForbiddenAddress("Port IO is not bound on this memory unit")
            if rw:
                if addr != 0x0001:
                    raise ForbiddenAddress(f"Unknown output port: {addr}")
                self.__out_io_val = self.__bus_in.get_data()
                self.__io_out_l.perform()
            else:
                if addr != 0x0000:
                    raise ForbiddenAddress(f"Unknown input port: {addr}")
                self.out_val = self.__input_data if self.__input_data is not None else bytes(self.__size_bus)
                self.__input_data = None
                self.__inp_got = False
            return
        if rw:
            in_data = self.__bus_in.get_data()
            self.__data_arr[addr:addr+self.__size_bus] = in_data
        else:
            self.out_val = self.__data_arr[addr:addr+self.__size_bus]

    def get_value(self) -> bytes:
        return self.out_val

    def __io_in_state(self) -> bytes:
        return self.__b_inp_allow.get_data()

    def __init_int(self):
        in_data = self.__io_in_data.get_data()
        self.__input_data = in_data
        self.__inp_got = True

    def __get_int_state(self) -> bytes:
        if self.__inp_got:
            return (1).to_bytes(1)
        else:
            return (0).to_bytes(1)

    def __get_io_output_value(self) -> bytes:
        return self.__out_io_val

    def bind_input_io(self, b_data: DataBus, b_ready: DataBus) -> None:
        self.__io_mode = True
        self.__io_in_data = b_data
        self.__io_in_r = b_ready
        self.__io_in_r.bind_provider(self.__io_in_state)

    def get_input_latch(self) -> Latch:
        return Latch(self.__init_int)

    def bind_int_buses(self, b_int_got: DataBus, b_int_allow: DataBus) -> None:
        self.__b_inp_got = b_int_got
        self.__b_inp_allow = b_int_allow
        self.__b_inp_got.bind_provider(self.__get_int_state)

    def bind_output_io(self, b_data: DataBus, b_ready: DataBus, l_out: Latch) -> None:
        self.__io_mode = True
        self.__io_out_data = b_data
        self.__io_out_r = b_ready
        self.__io_out_data.bind_provider(self.__get_io_output_value)
        self.__io_out_l = l_out


class Register:
    __value: bytes
    def __init__(self, bus_in: DataBus, bus_out: DataBus, size: int):
        self.__value = bytearray(size)
        self.__bus_in = bus_in
        bus_out.bind_provider(self.get_value)

    def get_value(self) -> bytes:
        return self.__value

    def __update_value(self) -> None:
        self.__value = self.__bus_in.get_data()

    def get_control_latch(self) -> Latch:
        return Latch(self.__update_value)


class MultiPlex:
    __Bindings: dict[int, DataBus]
    def __init__(self, b_ctrl: DataBus, b_out: DataBus, size: int):
        self.__b_ctrl = b_ctrl
        self.__size = size
        self.__Bindings = dict()
        self.b_out = b_out
        self.__data = bytes(self.__size)
        b_out.bind_provider(self.__getvalue)

    def bind_inp(self, code:int, bus: DataBus) -> None:
        self.__Bindings[code] = bus

    def __getvalue(self) -> bytes:
        choice = int.from_bytes(self.__b_ctrl.get_data())
        if choice not in self.__Bindings:
            raise WrongImplementationError("Multiplex choice is not bound: " + str(choice))

        return self.__Bindings[choice].get_data()

class ALU:

    def __init__(self, b_op: DataBus, b_in_1: DataBus, b_in_2: DataBus, b_flg: DataBus, b_out: DataBus):
        self.__b_op = b_op
        self.__b_in_1 = b_in_1
        self.__b_in_2 = b_in_2
        self.operations = {el.value: el for el in ALUOperations}
        self.__out = (0).to_bytes(4)
        self.__flg = (0).to_bytes(2)
        b_flg.bind_provider(self.__get_flg)
        b_out.bind_provider(self.__get_out)

    def __get_flg(self) -> bytes:
        self.perform()
        return self.__flg

    def __get_out(self) -> bytes:
        self.perform()
        return self.__out

    def perform(self):
        op_code_full = int.from_bytes(self.__b_op.get_data())
        op_code_op = op_code_full & 0b00001111
        flg_byte   = op_code_full & 0b00010000 != 0
        flg_inc    = op_code_full & 0b00100000 != 0
        flg_dec    = op_code_full & 0b01000000 != 0
        flg_inv    = op_code_full & 0b10000000 != 0
        operation = self.operations[op_code_op]
        data1 = self.__b_in_1.get_data()
        data2 = self.__b_in_2.get_data()
        op1 = int.from_bytes(data1, signed=True)
        op2 = int.from_bytes(data2, signed=True)
        res = self.perform_operation(operation, op1, op2, False)
        resu = self.perform_operation(operation, op1, op2, True)

        if flg_inc:
            res += 1

        if flg_dec:
            res -= 1

        if flg_inv:
            res = ~res

        if flg_byte:
            c = 0 if (res & 0x100) == 0 else 1
            v = 0 if -128 <= res <= 127 else 1
            res = res & 0xFF
            n = 1 if res > 127 else 0
            z = 0 if res != 0 else 1
        else:
            c = 0 if (resu & 0x100000000) == 0 else 1
            v = 0 if -2147483648 <= res <= 2147483647 else 1
            res = res & 0xFFFFFFFF
            n = 1 if res > 2147483647 else 0
            z = 0 if res != 0 else 1
        self.__flg = int.to_bytes((c << 3) + (v << 2) + (n << 1) + z, 1)
        self.__out = int.to_bytes(res, 4, signed=False)

    def perform_operation(self, operation: ALUOperations, op1e: int, op2e: int, unsigned: bool) -> int:
        if unsigned:
            op1 = (0x100000000+op1e)%0x100000000
            op2 = (0x100000000+op2e)%0x100000000
        else:
            op1 = op1e
            op2 = op2e
        if operation == ALUOperations.Add:
            res = op1 + op2
        elif operation == ALUOperations.Sub:
            if unsigned: res = op1 + 0x100000000-op2
            else: res = op1 - op2
        elif operation == ALUOperations.Mul:
            res = op1 * op2
        elif operation == ALUOperations.Div:
            res = op1 // op2
        elif operation == ALUOperations.Rem:
            res = op1 % op2
        elif operation == ALUOperations.Left:
            res = op1
        elif operation == ALUOperations.Right:
            res = op2
        elif operation == ALUOperations.ShiftL:
            res = op1 << op2
        elif operation == ALUOperations.ShiftR:
            res = op1 >> op2
        elif operation == ALUOperations.And:
            res = op1 & op2
        elif operation == ALUOperations.Or:
            res = op1 | op2
        elif operation == ALUOperations.Xor:
            res = op1 ^ op2
        elif operation == ALUOperations.Inc4:
            res = op1 + 4
        elif operation == ALUOperations.Dec4:
            res = op1 - 4
        elif operation == ALUOperations.Inc4r:
            res = op2 + 4
        elif operation == ALUOperations.Dec4r:
            res = op2 - 4
        else:
            raise WrongImplementationError("Operation not implemented ")
        return res

class DeviceControlUnitInput:
    __data: bytes|None
    def __init__(self, b_to_reg: DataBus, l_reg: Latch, b_io_r: DataBus, l_io_in: Latch):
        self.__b_to_reg = b_to_reg
        self.__l_reg = l_reg
        self.__b_io_r = b_io_r
        self.__l_io_in = l_io_in
        self.__b_to_reg.bind_provider(self.__get_data_to_reg)
        self.input_queue = queue.Queue()

    def __get_data_to_reg(self) -> bytes:
        return self.__data

    def post_data(self, data: bytes|None = None) -> None:
        if data is not None:
            self.input_queue.put(data)
        if int.from_bytes(self.__b_io_r.get_data()) != 1:
            return
        if self.input_queue.empty():
            return
        self.__data = self.input_queue.get()
        self.__l_reg.perform()
        self.__l_io_in.perform()

class DeviceControlUnitOutput:

    def __init__(self, b_from_reg: DataBus, l_reg: Latch, b_io_r: DataBus):
        self.__b_from_reg = b_from_reg
        self.__l_reg = l_reg
        self.__b_io_r = b_io_r
        self.__b_io_r.bind_provider(self.__get_ready)
        self.output_queue = queue.Queue()

    def __get_ready(self) -> bytes:
        return (1).to_bytes(1, signed=False)

    def __load_data(self):
        self.__l_reg.perform()
        self.output_queue.put(self.__b_from_reg.get_data())

    def get_control_latch(self) -> Latch:
        return Latch(self.__load_data)

    def get_data(self) -> bytes|None:
        if self.output_queue.empty():
            return None
        else:
            return self.output_queue.get()


class SimpleAction:
    def __init__(self, b_in: DataBus, b_out: DataBus, action: Callable[[bytes],bytes]):
        self.__b_in = b_in
        self.__b_out = b_out
        self.__action = action
        self.__b_out.bind_provider(lambda: self.__action(self.__b_in.get_data()))

class BiAction:
    def __init__(self, b_in1: DataBus,b_in2: DataBus, b_out: DataBus, action: Callable[[bytes,bytes],bytes]):
        self.__b_in1 = b_in1
        self.__b_in2 = b_in2
        self.__b_out = b_out
        self.__action = action
        self.__b_out.bind_provider(lambda: self.__action(self.__b_in1.get_data(), self.__b_in2.get_data()))

class InstructionDecoder:
    def __init__(self,
                 l_pc: Latch,
                 l_cdata: Latch,
                 l_cr: Latch,
                 l_ra: Latch,
                 l_data: Latch,
                 l_ac: Latch,
                 l_ar: Latch,
                 l_flg: Latch,
                 l_var: Latch,
                 l_cv: Latch,
                 l_vcu1: Latch,
                 l_vcu2: Latch,
                 l_vcu3: Latch,
                 l_vcu4: Latch,
                 b_cmd: DataBus,
                 b_pc_choice: DataBus,
                 b_cr_choice: DataBus,
                 b_alu_choice: DataBus,
                 b_alu_op: DataBus,
                 b_data_op: DataBus,
                 b_int_got: DataBus,
                 b_int_allow: DataBus,
                 b_cv_nxt: DataBus,
                 b_cv_state: DataBus,
                 b_flg: DataBus
                 ):

        self.__l_pc = l_pc
        self.__l_cdata = l_cdata
        self.__l_cr = l_cr
        self.__l_ra = l_ra
        self.__l_data = l_data
        self.__l_ac = l_ac
        self.__l_ar = l_ar
        self.__l_cv = l_cv
        self.__l_flg = l_flg
        self.__l_var = l_var
        self.__l_vcu1 = l_vcu1
        self.__l_vcu2 = l_vcu2
        self.__l_vcu3 = l_vcu3
        self.__l_vcu4 = l_vcu4

        #in buses
        self.__b_cmd = b_cmd
        self.__b_int_got = b_int_got
        self.__b_flg = b_flg
        self.__b_cv_state = b_cv_state

        #out buses
        self.__b_pc_choice = b_pc_choice
        self.__b_cr_choice = b_cr_choice
        self.__b_alu_choice = b_alu_choice
        self.__b_alu_op = b_alu_op
        self.__b_data_op = b_data_op
        self.__b_int_allow = b_int_allow
        self.__b_cv_nxt = b_cv_nxt

        self.pc_choice = (0).to_bytes(1, signed=False)
        self.__b_pc_choice.bind_provider(lambda: self.pc_choice)

        self.cr_choice = (0).to_bytes(1, signed=False)
        self.__b_cr_choice.bind_provider(lambda: self.cr_choice)

        self.alu_choice = (0).to_bytes(1, signed=False)
        self.__b_alu_choice.bind_provider(lambda: self.alu_choice)

        self.alu_op = (0).to_bytes(1, signed=False)
        self.__b_alu_op.bind_provider(lambda: self.alu_op)

        self.data_op = (0).to_bytes(1, signed=False)
        self.__b_data_op.bind_provider(lambda: self.data_op)

        self.cv_nxt = (0).to_bytes(1, signed=False)
        self.__b_cv_nxt.bind_provider(lambda: self.cv_nxt)

        self.interception = 0
        self.stop = False
        self.state = CUState.PreStart
        self.ticks = queue.Queue()

        self.__b_int_allow.bind_provider(lambda: (1 & (1 ^ (int.from_bytes(self.__b_int_got.get_data()) | int.from_bytes(self.__b_cv_state.get_data()) | self.interception))).to_bytes(1))

        self.cmd_read = False
        self.additional_tick = False

    def put_to_ticks(self, ticks: list[Callable[[],None]]) -> None:
        for el in ticks:
            self.ticks.put(el)

    def tick_read(self) -> Callable[[],None]:
        def tick1() -> None:
            self.data_op = (0).to_bytes(1, signed=False)
            self.__l_data.perform()
        return tick1

    def inc(self) -> list[Callable[[],None]]:
        def tick1() -> None:
            self.alu_op = (0b00100111).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()
        return [tick1]

    def dec(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_op = (0b01000111).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def inc4(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_op = (0b00001100).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def dec4(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_op = (0b00001101).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def inv(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_op = (0b10000111).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def neg(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_op = (0b11000111).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def ld_imm(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_choice =  (0).to_bytes(1, signed=False)
            self.alu_op = (0b00001000).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def add_imm(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_choice =  (0).to_bytes(1, signed=False)
            self.alu_op = (0b00000000).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def sub_imm(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_choice =  (0).to_bytes(1, signed=False)
            self.alu_op = (0b00000001).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()
        return [tick1]

    def and_imm(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_choice =  (0).to_bytes(1, signed=False)
            self.alu_op = (0b00001001).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def or_imm(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_choice =  (0).to_bytes(1, signed=False)
            self.alu_op = (0b00001010).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def xor_imm(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_choice =  (0).to_bytes(1, signed=False)
            self.alu_op = (0b00001011).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def shiftl_imm(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_choice =  (0).to_bytes(1, signed=False)
            self.alu_op = (0b00000010).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def shiftr_imm(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_choice =  (0).to_bytes(1, signed=False)
            self.alu_op = (0b00000011).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def mul_imm(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_choice =  (0).to_bytes(1, signed=False)
            self.alu_op = (0b00000101).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def div_imm(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_choice =  (0).to_bytes(1, signed=False)
            self.alu_op = (0b00000100).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def rem_imm(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.alu_choice =  (0).to_bytes(1, signed=False)
            self.alu_op = (0b00000110).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1]

    def ld_addr(self) -> list[Callable[[], None]]:
        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00001000).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [self.tick_read(), tick2]

    def st_addr(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.data_op = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00000111).to_bytes(1, signed=False)
            self.__l_data.perform()

        return [tick1]

    def add_addr(self) -> list[Callable[[], None]]:
        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00000000).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [self.tick_read(), tick2]

    def sub_addr(self) -> list[Callable[[], None]]:
        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00000001).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [self.tick_read(), tick2]

    def and_addr(self) -> list[Callable[[], None]]:
        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00001001).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [self.tick_read(), tick2]

    def or_addr(self) -> list[Callable[[], None]]:

        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00001010).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [self.tick_read(), tick2]

    def xor_addr(self) -> list[Callable[[], None]]:
        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00001011).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [self.tick_read(), tick2]

    def shiftl_addr(self) -> list[Callable[[], None]]:
        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00000010).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [self.tick_read(), tick2]

    def shiftr_addr(self) -> list[Callable[[], None]]:
        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00000011).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [self.tick_read(), tick2]

    def mul_addr(self) -> list[Callable[[], None]]:
        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00000101).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [self.tick_read(), tick2]

    def div_addr(self) -> list[Callable[[], None]]:
        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00000100).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [self.tick_read(), tick2]

    def rem_addr(self) -> list[Callable[[], None]]:
        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00000110).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [self.tick_read(), tick2]

    def jump(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.pc_choice = (4).to_bytes(1, signed=False)
            self.__l_pc.perform()

        return [tick1]

    def jz(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            if int.from_bytes(self.__b_flg.get_data()) & 1 == 0:
                return
            self.pc_choice = (4).to_bytes(1, signed=False)
            self.__l_pc.perform()

        return [tick1]

    def jnz(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            if int.from_bytes(self.__b_flg.get_data()) & 1 != 0:
                return
            self.pc_choice = (4).to_bytes(1, signed=False)
            self.__l_pc.perform()

        return [tick1]

    def jgt(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            if int.from_bytes(self.__b_flg.get_data()) & 2 != 0:
                return
            self.pc_choice = (4).to_bytes(1, signed=False)
            self.__l_pc.perform()

        return [tick1]

    def jlt(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            if int.from_bytes(self.__b_flg.get_data()) & 2 == 0:
                return
            self.pc_choice = (4).to_bytes(1, signed=False)
            self.__l_pc.perform()

        return [tick1]

    def jc(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            if int.from_bytes(self.__b_flg.get_data()) & 8 == 0:
                return
            self.pc_choice = (4).to_bytes(1, signed=False)
            self.__l_pc.perform()

        return [tick1]

    def jnc(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            if int.from_bytes(self.__b_flg.get_data()) & 8 != 0:
                return
            self.pc_choice = (4).to_bytes(1, signed=False)
            self.__l_pc.perform()

        return [tick1]

    def jv(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            if int.from_bytes(self.__b_flg.get_data()) & 4 == 0:
                return
            self.pc_choice = (4).to_bytes(1, signed=False)
            self.__l_pc.perform()

        return [tick1]

    def jnv(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            if int.from_bytes(self.__b_flg.get_data()) & 4 != 0:
                return
            self.pc_choice = (4).to_bytes(1, signed=False)
            self.__l_pc.perform()

        return [tick1]

    def halt(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.stop = True

        return [tick1]

    def ld_ind(self) -> list[Callable[[], None]]:
        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00001000).to_bytes(1, signed=False)
            self.__l_ar.perform()

        def tick4() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00001000).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [self.tick_read(), tick2, self.tick_read(),tick4]

    def st_ind(self) -> list[Callable[[], None]]:
        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00001000).to_bytes(1, signed=False)
            self.__l_ar.perform()

        def tick3() -> None:
            self.data_op = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00000111).to_bytes(1, signed=False)
            self.__l_data.perform()

        return [self.tick_read(), tick2,tick3]

    def in_port(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.data_op = (0b00000010).to_bytes(1, signed=False)
            self.__l_data.perform()

        def tick2() -> None:
            self.alu_choice = (1).to_bytes(1, signed=False)
            self.alu_op = (0b00001000).to_bytes(1, signed=False)
            self.__l_flg.perform()
            self.__l_ac.perform()

        return [tick1, tick2]

    def out_port(self) -> list[Callable[[], None]]:
        def tick1() -> None:
            self.data_op = (0b00000011).to_bytes(1, signed=False)
            self.alu_op = (0b00000111).to_bytes(1, signed=False)
            self.__l_data.perform()

        return [tick1]

    def int_ret(self)-> list[Callable[[], None]]:
        def tick() -> None:
            self.pc_choice = (3).to_bytes(1, signed=False)
            self.__l_pc.perform()
            self.interception = 0
        return [tick]

    def tick(self) -> None:
        if self.stop:
            return
        if self.state == CUState.PreStart:
            #~(int_got | b_cv[0] | interception)
            #lambda: (1 & (1 ^ (int.from_bytes(self.__b_int_got.get_data()) | int.from_bytes(self.__b_cv_state.get_data()) | self.interception))).to_bytes(1))
            if int.from_bytes(self.__b_int_got.get_data()) != 0 and self.interception == 0:
                self.interception = 1
                self.__l_ra.perform()
                self.pc_choice = (5).to_bytes(1, signed=False)
                self.__l_pc.perform()
                return

            if not self.cmd_read:
                self.__l_cdata.perform()
                self.cmd_read = True

            cv_state = int.from_bytes(self.__b_cv_state.get_data())
            if cv_state != 0:
                if self.additional_tick:
                    state = cv_state >> 1
                    if state == 1:
                        self.__l_vcu1.perform()
                    elif state == 2:
                        self.__l_vcu2.perform()
                    elif state == 3:
                        self.__l_vcu3.perform()
                    elif state == 4:
                        self.__l_vcu4.perform()
                    self.additional_tick = False
                    self.state = CUState.Start
                else:
                    self.__l_vcu1.perform()
                    self.__l_vcu2.perform()
                    self.__l_vcu3.perform()
                    self.__l_vcu4.perform()
                    if cv_state >> 1 != 0:
                        self.additional_tick = True
                        self.state = CUState.PreStart
            else:
                self.state = CUState.Start

        elif self.state == CUState.Start:
            self.__l_cr.perform()
            command = int.from_bytes(self.__b_cmd.get_data()[0:1])
            cv_state = int.from_bytes(self.__b_cv_state.get_data())
            cmd_pref = (command & 0xC0) >> 6
            cmd_last = command & 0x3F

            if command == 0:
                self.pc_choice = (2).to_bytes(1, signed=False)
                self.__l_pc.perform()
                self.cmd_read = False
                return

            if (cmd_pref != 3 and cv_state != 0) or (command & 0xF0 == 0xF0 and cv_state >> 1 in (1, 2, 3)):
                self.cv_nxt = (0).to_bytes(1)
                self.__l_cv.perform()
                self.state = CUState.PreStart
                return

            if cmd_pref == 0:
                self.pc_choice = (2).to_bytes(1, signed=False)
                self.__l_pc.perform()
                if cmd_last == 1:
                    self.put_to_ticks(self.inc())
                elif cmd_last == 2:
                    self.put_to_ticks(self.dec())
                elif cmd_last == 3:
                    self.put_to_ticks(self.inc4())
                elif cmd_last == 4:
                    self.put_to_ticks(self.dec4())
                elif cmd_last == 5:
                    self.put_to_ticks(self.inv())
                elif cmd_last == 6:
                    self.put_to_ticks(self.neg())
                elif cmd_last == 7:
                    self.put_to_ticks(self.halt())
                elif cmd_last == 8:
                    self.put_to_ticks(self.int_ret())
            elif cmd_pref == 1:
                self.pc_choice = (0).to_bytes(1, signed=False)
                self.__l_pc.perform()
                cmd_last = command & 0x1F
                cmd_mode = (command & 0x20) >> 5
                if cmd_mode == 0:
                    self.cr_choice = (1).to_bytes(1, signed=False)
                    if cmd_last == 0x0:
                        self.put_to_ticks(self.ld_imm())
                    elif cmd_last == 0x1:
                        self.put_to_ticks(self.add_imm())
                    elif cmd_last == 0x2:
                        self.put_to_ticks(self.sub_imm())
                    elif cmd_last == 0x3:
                        self.put_to_ticks(self.and_imm())
                    elif cmd_last == 0x4:
                        self.put_to_ticks(self.or_imm())
                    elif cmd_last == 0x5:
                        self.put_to_ticks(self.xor_imm())
                    elif cmd_last == 0x6:
                        self.put_to_ticks(self.shiftl_imm())
                    elif cmd_last == 0x7:
                        self.put_to_ticks(self.shiftr_imm())
                    elif cmd_last == 0x8:
                        self.put_to_ticks(self.mul_imm())
                    elif cmd_last == 0x9:
                        self.put_to_ticks(self.div_imm())
                    elif cmd_last == 0xa:
                        self.put_to_ticks(self.rem_imm())
                    elif cmd_last == 0xb:
                        self.put_to_ticks(self.jump())
                    elif cmd_last == 0xc:
                        self.put_to_ticks(self.jz())
                    elif cmd_last == 0xd:
                        self.put_to_ticks(self.jnz())
                    elif cmd_last == 0xe:
                        self.put_to_ticks(self.jgt())
                    elif cmd_last == 0xf:
                        self.put_to_ticks(self.jlt())
                    elif cmd_last == 0x10:
                        self.put_to_ticks(self.jc())
                    elif cmd_last == 0x11:
                        self.put_to_ticks(self.jnc())
                    elif cmd_last == 0x12:
                        self.put_to_ticks(self.jv())
                    elif cmd_last == 0x13:
                        self.put_to_ticks(self.jnv())
                elif cmd_mode == 1:
                    self.cr_choice = (1).to_bytes(1, signed=False)
                    self.alu_choice = (0).to_bytes(1, signed=False)
                    self.alu_op = (0b00001000).to_bytes(1, signed=False)
                    self.__l_ar.perform()
                    if cmd_last == 0x0:
                        self.put_to_ticks(self.ld_addr())
                    if cmd_last == 0x1:
                        self.put_to_ticks(self.add_addr())
                    if cmd_last == 0x2:
                        self.put_to_ticks(self.sub_addr())
                    if cmd_last == 0x3:
                        self.put_to_ticks(self.and_addr())
                    if cmd_last == 0x4:
                        self.put_to_ticks(self.or_addr())
                    if cmd_last == 0x5:
                        self.put_to_ticks(self.xor_addr())
                    if cmd_last == 0x6:
                        self.put_to_ticks(self.shiftl_addr())
                    if cmd_last == 0x7:
                        self.put_to_ticks(self.shiftr_addr())
                    if cmd_last == 0x8:
                        self.put_to_ticks(self.mul_addr())
                    if cmd_last == 0x9:
                        self.put_to_ticks(self.div_addr())
                    if cmd_last == 0x0a:
                        self.put_to_ticks(self.rem_addr())
                    elif cmd_last == 0x0b:
                        self.put_to_ticks(self.st_addr())
                    elif cmd_last == 0x0c:
                        self.put_to_ticks(self.ld_ind())
                    elif cmd_last == 0x0d:
                        self.put_to_ticks(self.st_ind())
                    elif cmd_last == 0x0e:
                        self.put_to_ticks(self.in_port())
                    elif cmd_last == 0x0f:
                        self.put_to_ticks(self.out_port())
            elif cmd_pref == 2:
                self.pc_choice = (1).to_bytes(1, signed=False)
                self.__l_pc.perform()
                self.cr_choice = (0).to_bytes(1, signed=False)
                if cmd_last == 0x00:
                    self.put_to_ticks(self.jz())
                elif cmd_last == 0x01:
                    self.put_to_ticks(self.jnz())
                elif cmd_last == 0x02:
                    self.put_to_ticks(self.jgt())
                elif cmd_last == 0x03:
                    self.put_to_ticks(self.jlt())
                elif cmd_last == 0x04:
                    self.put_to_ticks(self.jc())
                elif cmd_last == 0x05:
                    self.put_to_ticks(self.jnc())
                elif cmd_last == 0x06:
                    self.put_to_ticks(self.jv())
                elif cmd_last == 0x07:
                    self.put_to_ticks(self.jnv())
                elif cmd_last == 0x08:
                    self.put_to_ticks(self.jump())
            elif cmd_pref == 3:
                if command & 0xF0 == 0xF0:
                    self.pc_choice = (0).to_bytes(1, signed=False)
                    self.__l_pc.perform()
                    self.cr_choice = (1).to_bytes(1, signed=False)
                    self.__l_var.perform()
                    if command == 0xF0:
                        self.cv_nxt = (0x80).to_bytes(1)

                    elif command == 0xF1:
                        self.cv_nxt = (0x81).to_bytes(1)

                    elif command == 0xF2:
                        self.cv_nxt = (0x82).to_bytes(1)

                    elif command == 0xF3:
                        self.cv_nxt = (0x83).to_bytes(1)

                    elif command == 0xF4:
                        self.cv_nxt = (0x84).to_bytes(1)

                    elif command == 0xF5:
                        self.cv_nxt = (0x85).to_bytes(1)

                else:
                    self.pc_choice = (2).to_bytes(1, signed=False)
                    self.__l_pc.perform()

                    if command == 0xD0:
                        self.cv_nxt = (0x10).to_bytes(1)

                    elif command == 0xD1:
                        self.cv_nxt = (0x11).to_bytes(1)

                    elif command == 0xD2:
                        self.cv_nxt = (0x12).to_bytes(1)

                    elif command == 0xD3:
                        self.cv_nxt = (0x13).to_bytes(1)

                    elif command == 0xC1:
                        self.cv_nxt = (0x01).to_bytes(1)

                    elif command == 0xC2:
                        self.cv_nxt = (0x02).to_bytes(1)

                    elif command == 0xCA:
                        self.cv_nxt = (0x0A).to_bytes(1)

                self.__l_cv.perform()
                self.cmd_read = False
                self.state = CUState.PreStart
                return

            self.cmd_read = False
            self.state = CUState.Run

        elif self.state == CUState.Run:
            self.ticks.get(block=False)()
            if self.ticks.empty():
                self.state = CUState.PreStart

class ImmediateValue:
    def __init__(self, bus_out:DataBus, value: bytes):
        val = bytes(value)
        bus_out.bind_provider(lambda: val)

class FourPartRegister:
    def __init__(self, b_in_1: DataBus,
                 b_in_2: DataBus,
                 b_in_3: DataBus,
                 b_in_4: DataBus,
                 b_out_1: DataBus,
                 b_out_2: DataBus,
                 b_out_3: DataBus,
                 b_out_4: DataBus,
                 size: int):
        self.reg1 = Register(b_in_1, b_out_1, size)
        self.reg2 = Register(b_in_2, b_out_2, size)
        self.reg3 = Register(b_in_3, b_out_3, size)
        self.reg4 = Register(b_in_4, b_out_4, size)

    def get_control_latch_1(self) -> Latch:
        return self.reg1.get_control_latch()

    def get_control_latch_2(self) -> Latch:
        return self.reg2.get_control_latch()

    def get_control_latch_3(self) -> Latch:
        return self.reg3.get_control_latch()

    def get_control_latch_4(self) -> Latch:
        return self.reg4.get_control_latch()

class VectorStateLogic:
    def __init__(self, b_in: DataBus, b_out: DataBus):
        self.__b_in = b_in
        b_out.bind_provider(self.perform)

    def perform(self) -> bytes:
        data = int.from_bytes(self.__b_in.get_data())
        first = 0
        second = 0
        if data != 0:
            first = 1

        if data & 0x80 != 0:
            second = 1
        elif data & 0x8000 != 0:
            second = 2
        elif data & 0x800000 != 0:
            second = 3
        elif data & 0x80000000 != 0:
            second = 4


        return (first + (second << 1)).to_bytes(1)

class SimpleExtender:
    def __init__(self, b_in: DataBus, b_out: DataBus, size_to: int):
        b_out.bind_provider(lambda: int.from_bytes(b_in.get_data()).to_bytes(size_to))


class VectorControlUnit:
    def __init__(self,
                 b_cv_part: DataBus,
                 b_alu_inp1_choice: DataBus,
                 b_alu_inp2_choice: DataBus,
                 b_alu_op_vec: DataBus,
                 b_alu_out_choice: DataBus,
                 b_data_op: DataBus,
                 l_data: Latch,
                 l_vec1: Latch,
                 l_vec2: Latch,
                 l_vec3: Latch):

        self.__b_cv_part = b_cv_part
        self.__b_alu_inp1_choice = b_alu_inp1_choice
        self.__b_alu_inp2_choice = b_alu_inp2_choice
        self.__b_alu_op_vec = b_alu_op_vec
        self.__b_alu_out_choice = b_alu_out_choice
        self.__b_data_op = b_data_op

        self.inp1_choice = (0).to_bytes(1)
        self.inp2_choice = (0).to_bytes(1)
        self.out_choice = (0).to_bytes(1)
        self.alu_op_vec = (0).to_bytes(1)
        self.data_op = (0).to_bytes(1)

        self.__b_alu_inp1_choice.bind_provider(lambda: self.inp1_choice)
        self.__b_alu_inp2_choice.bind_provider(lambda: self.inp2_choice)
        self.__b_alu_out_choice.bind_provider(lambda: self.out_choice)
        self.__b_alu_op_vec.bind_provider(lambda: self.alu_op_vec)
        self.__b_data_op.bind_provider(lambda: self.data_op)


        self.__l_data = l_data
        self.__l_vec1 = l_vec1
        self.__l_vec2 = l_vec2
        self.__l_vec3 = l_vec3

        self.tick2 = False

    def tick(self):
        cmd = int.from_bytes(self.__b_cv_part.get_data())
        if cmd & 0x80:
            if cmd in (0x80, 0x81, 0x82):
                if not self.tick2:
                    self.data_op = (0).to_bytes(1)
                    self.__l_data.perform()
                    self.tick2 = True
                else:
                    self.alu_op_vec = (8).to_bytes(1)
                    self.inp2_choice = (3).to_bytes(1)
                    self.out_choice = (1).to_bytes(1)
                    if cmd == 0x80:
                        self.__l_vec1.perform()
                    elif cmd == 0x81:
                        self.__l_vec2.perform()
                    elif cmd == 0x82:
                        self.__l_vec3.perform()
                    self.tick2 = False

            elif cmd in (0x83, 0x84, 0x85):
                self.data_op = (1).to_bytes(1)
                self.alu_op_vec = (8).to_bytes(1)
                if cmd == 0x83:
                    self.inp2_choice = (2).to_bytes(1)
                elif cmd == 0x84:
                    self.inp2_choice = (1).to_bytes(1)
                elif cmd == 0x85:
                    self.inp2_choice = (0).to_bytes(1)
                self.out_choice = (1).to_bytes(1)
                self.__l_data.perform()

        else:
            if cmd in (0x10, 0x11, 0x12, 0x13):
                self.inp1_choice = (2).to_bytes(1)
                self.inp2_choice = (1).to_bytes(1)
                if cmd == 0x10:
                    self.alu_op_vec = (0).to_bytes(1)
                elif cmd == 0x11:
                    self.alu_op_vec = (1).to_bytes(1)
                elif cmd == 0x12:
                    self.alu_op_vec = (5).to_bytes(1)
                elif cmd == 0x13:
                    self.alu_op_vec = (4).to_bytes(1)

                self.out_choice = (1).to_bytes(1)
                self.__l_vec3.perform()

            elif cmd in (0x01, 0x02):
                self.inp2_choice = (0).to_bytes(1)
                self.alu_op_vec = (8).to_bytes(1)
                self.out_choice = (1).to_bytes(1)
                if cmd == 0x01:
                    self.__l_vec1.perform()
                elif cmd == 0x02:
                    self.__l_vec2.perform()

            elif cmd in (0x0a,):
                self.inp2_choice = (0).to_bytes(1)
                self.alu_op_vec = (8).to_bytes(1)
                self.out_choice = (0).to_bytes(1)
                self.__l_vec3.perform()

    def get_control_latch(self) -> Latch:
        return Latch(self.tick)















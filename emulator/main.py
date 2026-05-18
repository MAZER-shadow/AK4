import sys
import json
from cpu.modules import MainDataPath, MainControlUnit
from cpu.utils import SharedMemory
from cpu.modules import ExtensionModule

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: main.py <source path> <config>")
        sys.exit(1)

    with open(sys.argv[1] + '.cmem', 'rb') as f:
        cmem_read = f.read()

    with open(sys.argv[1] + '.mem', 'rb') as f:
        mem_read = f.read()

    with open(sys.argv[2], 'r') as f:
        params = json.loads(f.read())

    mem_size = 32768
    if 'mem_size' in params:
        if type(params['mem_size']) != int:
            raise TypeError("Memory size must be an integer")
        mem_size = params['mem_size']

    tick_cnt = 1000
    if 'tick_cnt' in params:
        if type(params['mem_size']) != int:
            raise TypeError("Tick count must be an integer")
        tick_cnt = params['tick_cnt']

    report = "ac: {ac} ar: {ar} pc: {pc} cr: {cr} flags: {flg}"
    if 'report' in params:
        if type(params['report']) != str:
            raise TypeError("Field report must be a string value")
        report = params['report']

    res_type = "hex"
    if 'res' in params:
        if type(params['res']) != str:
            raise TypeError("Field res must be a string value")
        res_type = params['res']

    if res_type == 'hex':
        res_to_str = lambda x, y: str(x.hex())+" "
    elif res_type == 'str':
        res_to_str = lambda x, y: str(chr(x[-1])) if x [-1] != 0 else "\\0"
    elif res_type == 'full':
        res_to_str = lambda x, y: str(y)+": "+str(x.hex()) + "  "
    elif res_type == 'dec':
        res_to_str = lambda x, y: str(int.from_bytes(x, signed=True))+" "
    else:
        raise TypeError("Unknown res type")
    mem = SharedMemory(mem_size)
    cmem = SharedMemory(mem_size)
    mem.load_to_mem([list(mem_read)])
    cmem.load_to_mem([list(cmem_read)])

    dp = MainDataPath(mem)
    vex = ExtensionModule(mem, dp.b_cr_arg)
    cu = MainControlUnit(dp, vex, cmem)
    full_res = ""
    for i in range(tick_cnt):
        if cu.id.stop:
            break
        inp = None
        if 'input' in params and params['input']:
            if str(i) in params['input']:
                el = params['input'][str(i)]
                if type(el) != str:
                    raise TypeError("Input must be a string value")
                if el[0:2] == '0x':
                    inp = bytes.fromhex(el[2:])
                elif el.isdigit() or el[0] == '-' and el[1:].isdigit():
                    inp = int(el).to_bytes(4, signed=True)
                elif len(el) == 1:
                    inp = ord(el).to_bytes(4, signed=True)
                else:
                    raise TypeError(f"Invalid input data for timestamp: {str(i)}")
        dp.ex1.cu.post_data(inp)
        cu.id.tick()
        res = dp.ex2.cu.get_data()
        if res is not None:
            full_res += res_to_str(res, i)
        print(report
              .replace('{ac}', str(dp.b_alu_ac.get_data().hex()))
              .replace('{ar}', str(dp.b_ar.get_data().hex()))
              .replace('{pc}', str(cu.b_pc.get_data().hex()))
              .replace('{cr}', str(cu.b_cmd.get_data().hex()))
              .replace('{flg}', str(dp.b_flg.get_data().hex()))
              .replace('{cv}', str(vex.b_cv.get_data().hex()))
              .replace('{tick}', str(i+1))
              )
        #print(str(vex.b_vec1_1.get_data().hex())+" "+str(vex.b_vec1_2.get_data().hex())+" "+str(vex.b_vec1_3.get_data().hex())+" "+str(vex.b_vec1_4.get_data().hex()))
        #print(str(vex.b_vec2_1.get_data().hex())+" "+str(vex.b_vec2_2.get_data().hex())+" "+str(vex.b_vec2_3.get_data().hex())+" "+str(vex.b_vec2_4.get_data().hex()))
        #print(str(vex.b_vec3_1.get_data().hex())+" "+str(vex.b_vec3_2.get_data().hex())+" "+str(vex.b_vec3_3.get_data().hex())+" "+str(vex.b_vec3_4.get_data().hex()))

    print(full_res)
    if 'assert' in params:
        if type(params['assert']) != str:
            raise TypeError("Field assert must be a string value")

        if params['assert'] != full_res:
            raise AssertionError('Assertion failed. Expected: ' + params['assert'] + ' Got: ' + full_res)

        print("Assertion passed")
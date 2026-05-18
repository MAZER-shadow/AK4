import sys

from parser import Parser

if __name__ == '__main__':
    if len(sys.argv) not in (2,3):
        print("Usage: main.py <source file> [memory_limit]")
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:

        (cmem, mem, rep_data, rep_cmd) = Parser.parse_asm(Parser.preprocessor(f.read()))

    name = sys.argv[1].rsplit('.')[0]
    mem_size = 32768

    if len(sys.argv) == 3:
        try:
            mem_size = int(sys.argv[2])
        except ValueError:
            print("Unable to parse memory limit, it should be an integer")
            sys.exit(1)

    with open(name+'.cmem', 'wb') as f:
        write_cmem = bytearray(mem_size)
        for addr in cmem:
            write_cmem[addr] = cmem[addr]
        f.write(write_cmem)

    with open(name+'.mem', 'wb') as f:
        write_mem = bytearray(mem_size)
        for addr in mem:
            write_mem[addr] = mem[addr]
        f.write(write_mem)

    with open(name+'.dreport', 'w') as f:
        f.write(rep_data)

    with open(name+'.creport', 'w') as f:
        f.write(rep_cmd)

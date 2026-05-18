import yaml
import sys
import subprocess
import os
if __name__ == '__main__':
    if len(sys.argv) not in (2,):
        print("Usage: golden_runner.py <test file>")
        sys.exit(1)

    name = sys.argv[1]
    with open(name+".yaml", 'r') as f:
        loaded = yaml.safe_load(f)

    with open(name+'.asm', 'w') as f:
        f.write(loaded["code"])

    with open(name+'.json', 'w') as f:
        f.write(loaded["config"])

    subprocess.run(["python", "compiler/main.py", name+".asm"])
    if "assert_cmem" in loaded:
        with open(name+'.creport', 'r') as f:
            assert loaded["assert_cmem"].strip() == f.read().strip()
            print("cmem assertion passed")

    if "assert_mem" in loaded:
        with open(name+'.dreport', 'r') as f:
            assert loaded["assert_mem"].strip() == f.read().strip()
            print("mem assertion passed")

    emulation_res = subprocess.run(["python", "emulator/main.py", name, name + ".json"], capture_output = True, text = True)
    assert emulation_res.returncode == 0

    if "assert_report" in loaded:
        assert loaded["assert_report"].strip() == emulation_res.stdout.strip()
        print("report assertion passed")

    os.remove(name+".asm")
    os.remove(name+".json")
    os.remove(name+".creport")
    os.remove(name+".dreport")
    os.remove(name+".cmem")
    os.remove(name+".mem")
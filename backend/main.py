import file_parser as fp
import global_vars as gv
import server as s
import asyncio
import time

fp.read_bin_file("output.bin")

result = asyncio.run(s.read_root())
print(result)
time.sleep(1)

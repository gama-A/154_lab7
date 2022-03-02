# from socket import RDS_CANCEL_SENT_TO
from cProfile import label
from turtle import rt
# import rsa
import pyrtl

i_mem = pyrtl.MemBlock(bitwidth=32, addrwidth=32, name='i_mem', max_read_ports=1)
d_mem = pyrtl.MemBlock(bitwidth=32, addrwidth=32, name='d_mem', max_read_ports=1, max_write_ports=1, asynchronous=True)
rf    = pyrtl.MemBlock(bitwidth=32, addrwidth=5, name='rf', max_read_ports=2, max_write_ports=1, asynchronous=True)

counter = pyrtl.Register(bitwidth=32, name='counter')
instr = pyrtl.WireVector(bitwidth=32, name='instr')

instr <<= i_mem[counter]

op = pyrtl.WireVector(bitwidth=6, name='op')
rs = pyrtl.WireVector(bitwidth=5, name='rs')
rt = pyrtl.WireVector(bitwidth=5, name='rt')
rd = pyrtl.WireVector(bitwidth=5, name='rd')
sh = pyrtl.WireVector(bitwidth=5, name='sh')
funct = pyrtl.WireVector(bitwidth=6, name='funct')
imm = pyrtl.WireVector(bitwidth=16, name='imm')
address = pyrtl.WireVector(bitwidth=32, name='address')

alu_out = pyrtl.WireVector(bitwidth=32, name='alu_out')
alu_zero = pyrtl.WireVector(bitwidth=1, name='alu_zero')
data0 = pyrtl.WireVector(bitwidth=32, name='data0')
data1 = pyrtl.WireVector(bitwidth=32, name='data1')

op <<= instr[26:32]
rs <<= instr[21:26]
rt <<= instr[16:21]
rd <<= instr[11:16]
sh <<= instr[6:11]
funct <<= instr[0:6]
imm <<= instr[0:16]

control_signals = pyrtl.WireVector(bitwidth=12, name='control')

with pyrtl.conditional_assignment:
   with op == 0:
      with funct == 0x20:
         control_signals |= 0x280
      with funct == 0x24:
         control_signals |= 0x281
      with funct == 0x2a:
         control_signals |= 0x284
   with op == 0x8:
      control_signals |= 0x0a0
   with op == 0xf:
      control_signals |= 0x0a5
   with op == 0x23:
      control_signals |= 0x2a8
   with op == 0x2b:
      control_signals |= 0x0b0
   with op == 0x4:
      control_signals |= 0x123

alu_op = control_signals[0:3]
mem_to_reg = control_signals[3:4]
mem_write = control_signals[4:5]
alu_src = control_signals[5:7]
regWrite = control_signals[7:8]
branch = control_signals[8:9]
reg_dst = control_signals[9:10]

regDest = pyrtl.WireVector(bitwidth=5, name='regDest')

with pyrtl.conditional_assignment:
   with reg_dst == 0:
      regDest |= rt
   with reg_dst == 1:
      regDest |= rd

data0 <<= rf[rs]
data1 <<= rf[regDest]

with pyrtl.conditional_assignment:
   with alu_src == 0:
      data1 |= data1
   with alu_src == 1:
      with branch == 1:
         data1 |= data1
         address |= imm.sign_extended(32)
      with branch == 0:
         data1 |= imm.sign_extended(32)
   with alu_src == 2:
      data1 |= imm.zero_extended(32)

with pyrtl.conditional_assignment:
   with alu_op == 0:
      alu_out |= data0 + data1
   with alu_op == 1:
      alu_out |= data0 & data1
   with alu_op == 2:
      alu_out |= data0 | data1
   with alu_op == 3:
      alu_out |= data0 - data1
      alu_zero |= alu_out == 0
   with alu_op == 4:
      alu_out |= data1 < data0
   with alu_op == 5:
      alu_out |= pyrtl.shift_left_logical(data1, sh)


with pyrtl.conditional_assignment:
   with branch == 1:
      with alu_zero == 1:
         counter.next |= counter + address + 1
      with alu_zero == 0:
         counter.next |= counter + 1
   with branch == 0:
      counter.next |= counter + 1

WE = pyrtl.MemBlock.EnabledWrite
rf[regDest] <<= WE(alu_out, regWrite)
d_mem[regDest] <<= WE(alu_out, mem_write)

if __name__ == '__main__':

    """

    Here is how you can test your code.
    This is very similar to how the autograder will test your code too.

    1. Write a MIPS program. It can do anything as long as it tests the
       instructions you want to test.

    2. Assemble your MIPS program to convert it to machine code. Save
       this machine code to the "i_mem_init.txt" file.
       You do NOT want to use QtSPIM for this because QtSPIM sometimes
       assembles with errors. One assembler you can use is the following:

       https://alanhogan.com/asu/assembler.php

    3. Initialize your i_mem (instruction memory).

    4. Run your simulation for N cycles. Your program may run for an unknown
       number of cycles, so you may want to pick a large number for N so you
       can be sure that the program has "finished" its business logic.

    5. Test the values in the register file and memory to make sure they are
       what you expect them to be.

    6. (Optional) Debug. If your code didn't produce the values you thought
       they should, then you may want to call sim.render_trace() on a small
       number of cycles to see what's wrong. You can also inspect the memory
       and register file after every cycle if you wish.

    Some debugging tips:

        - Make sure your assembly program does what you think it does! You
          might want to run it in a simulator somewhere else (SPIM, etc)
          before debugging your PyRTL code.

        - Test incrementally. If your code doesn't work on the first try,
          test each instruction one at a time.

        - Make use of the render_trace() functionality. You can use this to
          print all named wires and registers, which is extremely helpful
          for knowing when values are wrong.

        - Test only a few cycles at a time. This way, you don't have a huge
          500 cycle trace to go through!

    """

    # Start a simulation trace
    sim_trace = pyrtl.SimulationTrace()

    # Initialize the i_mem with your instructions.
    i_mem_init = {}
    with open('i_mem_init.txt', 'r') as fin:
        i = 0
        for line in fin.readlines():
            i_mem_init[i] = int(line, 16)
            i += 1

    sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map={
        i_mem : i_mem_init
    })

    # Run for an arbitrarily large number of cycles.
    for cycle in range(500):
        sim.step({})

    # Use render_trace() to debug if your code doesn't work.
    # sim_trace.render_trace()

    # You can also print out the register file or memory like so if you want to debug:
    # print(sim.inspect_mem(d_mem))
    # print(sim.inspect_mem(rf))

    # Perform some sanity checks to see if your program worked correctly
    assert(sim.inspect_mem(d_mem)[0] == 10)
    assert(sim.inspect_mem(rf)[8] == 10)    # $v0 = rf[8]
    print('Passed!')

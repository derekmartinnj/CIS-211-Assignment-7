"""
Derek Martin
CIS 211

Duck Machine model DM2019W CPU
"""

from instr_format import Instruction, OpCode, CondFlag, decode
from typing import Tuple
from memory import Memory
from register import Register, ZeroRegister
from mvc import MVCEvent, MVCListenable
import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)



class ALU(object):
    """The arithmetic logic unit (also called a "functional unit"
    in a modern CPU) executes a selected function but does not
    otherwise manage CPU state. A modern CPU core may have several
    ALUs to boost performance by performing multiple operatons
    in parallel, but the Duck Machine has just one ALU in one core.
    """
    # The ALU chooses one operation to apply based on a provided
    # operation code.  These are just simple functions of two arguments;
    # in hardware we would use a multiplexer circuit to connect the
    # inputs and output to the selected circuitry for each operation.
    ALU_OPS = {
        OpCode.ADD: lambda x, y: x + y,
        OpCode.SUB: lambda x, y: x - y,
        OpCode.MUL: lambda x, y: x * y,
        OpCode.DIV: lambda x, y: x // y,
        # For memory access operations load, store, the ALU
        # performs the address calculation
        OpCode.LOAD: lambda x, y: x + y,
        OpCode.STORE: lambda x, y: x + y,
        # Some operations perform no operation
        OpCode.HALT: lambda x, y: 0
    }

    def exec(self, op: OpCode, in1: int, in2: int) -> Tuple[int, CondFlag]:
        try:
            result = self.ALU_OPS[op](in1, in2)
            if result < 0:
                return result, CondFlag.M
            elif result == 0:
                return result, CondFlag.Z
            elif result > 0:
                return result, CondFlag.P
        except:
            return 0, CondFlag.V



class CPUStep(MVCEvent):
    """CPU is beginning step with PC at a given address"""
    def __init__(self, subject: "CPU", pc_addr: int,
                 instr_word: int, instr: Instruction)-> None:
        self.subject = subject
        self.pc_addr = pc_addr
        self.instr_word = instr_word
        self.instr = instr



class CPU(MVCListenable):
    """Duck Machine central processing unit (CPU)
    has 16 registers (including r0 that always holds zero
    and r15 that holds the program counter), a few
    flag registers (condition codes, halted state),
    and some logic for sequencing execution.  The CPU
    does not contain the main memory but has a bus connecting
    it to a separate memory.
    """
    def __init__(self, memory: Memory):
        super().__init__()
        self.memory = memory  # Not part of CPU; what we really have is a connection
        self.registers = [ZeroRegister(), Register(), Register(), Register(),
                          Register(), Register(), Register(), Register(),
                          Register(), Register(), Register(), Register(),
                          Register(), Register(), Register(), Register()]
        self.pc = self.registers[15]
        self.condition = CondFlag.ALWAYS
        self.halted = False
        self.alu = ALU()

    def step(self):
        # Fetch
        counter = self.pc.get()
        instr_word = self.memory.get(counter)

        # Decode
        instr = decode(instr_word)
        # Display the CPU state when we have decoded the instruction,
        # before we have executed it
        self.notify_all(CPUStep(self, counter, instr_word, instr))

        # Execute
        pre_satisfied = (self.condition & instr.cond)
        if pre_satisfied:

            left_index = instr.reg_src1
            left_op = self.registers[left_index].get()
            right_index = instr.reg_src2
            right_op = (self.registers[right_index].get() + instr.offset)

            result_val, cond_code = self.alu.exec(instr.op, left_op, right_op)

            counter += 1
            self.pc.put(counter)

            if instr.op == OpCode.STORE:  # STORE
                self.memory.put(result_val, self.registers[instr.reg_target].get())
            if instr.op == OpCode.LOAD:  # LOAD
                self.registers[instr.reg_target].put(self.memory.get(result_val))
            if instr.op == OpCode.HALT:  # HALT
                self.halted = True
            if (instr.op == OpCode.ADD) or (instr.op == OpCode.SUB) or (instr.op == OpCode.MUL) or (instr.op == OpCode.DIV):
                self.registers[instr.reg_target].put(result_val)
                self.condition = cond_code
        else:
            counter += 1
            self.pc.put(counter)

    def run(self, from_addr=0, single_step=False) -> None:
        self.halted = False
        self.pc.put(from_addr)
        step_count = 0
        while not self.halted:
            if single_step:
                input("Step {}; press enter".format(step_count))
            self.step()
            step_count += 1

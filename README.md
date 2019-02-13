# Fault
[![Build Status](https://travis-ci.com/leonardt/fault.svg?branch=master)](https://travis-ci.com/leonardt/fault)
[![Coverage Status](https://coveralls.io/repos/github/leonardt/fault/badge.svg?branch=master)](https://coveralls.io/github/leonardt/fault?branch=master)

A Python package for testing hardware (part of the magma ecosystem).

[API Documentation](http://truong.io/fault/)

[CHANGELOG](./CHANGELOG.md)

## Example
Here is a simple ALU defined in magma.
```python
import magma as m
import mantle


class ConfigReg(m.Circuit):
    IO = ["D", m.In(m.Bits(2)), "Q", m.Out(m.Bits(2))] + \
        m.ClockInterface(has_ce=True)

    @classmethod
    def definition(io):
        reg = mantle.Register(2, has_ce=True, name="conf_reg")
        io.Q <= reg(io.D, CE=io.CE)


class SimpleALU(m.Circuit):
    IO = ["a", m.In(m.UInt(16)),
          "b", m.In(m.UInt(16)),
          "c", m.Out(m.UInt(16)),
          "config_data", m.In(m.Bits(2)),
          "config_en", m.In(m.Enable),
          ] + m.ClockInterface()

    @classmethod
    def definition(io):
        opcode = ConfigReg(name="config_reg")(io.config_data, CE=io.config_en)
        io.c <= mantle.mux(
            [io.a + io.b, io.a - io.b, io.a * io.b, io.a / io.b], opcode)
```

Here's an example test in fault that uses the configuration interface, expects
a value on the internal register, and checks the result of performing the
expected operation.

```python
import operator

ops = [operator.add, operator.sub, operator.mul, operator.div]
tester = fault.Tester(SimpleALU, SimpleALU.CLK)
tester.circuit.CLK = 0
tester.circuit.config_en = 1
for i in range(0, 4):
    tester.circuit.config_data = i
    tester.step(2)
    tester.circuit.a = 3
    tester.circuit.b = 2
    tester.eval()
    tester.circuit.c.expect(ops[i](3, 2))
```

We can run this with three different simulators

```python
tester.compile_and_run("verilator", flags=["-Wno-fatal"], directory="build")
tester.compile_and_run("system-verilog", simulator="ncsim", directory="build")
tester.compile_and_run("system-verilog", simulator="vcs", directory="build")
```

### Working with internal signals
Fault supports peeking, expecting, and printing internal signals. For the
`verilator` target, you should use the keyword argument `magma_opts` with
`"verilator_debug"` set to true.  This will cause coreir to compile the verilog
with the required debug comments.  Example:
```python
tester.compile_and_run("verilator", flags=["-Wno-fatal"], 
                       magma_opts={"verilator_debug": True}, directory="build")
```

If you're using `mantle.Register` from the `coreir` implementation, you can
also poke the internal register value directly using the `value` field.  Notice
that `conf_reg` is defined in `ConfigReg` to be an instance of
`mantle.Register` and the test bench pokes it by setting `confg_reg.value`
equal to `1`.

```python
tester = fault.Tester(SimpleALU, SimpleALU.CLK)
tester.circuit.CLK = 0
# Initialize
tester.step(2)
for i in reversed(range(4)):
    tester.circuit.config_reg.conf_reg.value = i
    tester.step(2)
    tester.circuit.config_reg.conf_reg.O.expect(i)
```

## FAQ

### How do I generate waveforms with fault?

Fault supports generating `.vcd` dumps when using the `verilator` and
`system-verilog/ncsim` target.

For the `verilator` target, use the `flags` keyword argument to pass the
`--trace` flag.  For example,

    tester.compile_and_run("verilator", flags=["-Wno-fatal", "--trace"])

The `--trace` flag must be passed through to verilator so it generates code
that supports waveform dumping. The test harness generated by fault will
include the required logic for invoking `tracer->dump(main_time)` for every
call to `eval` and `step`.  `main_time` is incremented for every call to step.
The output `.vcd` file will be saved in the file `logs/{circuit_name}` where
`circuit_name` is the name of the ciruit passed to `Tester`.  The `logs`
directory will be placed in the same directory as the generated harness, which
is controlled by the `directory` keyword argument (by default this is
`"build/"`).

For the `system-verilog/ncsim` target, tracing is enabled by default. For
`ncsim`, the trace will be placed in a file called `verilog.vcd` in the same
directory as the generated harness.

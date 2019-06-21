# Python Model of an Ordt generated Register File

This script parses the XML output from running Ordt and constructs a model of the register file
that allows reading/writing to the registers as well as setting host side signals such as interrupt
inputs.  The aim is to provide a Python model that can be used within a cocotb verification env.

At this stage there are significant limitations in the implementation as well as big gaps in testing.
I have only tested this with a simple single hierarchy of address map with none of the external access
options available in Ordt.  However, I hope to build upon this as I progress with my usage of Ordt
and am happy to accept input from others.

## Usage

The model is intended to be instanced from within your cocotb testbench.  However, there are some
simple command line options that allow familiarisation of the script.

## Running the script

`ordt_addrmap.py -h`

`ordt_addrmap.py --example` will print a bunch of output examples

`ordt_addrmap.py --get_irq_inputs` will list all the host side interrupt inputs
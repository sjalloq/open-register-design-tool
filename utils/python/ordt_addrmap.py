#!/usr/bin/env python

# Copyright (c) 2019, Shareef Jalloq
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import xml.etree.ElementTree as ET
import collections

from enum import Enum, auto

debug = False

def collimate(lst,delimiter):
    """Helper function for producing nicely aligned text output"""
    out    = []
    maxlen = [0] * len(lst[0].split(delimiter))

    for string in lst:
        for i,s in enumerate(string.split(delimiter)):
            maxlen[i] = max([len(s), maxlen[i]])
    for string in lst:
        out.append(' | '.join( [ s + ' ' * (maxlen[i] - len(s)) for i,s in enumerate(string.split(delimiter)) ] ) )
    return out

def flatten(l, ltypes=(list, tuple)):
    """Takes a list of lists and flattens it"""
    ltype = type(l)
    l = list(l)
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i:i + 1] = l[i]
        i += 1
    return ltype(l)

def to_rtl(path):
    """Modifies a path to look like the RTL net/register names"""
    return '_'.join(path.split('.'))

def divider(string):
    """Inserts a Verilog style divider into a string"""
    return '\n// ' + '-' * 70 + '\n// ' + string + '\n// ' + '-' * 70 + '\n'


class Error(Exception):
    pass

class UnknownHwInfoField(Error):
    """Should never happen, probably a new field that hasn't been seen previously"""
    def __init__(self, message):
        self.message = message

class UnknownChildTag(Error):
    """Should never happen, probably a new field that hasn't been seen previously"""
    def __init__(self, message):
        self.message = message
        
class UnknownRegsetElement(Error):
    """Should never happen, probably a new field that hasn't been seen previously"""
    def __init__(self, message):
        self.message = message

class UnknownRegElement(Error):
    """Should never happen, probably a new field that hasn't been seen previously"""
    def __init__(self, message):
        self.message = message

class UnknownFieldElement(Error):
    """Should never happen, probably a new field that hasn't been seen previously"""
    def __init__(self, message):
        self.message = message

class MissingFieldElement(Error):
    """Should never happen, probably a new field that hasn't been seen previously"""
    def __init__(self, message):
        self.message = message

class IllegalRegWrite(Error):
    """The user has performed a write to reserved/unused register fields"""
    def __init__(self, message):
        self.message = message

class IncorrectAddrType(Error):
    def __init__(self, message):
        self.message = message    

        
class Access(Enum):
    RW = 'RW'
    RO = 'RO'
    RC = 'RC'
    WO = 'WO'

    
class HwAccess(Enum):
    NA = 'na'
    R  = 'r'
    W  = 'w'
    RW = 'rw'

    
class ReadWriteAck(Enum):
    ACK = auto()
    NACK = auto()

    
class HwInfo(object):
    """Maps to the SystemRDL Field HwInfo property"""
    
    def __init__(self, elem):
        for e in elem:
            if e.tag == 'hwaccess':
                self.hwaccess = self._hwaccess(e.text)
            elif e.tag == "nextassign":
                self.nextassign = e.text
            elif e.tag == "we":
                self.we = e.text
            else:
                raise UnknownHwInfoField("Unexpected HwInfo.tag={}".format(e.tag))

    def _hwaccess(self, hwaccess):
        """Returns an enum from the input string"""
        return HwAccess(hwaccess)

    
class Intr(object):
    """Maps to the SystemRDL Field Interrupt property"""
    
    def __init__(self, elem):
        # Defaults
        self.input = None
        
        for e in elem:
            if e.tag == 'type':
                self.type = e.text
            elif e.tag == 'stickytype':
                self.stickytype = e.text
            elif e.tag == 'enable':
                self.enable = e.text
            elif e.tag == 'input':
                self.input = e.text
            else:
                raise UnknownFieldElement("Unexpected Intr.tag={}".format(e.tag))

    def to_s(self):
        """Return a string"""

        try:
            return 'irq_type={} irq_stickytype={} irq_enable={} irq_next={}'.format(
                self.type, self.stickytype, to_rtl(self.enable), self.input )
        except AttributeError:
            raise AttributeError("Intr::to_s() missing an attribute; add a default?")

        
class Signal(object):
    def __init__(self):
        pass


class Component(object):
    """RDL base class with some common methods"""
    def __init__(self, claas):
        self.claas = claas

    def isregfile(self):
        return self.claas == 'RegisterFile'
    
    def isreg(self):
        return self.claas == 'Register'

    def isfield(self):
        return self.claas == 'Field'

        
class Field(Component):
    """Maps to the SystemRDL Field component"""
    
    def __init__(self, args):
        Component.__init__(self, self.__class__.__name__)
        for k,v in args.items():
            setattr(self, k, v)
        self.value = int(self.reset)

    def isirq(self):
        return hasattr(self, 'intr')

    def isstickyirq(self):
        if hasattr(self, 'intr'):
            return self.intr.stickytype == 'STICKYBIT'
        else:
            return False

    def iswriteable(self):
        return (self.access in [access.RW, access.WO])

    def read(self):
        """ Return the field value shifted to its correct bit location in the word"""
        return  self.value << int(self.lowidx)
    
    def write(self, value):
        """Accepts an int and picks out the relevant field bits from the word"""
        self.value = (1 * int(self.width)) & (value >> int(self.lowidx))

    def to_s(self, verbosity=0):
        """Return a string

        Arguments:
          verbosity - the verbosity level from 0:low to 2:high"""
        string = 'field={} width={} offset={} value={} sw={} hw={} path={} '.format(
            self.id, self.width, self.lowidx, self.value, self.access, self.hwinfo.hwaccess, self.path)
        if verbosity > 0:
            string += self.intr.to_s()
        return string

    
class Register(Component):
    """Maps to the SystemRDL Register component"""
    
    def __init__(self, args):
        Component.__init__(self, self.__class__.__name__)
        for k,v in args.items():
            setattr(self, k, v)
        self.wmask = self._wmask(int(self.width))
        
    def __iter__(self):
        return iter(self.fields)

    def read(self):
        """Constructs the read data from each sub-field"""
        data = 0
        for f in self.fields:
            data |= f.read()
        return data
    
    def write(self, value):
        """Performas a write after checking against each field's write access"""
        if (value & ~self.wmask):
            raise IllegalRegWrite(
                "write to non-writeable fields: addr={} wmask={} wdata={}".format(
                    hex(self.baseaddr),hex(self.wmask),hex(value)))
        else:
            [f.write(value) for f in self.fields]

    def to_s(self, verbosity=0):
        """Return a string

        Arguments:
          verbosity - the verbosity level from 0:low to 2:high"""
        string = '\n'
        string += 'address={} name={} path={}'.format(self.baseaddr, self.id, self.path)
        for f in self.fields:
            string += f.to_s() 
        return string

    def _wmask(self, width):
        """Generate a bitwise write mask"""

        mask = 0
        for field in self.fields:
            if field.iswriteable:
                mask += (1 * int(field.width)) << int(field.lowidx)
        return mask
        

    
class RegisterFile(Component):
    """Maps to the SystemRDL Register File Component"""
    
    def __init__(self, args):
        Component.__init__(self, self.__class__.__name__)
        for k,v in args.items():
            setattr(self, k, v)
            
    def __iter__(self):
        return iter(self.registers)
    
    def to_s(self, verbosity=0):
        """Return a string

        Arguments:
          verbosity - the verbosity level from 0:low to 2:high"""
        return 'regset={}'.format(self.id)
        

class AddressMap(object):
    """Maps to the SystemRDL Address Map component"""
    
    def __init__(self, xmlfile):
        """Initialises the top level register file

        Arguments:
          xmlfile - the full path to the XML file to parse"""
        self.root       = ET.parse(xmlfile).getroot()
        self.id         = self.root.find('id').text
        self.baseaddr   = self.root.find('baseaddr').text
        self.registers  = []
        self.addressmap = {}
        self.pathmap    = {}
        self.interrupts = {}
        self._parse()
        self._addressmap(self.registers)
        self._pathmap(self.registers)
        self._interrupts(self.registers)

    def read(self, addr, verbosity=0):
        try:
            reg = self.get_reg_by_address(addr)
            rdata = reg.read()
            if verbosity > 0: print('AddressMap::read() : addr={} rdata={}'.format(addr,rdata))
            return [ReadWriteAck.ACK, rdata]
        except KeyError:
            print("WARN: read to address {} doesn't exist".format(hex(addr)))
            return [ReadWriteAck.NACK, 0]
        
    def write(self, addr, value, verbosity=0):
        try:
            reg = self.get_reg_by_address(addr)
            if verbosity > 0: print("AddressMap::write() : addr={} wdata={}".format(addr,value))
            return [ReadWriteAck.ACK, reg.write(value)]
        except KeyError:
            print("WARN: write to address {} doesn't exist".format(hex(addr)))
            return ReadWriteAck.NACK
        except IllegalRegWrite as err:
            print(err)
            return ReadWriteAck.ACK

    def get_address_by_field(self, field):
        """Returns a list of addresses given a full or partial path name"""

        return [v.baseaddr for k,v in self.pathmap.items() if (field in k and v.isfield())]
        
    def get_address_by_reg(self, reg, verbosity=0):
        """Returns a list of addresses given a full or partial path name"""

        addr = []
        for k,v in self.pathmap.items():
            if (reg in k and v.isreg()):
                if verbosity == 0:
                    addr += v.baseaddr
                else:
                    addr += [ v.baseaddr, v.path ]
        return addr
    
    def get_reg_by_address(self, addr):
        """Returns the path of a register given an integer address"""

        if not addr.__class__ is int:
            raise IncorrectAddrType(
                "get_reg_by_address(addr) called with wrong type: value={} type={}".format(
                    addr, addr.__class__.__name__))
        else:
            return self.addressmap[addr]

    def get_irqs(self):
        """Returns a list of all interrupt registers"""
        return [f for f in self._fields() if f.isirq()]

    def get_sticky_irqs(self):
        """Returns a list of all the sticky interrupts; these are associated with the external IRQ inputs from the host"""
        return [f for f in self._fields() if f.isstickyirq()]

    def get_rtl_irq_inputs(self):
        """Returns a list of the host interrupt nets"""
        return list(map(lambda f: { 'wire': 'h2l_' + f.path + '_intr', 'field': f }, self.get_sticky_irqs()))

    def get_irq_by_path(self, path):
        """Returns the Field component for a given interrupt

        Arguments:
          path - a full or partial hierarchical path to a field"""

        return [v for k,v in self.interrupts.items() if path in k]
    
    def to_s(self):
        """Return a string

        Arguments:
          verbosity - the verbosity level from 0:low to 2:high"""
        od = collections.OrderedDict(sorted(self.addressmap.items()))
        for addr,reg in od.items():
            print(reg.to_s())
            
    def _parse(self):
        """Parses the Ordt XML tree and constructs the RDL Adress Map hierarchy"""
        
        for child in self.root:
            # Get all the top level Register components
            if child.tag == 'reg':
                self.registers.append(self._parse_reg(child))
            # then parse all Register File components
            elif child.tag == 'regset':
                self.registers.append(self._parse_regset(child))
            # Ignore all other tags
            elif child.tag in ['id', 'baseaddr', 'shorttext']:
                pass
            else:
                raise UnknownChildTag("Unexpected root.tag={}".format(child.tag))
            
    def _parse_regset(self, elem):
        """Parses the RDL Register File componet

        Arguments:
          elem - the XML element over which to iterate"""
        
        regset = {}
        regset['registers'] = []
        
        for e in elem:
            if e.tag in ['id', 'shorttext', 'longtext', 'baseaddr', 'highaddr']:
                regset[e.tag] = e.text
            elif e.tag == 'reg':
                regset['registers'].append(self._parse_reg(e))
            else:
                raise UnknownRegsetElement('Unexpected regset.tag={}'.format(e.tag))
            
        return RegisterFile(regset)
    
    def _parse_reg(self, elem):
        """Parses the RDL Register componet

        Arguments:
          elem - the XML element over which to iterate"""
        
        reg = {}
        reg['fields'] = []

        for e in elem:
            if e.tag in ['id', 'shorttext', 'baseaddr', 'width', 'access', 'parentpath', 'longtext']:
                reg[e.tag] = e.text
            elif e.tag == 'field':
                reg['fields'].append( self._parse_field(e) )
                reg['fields'][-1].baseaddr = reg['baseaddr']
            else:
                raise UnknownRegElement('Unexpected reg.tag={}'.format(e.tag))
            
        return Register(reg)
    
    def _parse_field(self, elem):
        """Parses the RDL Field componet

        Arguments:
          elem - the XML element over which to iterate"""
        field = {}
        
        for e in elem:
            if e.tag in ['id', 'shorttext', 'reset', 'lowidx', 'width', 'longtext', 'hwmod', 'singlepulse']:
                field[e.tag] = e.text if e.text else True
            elif e.tag == 'access':
                field['access'] = Access(e.text)
            elif e.tag == 'hwinfo':
                field['hwinfo'] = HwInfo(e)
            elif e.tag == 'intr':
                field['intr'] = Intr(e)
            else:
                raise UnknownFieldElement("Unexpected field.tag={}".format(e.tag))
            
        return Field(field)
    
    def _pathmap(self, comp, path=''):
        """Construct the full hierarchical paths to each register and their fields"""

        try:
            for c in comp:
                # Construct the full hierarchical path
                p = path + '_' + c.id if path else c.id
                # Update the component's path attribute
                c.path = p
                # Update the pathmap
                self.pathmap[p] = c
                # Recurse...
                self._pathmap(c,p)
        except TypeError:
            comp.path = path
            self.pathmap[path] = comp
                
    def _addressmap(self, comp):
        """Creates a flattened view of the address map by squashing any Register File components"""

        try:
            for c in comp:
                # Only update the addressmap for registers
                if c.isreg(): self.addressmap[int(c.baseaddr, 16)] = c
                self._addressmap(c)
        except TypeError:
            pass

    def _interrupts(self, comp):
        """Creates a dict containing all the external host interrupts for fast searching"""

        for d1ct in self.get_rtl_irq_inputs():
            self.interrupts[d1ct['wire']] = d1ct['field']

    def _fields(self):
        """Returns a list of all the individual fields"""

        return flatten( [r.fields for r in self._registers()] )

    def _registers(self):
        """Returns a list of all registers"""

        return flatten( [r.registers if r.isregfile() else r for r in self.registers] )
        
if __name__ == "__main__":
    
    import argparse

    parser = argparse.ArgumentParser(description="An Ordt XML parser")
    parser.add_argument("xml_file", help="Specify the XML file to parse")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--get_irq_inputs', action='store_true')
    group.add_argument('--get_irq_registers', action='store_true')
    group.add_argument('--get_irq_by_path')
    group.add_argument('--example', action='store_true', help='generate some example output data')
    parser.add_argument('--verbosity', default=0, type=int, help='specify a verbosity from 0, low, to 2, high.')
    args = parser.parse_args()

    addrmap = AddressMap(args.xml_file)

    if args.example:
        print(divider('ADDRESS MAP SUMMARY'))
        addrmap.to_s()

        print(divider('ADDRESS OF ALL REGS NAMED *irq_enable*'))
        print(addrmap.get_address_by_reg('irq_enable', 1))

        print(divider('ALL INTERRUPT REGS'))
        for irq in addrmap.get_irqs():
            print(irq.to_s(1))

        print(divider('STICKY INTERRUPT REGS'))
        for irq in addrmap.get_sticky_irqs():
            print(irq.to_s(1))

        print(divider('RTL IRQ INPUTS'))
        for d1ct in addrmap.get_rtl_irq_inputs():
            print(d1ct['wire'])

        # Perform some reads/writes
        ack = addrmap.write(3,1, args.verbosity)
        [ack, value] = addrmap.read(0x0, args.verbosity)
        ack = addrmap.write(0x0,1, args.verbosity)
        [ack, value] = addrmap.read(0x0, args.verbosity)
        print(ack, value)

    if args.get_irq_inputs:
        for d1ct in addrmap.get_rtl_irq_inputs():
            print(d1ct['wire'])

    if args.get_irq_registers:
        print('\n'.join(collimate( [irq.to_s(args.verbosity) for irq in addrmap.get_irqs()] , ' ')))

    if args.get_irq_by_path:
        fields = addrmap.get_irq_by_path(args.get_irq_by_path)
        [print(f.to_s(1)) for f in fields]
        


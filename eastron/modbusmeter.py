from pymodbus.client.sync import ModbusTcpClient
from pymodbus.pdu import ExceptionResponse
import struct
import logging
import time

class ModbusMeter:

    def __init__(self, host, slave_id):
        self.host = host
        self.slave_id = slave_id
        self.previous_values = {}
        self.persistent_regs = {0x48, 0x4a}

    def __read_float_reg(self, client, basereg, unit):
        self.__init_previous_value(client, basereg, unit)
        connection_error = False
        try:
            resp = client.read_input_registers(basereg, 2, unit=unit)
        except:
            connection_error = True
            logging.debug("Connection error while trying to connect to net meter.")
        if(connection_error or type(resp) is ExceptionResponse):
            if(basereg not in self.persistent_regs):
                self.previous_values[basereg] = 0
            # Most likely because of power failure.
            logging.debug("Received exception while reading eastron meter.")
        else:
            self.previous_values[basereg] = struct.unpack('>f', struct.pack('>HH', *resp.registers))

        return self.previous_values[basereg]

    def __fmt_or_dummy(self, regfmt, val):
        if val is None:
            return '.' * len(regfmt % (0))

        return regfmt % (val)

    def __init_previous_value(self, client, basereg, unit):
        while (basereg not in self.previous_values.keys()):
            resp = client.read_input_registers(basereg, 2, unit=unit)
            if (type(resp) is not ExceptionResponse):
                self.previous_values[basereg] = struct.unpack('>f', struct.pack('>HH', *resp.registers))
            else:
                time.sleep(10)

    def get_meter_vals(self, regs):
        client = ModbusTcpClient(self.host)

        values = {}

        for reg in regs:
            values[reg[0]] = self.__fmt_or_dummy(reg[2], self.__read_float_reg(client, reg[1], self.slave_id))

        client.close()
        return values

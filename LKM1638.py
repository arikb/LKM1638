"""JY-LKM1638 board driver library for Micropython / WiPy"""
#
# Code has been written from scratch by me:
#
# Arik Baratz <github@arik.baratz.org>
#
# but was HEAVILY inspired by the Arduino library by Ricardo Batista:
#
# https://github.com/rjbatista/tm1638-library
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the version 3 GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/
#
## Usage:
#
#from machine import Pin
#from LKM1638 import LKM1638, LED_RED, LED_NONE
#
#display = LKM1638(Pin.board.GP8, Pin.board.GP30, Pin.board.GP31)
#display.setup(True, 7)
#
#n = 0                 
#while True:
#    display.print_number(n, 16)
#    n+=1234
#    
#    for i, button in enumerate(display.get_buttons()):
#        if button:
#            display.set_led(i, LED_RED)
#        else:
#            display.set_led(i, LED_NONE)
#
## WARNING ##
#
# The JY-LKM1638 display is a 5v CMOS platform. This code has been tested on
# WiPi - a 3.3v platform. While the diaplay can accept 3.3v input, WiPy cannot
# accept a 5v input, which can happen on the DIO control.
#
# I've used a simple bidirectional level shifter, described here:
#
# http://electronics.stackexchange.com/a/97892/116011
#
# This level shifter already has pull-ups on both ends, so I have configured
# DIO as an open drain output without a pull-up. If your hardware differs, you
# would have to change it. Note that it's reinitialised in the _recv method.
#


from machine import Pin

HI = HIGH = True
LO = LOW = False

# Hex nibble font copied shamelessly from
# https://github.com/JensGrabner/tm1638-library/blob/master/TM16XXFonts.h
NUMBER_FONT = (0x3f, 0x06, 0x5b, 0x4f,
               0x66, 0x6d, 0x7d, 0x07,
               0x7f, 0x6f, 0x77, 0x7c,
               0x39, 0x5e, 0x79, 0x71)

LED_NONE, LED_GREEN, LED_RED = (0, 1, 2)

class LKM1638:
    def __init__(self, stb_pin, clk_pin, dio_pin):
        self._stb = stb_pin
        self._clk = clk_pin
        self._dio = dio_pin
        self._init()
    
    def _send_byte(self, bdata):
        """Send a single byte, assuming STB low and CLK hi"""
        for _ in range(8):
            self._clk(LO)
            self._dio(bdata & 1)
            self._clk(HI)
            bdata>>=1
    
    def _send_cmd(self, cmd):
        """Send a command"""
        self._stb(LO)
        self._send_byte(cmd)
        self._stb(HI)
        
    def _send_ram_data(self, addr, data):
        """Set an address on the controller"""
        # 7.1 Data command - Fixed address 0100 0100
        self._send_cmd(0x44)
        self._stb(LO)
        # 7.2 Address command - 1100 xxxx dddd dddd
        self._send_byte(0xC0 | addr)
        self._send_byte(data)
        self._stb(HI)
    
    def _init(self):
        # assuming DIO will use a level shifter from 3.3v to 5v
        # which already contains a pull-up
        self._dio.init(mode=Pin.OPEN_DRAIN, pull=None)
        self._stb.init(mode=Pin.OUT, pull=None)
        self._clk.init(mode=Pin.OUT, pull=None)
        
        self._clk(HI)
        self._stb(HI)
        # 7.1 Data command - Data write mode, automatic address 0100 0000
        self._send_cmd(0x40)
        self.setup(True, 7)
        
        self._stb(LO)
        # 7.2 Start address 0 - 1100 0000
        self._send_byte(0xC0)
        
        # zero all addresses
        for _ in range(16):
            self._send_byte(0x00)
        
        self._stb(HI)
    
    def setup(self, active, intensity):
        """Set the display up"""
        # 7.3 Display Control Command - 1000 aiii
        self._send_cmd(0x80 | int(active) << 3 | intensity)
            
        # magic
        self._stb(LO)
        self._clk(LO)
        self._clk(HI)
        self._stb(HI)
        
    def set_digit(self, pos, digit, dot=False):
        """
            Set up a single hex `digit` at position `pos` from the left,
            0-based. None as the digit clears it. `dot` indicates that the
            dot to the right of the current digit will be turned on.
        """
        if digit is None:
            self._send_ram_data(pos << 1, int(dot) << 7)
        else:
            self._send_ram_data(pos << 1, NUMBER_FONT[digit] | int(dot) << 7)

    def print_number(self, number, base=10):
        """
            Print a positive number, right justified, clearing other digits.
            `base` could be 16 and below, as far as supported font.
        """
        digits=[]
        while number:
            digits.append(number % base)
            number //= base
        # clear unused digits
        for pos in range(8-len(digits)):
            self.set_digit(pos, None)
        for pos in range(8-len(digits), 8):
            self.set_digit(pos, digits.pop())

    def _recv_byte(self):
        """receive a byte back from the display"""
        # assuming DIO will use a level shifter that already has a pull-up
        self._dio.init(mode=Pin.IN, pull=None)
        temp = 0
        
        for _ in range(8):
            temp >>= 1
            self._clk(LO)
            if self._dio():
                temp |= 0x80
            self._clk(HI)
        
        self._dio.init(mode=Pin.OPEN_DRAIN, pull=None)

        return temp
    
    def get_buttons(self):
        """
            Queries the state of the buttons on the display module.

            Returns a list of boolean values standing for 'The button in this
            position is depressed', from left to right.
        """
        self._stb(LO)
        # 7.1 Data Command - Read Key Scan Data - 0100 0010
        self._send_byte(0x42)
        
        key_low = []
        key_high = []
        for b in range(4):
            key_data = self._recv_byte()
            key_low.append(bool(key_data & 0x01))
            key_high.append(bool(key_data & 0x10))

        self._stb(HI)
        
        return key_low+key_high
    
    def set_led(self, pos, colour):
        """
            Set the LED at position `pos` to `colour`. Position is 0-based
            left to write and colour is LED_RED, LED_GREEN or LED_NONE
        """
        self._send_ram_data((pos << 1) + 1, colour)

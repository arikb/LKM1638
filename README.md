# LKM1638
JY-LKM1638 board driver library for Micropython / WiPy


Code has been written from scratch by me:

Arik Baratz <github@arik.baratz.org>

but was HEAVILY inspired by the Arduino library by Ricardo Batista:

https://github.com/rjbatista/tm1638-library

This program is free software: you can redistribute it and/or modify
it under the terms of the version 3 GNU General Public License as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see http://www.gnu.org/licenses/

## Usage:

	from machine import Pin
	from LKM1638 import LKM1638, LED_RED, LED_NONE

	display = LKM1638(Pin.board.GP8, Pin.board.GP30, Pin.board.GP31)
	display.setup(True, 7)

	n = 0                 
	while True:
    	display.print_number(n, 16)
    	n+=1234
    
    	for i, button in enumerate(display.get_buttons()):
    	    if button:
        	    display.set_led(i, LED_RED)
     	   else:
        	    display.set_led(i, LED_NONE)

## WARNING ##

The JY-LKM1638 display is a 5v CMOS platform. This code has been tested on
WiPi - a 3.3v platform. While the diaplay can accept 3.3v input, WiPy cannot
accept a 5v input, which can happen on the DIO control.

I've used a simple bidirectional level shifter, described here:

http://electronics.stackexchange.com/a/97892/116011

This level shifter already has pull-ups on both ends, so I have configured
DIO as an open drain output without a pull-up. If your hardware differs, you
would have to change it. Note that it's reinitialised in the _recv method.


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Photobooth - a flexible photo booth software
# Copyright (C) 2018  Balthasar Reuter <photobooth at re - web dot eu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import logging
from colorsys import hsv_to_rgb
from time import sleep

from .. import StateMachine
from ..Threading import Workers


class Gpio:

    def __init__(self, config, comm):

        super().__init__()

        self._comm = comm
        self._gpio = None
        self._cfg = config
    
        self._is_bottompin = False
        self._is_leftpin = False     # neu und Ahnung
        self._is_rightpin = False   # neu und Ahnung
        self._is_enabled = config.getBool('Gpio', 'enable')
        self._countdown_time = config.getInt('Photobooth', 'countdown_time')

        self.initGpio(config)

    def initGpio(self, config):

        if self._is_enabled:
            self._gpio = Entities()
            
            # GPIO Nummer aus der Config auslesen
            custom_bottom_pin = config.getInt('Gpio', 'trigger_pin')     
            custom_left_pin = config.getInt('Gpio', 'printp_pin')        # neu
            custom_right_pin = config.getInt('Gpio', 'againpic_pin')     # neu


            logging.info(('GPIO enabled (custom_bottom_pin=%d,'
                        'custom_left_pin=%d,custom_right_pin=%d'                  # neu
                         ')'),
                         custom_bottom_pin, custom_left_pin, custom_right_pin)     # neu

            self._gpio.setButton(custom_bottom_pin, self.two_images)
            self._gpio.setButton(custom_left_pin, self.one_image)        # neu
            self._gpio.setButton(custom_right_pin, self.four_images)    # neu
        else:
            logging.info('GPIO disabled')

    def run(self):

        for state in self._comm.iter(Workers.GPIO):
            self.handleState(state)

        return True

    def handleState(self, state):

        if isinstance(state, StateMachine.IdleState):
            self.showIdle()
        elif isinstance(state, StateMachine.GreeterState):
            self.showGreeter()
        elif isinstance(state, StateMachine.CountdownState):
            self.showCountdown()
        elif isinstance(state, StateMachine.CaptureState):
            self.showCapture()
        elif isinstance(state, StateMachine.AssembleState):
            self.showAssemble()
        elif isinstance(state, StateMachine.ReviewState):
            self.showReview()
        elif isinstance(state, StateMachine.PostprocessState):
            self.showPostprocess()

    def enableBottomPin(self):

        if self._is_enabled:
            self._is_bottompin = True

    def disableBottomPin(self):

        if self._is_enabled:
            self._is_bottompin = False

    #----------------------------------neu
    # Aktivieren / Deaktivieren der Taster
    def enableLeftPin(self):

        if self._is_enabled:
            self._is_leftpin = True

    def disableLeftPin(self):

        if self._is_enabled:
            self._is_leftpin = False
            
    def enableRightPin(self):

        if self._is_enabled:
            self._is_rightpin= True

    def disableRightPin(self):

        if self._is_enabled:
            self._is_rightpin = False


    # neu --------------------------------------------------------------------------
    # Zuordnung zwischen Taster und Bilderanzahl + Schreiben in das Photobooth.cfg file
    def one_image(self):
        
        self._cfg.set('Picture','num_x','1')
        self._cfg.set('Picture','num_y','1')
        self._cfg.write()
        logging.info('Taste gedrückt - Schreibe 1 Bild ins Photobooth.cfg')
        if self._is_leftpin:
            self.disableBottomPin()
            self.disableLeftPin()
            self.disableRightPin()
            self._comm.send(Workers.MASTER, StateMachine.GpioEvent('printp'))
    
    def two_images(self):

        self._cfg.set('Picture','num_x','1')
        self._cfg.set('Picture','num_y','2')
        self._cfg.write()
        logging.info('Taste gedrückt - Schreibe 2 Bilder ins Photobooth.cfg')
        if self._is_bottompin:
            self.disableBottomPin()
            self.disableLeftPin()
            self.disableRightPin()
            self._comm.send(Workers.MASTER, StateMachine.GpioEvent('trigger'))
            
    def four_images(self):
        
        self._cfg.set('Picture','num_x','2')
        self._cfg.set('Picture','num_y','2')
        self._cfg.write()
        logging.info('Taste gedrückt - Schreibe 4 Bilder ins Photobooth.cfg')
        if self._is_rightpin:
            self.disableBottomPin()
            self.disableLeftPin()
            self.disableRightPin()
            self._comm.send(Workers.MASTER, StateMachine.GpioEvent('againpic'))
    # neu  --------------------------------------------------------------------------
    def exit(self):

        self._comm.send(
            Workers.MASTER,
            StateMachine.TeardownEvent(StateMachine.TeardownEvent.WELCOME))

    def showIdle(self):
        # sleep(3) # Wartezeit 
        self.enableBottomPin()
        self.enableLeftPin()     # Taster aktivieren
        self.enableRightPin()   # Taster aktivieren

    def showGreeter(self):

        self.disableBottomPin()
        self.disableLeftPin()
        self.disableRightPin()

    def showCountdown(self):

        self.disableBottomPin()
        self.disableLeftPin()
        self.disableRightPin()
        sleep(0.2)

    def showCapture(self):

        self.disableBottomPin()
        self.disableLeftPin()
        self.disableRightPin()

    def showAssemble(self):

        self.disableBottomPin()
        self.disableLeftPin()
        self.disableRightPin()

    def showReview(self):

        self.disableBottomPin()
        self.disableLeftPin()
        self.disableRightPin()

    def showPostprocess(self):
        
        self.enableRightPin()   # Taster aktivieren für "nochmal"
        self.enableBottomPin()    # Taster aktivieren für "nochmal"
        self.enableLeftPin()     # Taster aktivieren für "drucken"
        
        pass


class Entities:

    def __init__(self):

        super().__init__()

        import gpiozero
        self.Button = gpiozero.Button
        self.GPIOPinInUse = gpiozero.GPIOPinInUse

        self._buttons = []

    def setButton(self, bcm_pin, handler):

        try:
            self._buttons.append(self.Button(bcm_pin))
            self._buttons[-1].when_pressed = handler
        except self.GPIOPinInUse:
            logging.error('Pin {} already in use!'.format(bcm_pin))
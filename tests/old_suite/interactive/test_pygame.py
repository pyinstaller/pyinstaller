# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# This is a copy of
# http://jonasbsb.jo.funpic.de/hendrix/pygame-example.py


try:
    import sys
    import random
    import math
    import os
    import pygame
    import time
    from pygame.locals import *

except ImportError as err:
    raise SystemExit("Error, couldn't load module. %s" % err)

if not pygame.mixer: print('Warning, sound disabled')

NUM_SPRITES = 10

### Klassendefinitionen

class Screen:
    def __init__(self, resolution=(640, 480), cmdline=""):
        self.color = (0,0,0)
        self.resolution = resolution
        if "--fullscreen" in cmdline:
            self.window = \
                pygame.display.set_mode(self.resolution, pygame.FULLSCREEN) 
        else:
            self.window = pygame.display.set_mode(self.resolution)
        # pygame.display.set_mode() verändert die Größe des Fensters
        # Über das zweite Argument, pygame.FULLSCREEN, kann das Fenster
        # in den Vollbildmodus versetzt werden
                    
        pygame.display.set_caption('A Simple Yet Insightful Pygame Example') 
        # Verändert die Beschriftung des Fensters
        
        pygame.mouse.set_visible(0)
        # Verhindert, dass die Maus gezeigt wird
        
        self.screen = pygame.display.get_surface()
        # Generiert ein Surface des Fensters
        # Siehe: Allgemeines über Surfaces
        
        self.screen.fill(self.color)
        # Füllt das Surface self.screen mit der übergebenen Farbe
        # Siehe: Allgemeines über Farben

        self.screen_rect = self.screen.get_rect()
        # Rectangle des Fensters
        # Siehe: Allgemeines über Rectangles
        
    def size(self):
        return self.screen_rect
    
    def fill(self):
        self.screen.fill(self.color)
        # Füllt das Surface self.screen mit der übergebenen Farbe
        # Siehe: Allgemeines über Farben


class Sprite(pygame.sprite.Sprite): 
    def __init__(self, screen):
        pygame.sprite.Sprite.__init__(self) 
        # Die Klasse Sprite wird von der pygame-Basisklasse
        # pygame.sprite.Sprite abgeleitet
        
        self.screen= screen

        self.width = 10
        self.height = 10
        # Legt die Höhe und Breite der Objekte fest
        
        self.x = random.randint(0, screen.resolution[0] + self.width)
        self.y = random.randint(0, screen.resolution[1] + self.height)
        # Generiert zufällig eine x- und eine y-Koordinate als Startpunkt

        self.direction = random.choice((1,-1))
        self.angle = random.choice((0.45, 2.69)) * self.direction
        self.speed = random.randint(5,8)
        # Wählt zufällig Werte für die Richtung und Geschwindigkeit aus

        self.image = pygame.Surface([self.width, self.height])
        # Generiert ein Surface des Objektes mit der definierten Größe
        # Siehe: Allgemeines über Surfaces
        
        self.rect = self.image.get_rect()
        # Siehe: Allgemeines über Rectangles
        
        self.rect = self.rect.move(self.x,self.y)
        # self.rect.move(x-Wert, y-Wert) berechnet einen
        # neuen Punkt und ordnet ihn dem Rectangle des
        # Objektes zu
        #
        # Das Koordinatensystem beginnt am oberen, linken Rand
        # des Bildschirms mit (0,0)
         
        self.area = pygame.display.get_surface().get_rect()
        # Rectangle des Fensters
        # Siehe: Allgemeines über Rectangles

    def position(self):
        return self.rect

    def changeColor(self):
        newColor = []
        for i in range(3):
            newColor.append(random.randint(0,255))
        self.color = newColor
        # Generiert einen zufälligen Farbwert
        
        self.image.fill(self.color)
        # Füllt das Surface des Objektes
        # Siehe: Allgemeines über Farben

    def update(self):
        dx = self.speed*math.cos(self.angle)        
        dy = self.speed*math.sin(self.angle)
        # Mathematische Grundlage der Bewegung
        # siehe: http://de.wikipedia.org/wiki/Sinus
        
        newpos = self.rect.move(dx,dy)
        # berechnet eine neue Position

        if not self.area.contains(newpos):
        # Kollisionsberechnung  
            tl = not self.area.collidepoint(newpos.topleft)
            tr = not self.area.collidepoint(newpos.topright)
            bl = not self.area.collidepoint(newpos.bottomleft)
            br = not self.area.collidepoint(newpos.bottomright)
            # Kollisionen mit den Eckpunkten des Fensters werden
            # berechnet und als boolescher Wert gespeichert 
            # (0 keine Kollision, 1 Kollision)

            if tr and tl or (br and bl):
            # Falls das Objekt mit dem oberen oder unteren 
            # Bildschirmrand kollidiert,
                self.angle = -self.angle
                self.changeColor()
                # wird der Winkel (und damit die Richtung) umgekehrt
                # und die Farbe verändert
                
            if tl and bl or (tr and br):
            # Falls das Objekt mit dem linken oder rechten
            # Bildschirmrand kollidiert,
                self.angle = math.pi - self.angle
                self.changeColor()
                # Wird der Winkel (und damit die Richtung) umgekehrt
                # und die Farbe verändert

        self.rect = newpos
        # Ordnet dem Rectangle des Objekts die neue Position zu
        # Die Veränderung der Position wird erst hier gültig!


### Funktionsdefinitionen

def end():
    sys.exit(0)

def game(events, screen, sprites):
    for event in events:
    # Wertet die Event-Warteschleife aus
        if event.type == QUIT:
            # Beendet das Programm, wenn z.B. das Fenster geschlossen wurde
            end()
            return
        elif event.type == KEYDOWN and event.key == K_ESCAPE:
            # Beendet das Programm, wenn die Taste Escape gedrückt wurde 
            end()
            return
        elif event.type == KEYDOWN and event.key == K_f:
            # Schaltet in den Vollbildmodus, wenn die Taste F gedrückt wurde 
            pygame.display.toggle_fullscreen()
            return
        
    screen.fill()
    # Füllt den Bildschirm
        
    sprites.update()
    # Bewegung und Kollisionserkennung der Sprite-Gruppe
    # Die update-Funktion der Instanzen wird automatisch
    # für alle 123 Rechtecke aufgerufen
    
    sprites.draw(screen.screen)
    # Zeichnet die Sprite-Instanzen auf den Bildschirm
    
    pygame.display.update()
    # Aktualisiert den Bildschirm
    

def main():
    pygame.init()
    
    pygame.key.set_repeat(1, 1) 
    # Legt fest, wie oft Tastendrücke automatisch wiederholt werden
    # Das erste Argument gibt an ab wann, das zweite in welchen
    # Intervallen der Tastendruck wiederholt wird

    clock = pygame.time.Clock()
    # Erstellt einen Zeitnehmer
    
    screen = Screen(cmdline=sys.argv)
    # Erstellt eine Instanz der Klasse Screen()

    movingSprites = []
    for i in range(NUM_SPRITES):
        movingSprites.append(Sprite(screen))
    # Die for-Schleife erstellt 123 Instanzen der Klasse Sprite
    # und fügt sie der Liste movingSprites hinzu

    sprites = pygame.sprite.RenderPlain((movingSprites))
    # Fasst die erstellen Sprite-Instanzen zu einer Gruppe zusammen
    # um das Zeichnen der Sprites zu erleichtern

    while True:   
        clock.tick(30)
        # Verhindert, dass das Spiel zu schnell läuft
        
        game(pygame.event.get(), screen, sprites)
        # Ruft die Funktion game auf und übergibt ihr
        # die Event-Warteschleife, die Zeichenfläche und die Objekte
    end()

main()

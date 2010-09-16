#!/usr/bin/python
#coding=UTF-8
'''
Created on 1. jan. 2010

This script is created with the purpose of handling bandwidth issues 
with certain programs. The main problem being that the landlord of a 
certain university campus village disconnect their user's Internet 
connection if they exceed the 10gb/24h traffic limit. 

@author: Harald Hauknes <harald (att) hauknes (dot) org>

Written for Python 2.6 with PIL
'''

import time
import os
import ConfigParser
from Tkinter import Tk, Frame, Label
from Tkconstants import FALSE, LEFT, RIGHT, TOP, X, W, N
import tkFont
import urllib2
import base64

#TODO: Test in Ubuntu, Windows and OSX
#TODO: GUI for configuring cw.cfg
#TODO: Write README
#TODO: Add pokemon error handling?
class CWGUI:
    '''
    Draws the GUI and initiates the core components of the program.
    '''
    def __init__(self):
        self.root = Tk()
        self.root.title("CW")
        self.root.resizable(width=FALSE, height=FALSE)
        self.mainframe = Frame(self.root, bg='white', border=0)
        self.values = CONFIG()
        self.labels_pnames = []
        self.labels_status = []

        self.main_window(self.values)
    
    def main_window(self, values):
        '''
        Initiates the main components of the program, and draws the GUI.
        '''
#HEADER
        font_header = tkFont.Font(family="Helvetica", size=16, weight="bold")
        label_header = Label(self.mainframe, text="Campus-Warder",
            #fg="LightCyan3", 
            fg='LightCyan4',
            bg='white', font=font_header)
        label_header.pack(anchor=N, pady=5)
#BANDWIDTHUSAGE
        frame_bandwidth = Frame(self.mainframe, border=2, relief="groove",
            bg='white')

        label_bandwidth_decorator = Label(frame_bandwidth, text="Usage:\n",
            bg='white')
        label_bandwidth_decorator.pack(side=LEFT, padx=5)
        # Colors and font
        upcolor = color_indicator(values.parser.up, values.uplimit)
        downcolor = color_indicator(values.parser.down, values.downlimit)
        font_numbers = tkFont.Font(family="Helvetica", size=12, weight="bold")
        # Values
        label_up_decorator = Label(frame_bandwidth, bg='white', text="Up: ")
        label_up_decorator.pack(side=LEFT)
        self.label_up = Label(frame_bandwidth, bg='white', fg=upcolor,
            font=font_numbers, text=str(values.parser.up) + " MB")
        self.label_up.pack(side=LEFT)
        label_down_decorator = Label(frame_bandwidth, bg='white', 
            text=" /  Down: ")
        label_down_decorator.pack(side=LEFT)
        self.label_down = Label(frame_bandwidth, bg='white', fg=downcolor,
            text= str(values.parser.down) + " MB", font=font_numbers)
        self.label_down.pack(side=LEFT, padx= 5)

        frame_bandwidth.pack(side=TOP)
#PROGRAMS AND STATUS
        frame_status = Frame(self.mainframe, bg='white', border=2,
            relief="groove")
        frames_status = []

        for i in range(0, len(values.programs)):
            frames_status.append(Frame(frame_status, bg='white', border=0,
                relief='groove'))
            #Program display names
            self.labels_pnames.append(Label(frames_status[i], bg='white',
                text=values.programs[i].display_name + ": "))
            self.labels_pnames[i].pack(side=LEFT, padx=6)
            #Status
            self.labels_status.append(Label(frames_status[i], bg='white',
                text=values.programs[i].status))
            self.labels_status[i].pack(side=RIGHT, padx=6)

            frames_status[i].pack(side=TOP, fill=X) 
#PACK
        frame_status.pack(side=TOP, fill=X, anchor=W)
        self.mainframe.pack()
#ENDLESS LOOP
        #On the first run, wait 3 seconds so that the GUI
        #has a chance to draw
        self.root.after(3000, self.update)

    def update(self):
        '''
        Updates the status of the programs, depending on the output of the OS
        tasklist command
        '''
        #Update every 2 minutes
        self.root.after(60*1000*2, self.update)
#BANDWIDTH STATUS
        # Colors
        bandwidth = self.values.get_bandwidth()
        upcolor = color_indicator(bandwidth[0], self.values.uplimit)
        downcolor = color_indicator(bandwidth[1], self.values.downlimit)
        # Values
        self.label_up["fg"] = upcolor,
        self.label_up["text"] = str(self.values.parser.up) + " MB"
        self.label_up.update()
        self.label_down["fg"] = downcolor,
        self.label_down["text"] = str(self.values.parser.down) + " MB"
        self.label_down.update()
#PROGRAM STATUS
        if self.values.os == "Windows":
            ps_output = os.popen("tasklist").read()
        else:
            ps_output = os.popen("ps aux").read()
        #Loop through all programs
        for i in range(0, len(self.values.programs)):
            #If currently active
            if ps_output.find(self.values.programs[i].process_name) > 5:
                self.values.programs[i].status = "Active"
                self.values.programs[i].update()
            #If not currently active
            elif ps_output.find(self.values.programs[i].process_name) ==  -1:
                if self.values.programs[i].status == "Active":
                    self.values.programs[i].status = "KBU"
            
            self.labels_status[i]["text"] = self.values.programs[i].status
            self.labels_status[i].update()
#UPDATE GUI
        self.mainframe.update()
    
class CWPROCESS:
    '''
    Class to handle interaction with the various programs we need to 
    monitor and control.
    '''
    def __init__(self, process_name, up_limit, down_limit, display_name,
        values, full_path=None, status="MIA"):
        '''
        Arguments:
        process_name -- The name of the process as the OS sees it
        #TODO:write proper docstrings
        '''
        self.process_name = process_name
        self.up_limit = up_limit
        self.down_limit = down_limit
        self.display_name = display_name
        self.full_path = full_path
#MIA=it never ran, KIA=it ran but we killed it, Active = running now, KBU =
#killed by user
        self.status = status
        self.values = values

    def update(self):
        if (self.status == 'MIA') or (self.status == 'KBU'):
            #This status is updated from the update status loop
            return


        elif self.status == 'KIA':
            if (self.up_limit > self.values.parser.up) or (self.down_limit >
                self.values.parser.down):
                self.revive()

        elif self.status == 'Active':
            if (self.up_limit < self.values.parser.up) or (self.down_limit < 
                self.values.parser.down):
                self.kill()

    def kill(self):
        os.system(self.values.kill_command + " " + self.process_name)
        self.status = "KIA"

    def revive(self):
        '''
        Starts processes that has earlier been killed by this script and
        is eligble to be started again.
        '''
        if self.values.os == "OSX":
            os.system("/Applications/" + self.process_name + ".app" +
                "/Contents/MacOS/" + self.process_name + " &")
        #TODO: Investigate revive hang on OSX
        #TODO: Switch to use of subprocess module
        if self.values.os == "linux":
            os.system(self.process_name + " &")

        if self.values.os == "Windows":
            os.system("start " + self.full_path)
        self.status = "Active"

class CONFIG:
    def __init__(self):
#OS
        if os.path.isdir("/Applications"):
            self.os = "OSX"
        elif os.path.isdir("C:/Windows"):
            self.os = "Windows"
        elif os.path.isdir("/usr/bin"):
            self.os = "linux"

        config = ConfigParser.RawConfigParser()
        config.read('cw.cfg')
#LIMITS
        self.uplimit = int(config.get('CW', 'uplimit'))
        self.downlimit = int(config.get('CW', 'downlimit'))
#PROGRAMS
        all_programs_processed = False
        program_no = 1
        self.programs = []
        while not all_programs_processed:
            try:
                process_name = config.get('Program' + str(program_no),
                    'process_name')
                up_limit = int(config.get('Program' + str(program_no),
                    'up_limit'))
                down_limit = int(config.get('Program' + str(program_no),
                    'down_limit'))
                display_name = config.get('Program' + str(program_no),
                    'display_name')

                if self.os == "Windows":
                    full_path = config.get('Program' + str(program_no), 
                        'full_path')
                self.programs.append(CWPROCESS(process_name, up_limit,
                    down_limit, display_name, self))
                program_no += 1
            except ConfigParser.NoSectionError: 
                break
#KILL
        self.kill_command = "killall"
        if self.os == "Windows":
            self.kill_command = "taskkill /IM"
#ROUTER INFO
        self.router_url = config.get('CW', 'router_url')
        self.router_user = config.get('CW', 'router_user')
        self.router_pass = config.get('CW', 'router_pass')

#BANDWIDTH
        self.parser = CWPARSER(self)
        # Initiate values for the parser
        self.get_bandwidth()

        self.revive_list = []
        self.kill_count = 0

    def get_bandwidth(self):
        self.parser.parse()
        while ((self.parser.up == -1) or (self.parser.down == -1)):
            self.parser.parse()
            time.sleep(1)

        return (self.parser.up, self.parser.down)

def color_indicator(value, limit):
    '''
    Compares two values and returns a coloring based
    on the percentage the first value is of the second.

    Argument:
    value -- The first value
    limit -- The second value which the first is measured against
    '''
    if value < (limit * 0.33):
        color = 'darkgreen'
    elif value < (limit * 0.66):
        color = 'orange'
    else:
        color = 'red'

    return color

class CWPARSER:
    '''
    This class handles the parsing of the html
    from the router, it gets it's values from the 
    configuration object.
    '''
    def __init__(self, config):
        self.config = config
        self.up = 0
        self.down = 0

    def parse(self):
        '''
        Authenticates to the router, and parses the html of the
        24/h view to see how much data has been transmitted
        '''
        request = urllib2.Request(self.config.router_url)
        base64string = base64.encodestring(
            '%s:%s' % (self.config.router_user, 
            self.config.router_pass))[:-1]
        authheader =  "Basic %s" % base64string
        request.add_header("Authorization", authheader)
        try:
            handle = urllib2.urlopen(request)
        except IOError:
        # here we shouldn't fail if the username/password is right
            print "It looks like the username or password is wrong."
            self.up = -2
            self.down = -2
            return

        html = handle.read()

# Learned from trial and error the correct export value is extracted from the 
# 4th occurrence of the tx_total value.

        unsearched_tx = html
        unsearched_rx = html

        for i in range (0, 4):
            #This code is very old, and I cant bother to make it look better ;)
            #TODO: This is horrible, switch to regex 
            index_tx = unsearched_tx.find("tx_total")
            index_rx = unsearched_rx.find("rx_total")
            if (i != 3):
                # if we aren't on the fourth occurrence we just keep searching
                unsearched_tx = (
                    unsearched_tx[index_tx+25:len(unsearched_tx)])
                unsearched_rx = unsearched_rx[index_rx+25:len(unsearched_rx)]
            else:
                # extracting substring containing desired value
                tx_value = unsearched_tx[index_tx:index_tx+30]
                rx_value = unsearched_rx[index_rx:index_rx+30]
                whitepace_tx = tx_value.find(" ")
                whitepaceindexrx = rx_value.find(" ")
                # cutting away the identifying variable
                tx_value = tx_value[whitepace_tx+1:len(tx_value)]
                rx_value = rx_value[whitepaceindexrx+1:len(rx_value)]
                # the value may end in a whitespace or bracket
                # the rx value seems to be able to end in a comma 
                whitepace_tx = tx_value.find(" ")
                bracket_tx = tx_value.find("}")
                whitepaceindexrx = rx_value.find(" ")
                bracketindexrx = rx_value.find("}")
                commaindex_rx = rx_value.find(",")
                # take either the bracket or whitespace that comes first
                if (whitepace_tx>bracket_tx and 
                    bracket_tx>0 and whitepace_tx>0): 
                    bracket_tx = whitepace_tx
                tx_value = tx_value[0:bracket_tx]
                if (whitepaceindexrx>bracketindexrx and 
                    bracketindexrx>0 and whitepaceindexrx>0): 
                    bracketindexrx = whitepaceindexrx
                # Seems that rx is always separated by comma
                if (commaindex_rx>bracketindexrx 
                    and commaindex_rx > 0):
                    bracketindexrx = commaindex_rx
                rx_value = rx_value[0:bracketindexrx]
            i += 1
        
        # Display the value in megabytes
        try:
            self.up = int(tx_value)/(1024*1024)
            self.down = int(rx_value)/(1024*1024)
        # Sometimes the value is parsed incorrectly,
        # if so - ignore it - this script is meant to be looped
        except ValueError:
            self.up = -1
            self.down = -1

def main():
    '''
    Initiates CampusWarder, takes no arguments.
    '''
    app = CWGUI()
    app.mainframe.mainloop()

if __name__ == '__main__':
    main()


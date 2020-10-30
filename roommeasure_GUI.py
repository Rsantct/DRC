#!/usr/bin/env python3
""" This is a Tkinter based GUI to running DRC/roommeasure.py
"""

from tkinter import *
from tkinter import ttk

import roommeasure as rm
from time import sleep


class RoommeasureGUI():


    def __init__(self, root):
        self.root = root
        self.root.title('DRC/roommeasure.py GUI')
        content =  ttk.Frame( root, padding=(10,10,12,12) )

        # SOUND CARD
        lbl_scard      = ttk.Label(content, text='SOUND CARD:')
        lbl_cap        = ttk.Label(content, text=' IN:')
        self.combo_cap = ttk.Combobox(content, values=cap_devs)
        lbl_pbk        = ttk.Label(content, text='OUT:')
        self.combo_pbk = ttk.Combobox(content, values=pbk_devs)
        lbl_fs         = ttk.Label(content, text='rate:')
        self.combo_fs  = ttk.Combobox(content, values=srates, width=8)

        # MEASURE SECTION
        lbl_meastitle    = ttk.Label(content, text='MEASURE:')
        lbl_ch           = ttk.Label(content, text='channels:')
        self.combo_ch    = ttk.Combobox(content, values=channels, width=4)
        lbl_meas         = ttk.Label(content, text='meas per channel:')
        self.combo_meas  = ttk.Combobox(content, values=takes,    width=4)
        lbl_sweep        = ttk.Label(content, text='sweep length:')
        self.combo_sweep = ttk.Combobox(content, values=sweeplen, width=7)
        lbl_scho         = ttk.Label(content, text='Schroeder freq:')
        self.ent_scho    = ttk.Entry(content,                     width=5)

        # REMOTE JACK SECTION
        lbl_rjack        = ttk.Label(content, text='Remote JACK:')
        lbl_rjaddr       = ttk.Label(content, text='addr:')
        self.ent_rjaddr  = ttk.Entry(content,                     width=12)
        lbl_rjuser       = ttk.Label(content, text='user:')
        self.ent_rjuser  = ttk.Entry(content,                     width=12)
        self.ent_rjuser.insert(0, 'paudio')

        # [Run] BUTTON AREA
        lbl_run          = ttk.Label(content, text='RUN:')
        lbl_timer        = ttk.Label(content, text='auto timer (s):')
        self.combo_timer = ttk.Combobox(content, values=timers, width=7)
        self.noBeep      = BooleanVar()
        self.chk_noBeep  = ttk.Checkbutton(content, text=' no beep',
                                           variable=self.noBeep,
                                           onvalue=True, offvalue=False)
        self.btn_go    = ttk.Button(content, text='Go!', command=self.go)

        # BOTTOM MESSAGES AREA
        self.lbl_msg     = ttk.Label(content, text='...', font=(None, 30))

        # DEFAULT VALUES
        self.combo_fs.set('48000')
        self.combo_ch.set('LR')
        self.combo_meas.set('3')
        self.combo_sweep.set(str(2**17))
        self.ent_scho.insert(0, '200')
        self.combo_timer.set('manual')

        # GRID ARRANGEMENT
        content.grid(           row=0,  column=0, sticky=(N, S, E, W) )

        lbl_scard.grid(         row=0,  column=0, sticky=W )
        lbl_cap.grid(           row=1,  column=0, sticky=E )
        self.combo_cap.grid(    row=1,  column=1)
        lbl_pbk.grid(           row=1,  column=2, sticky=E )
        self.combo_pbk.grid(    row=1,  column=3)
        lbl_fs.grid(            row=1,  column=4, sticky=E )
        self.combo_fs.grid(     row=1,  column=5)

        lbl_meastitle.grid(     row=2,  column=0, sticky=W )
        lbl_ch.grid(            row=3,  column=0, sticky=E )
        self.combo_ch.grid(     row=3,  column=1, sticky=W )
        lbl_meas.grid(          row=3,  column=2, sticky=E )
        self.combo_meas.grid(   row=3,  column=3, sticky=W )
        lbl_sweep.grid(         row=3,  column=4, sticky=E )
        self.combo_sweep.grid(  row=3,  column=5, sticky=W )
        lbl_scho.grid(          row=4,  column=4, sticky=E )
        self.ent_scho.grid(     row=4,  column=5, sticky=W )

        lbl_rjack.grid(         row=5,  column=0, sticky=W )
        lbl_rjaddr.grid(        row=6,  column=0, sticky=E )
        self.ent_rjaddr.grid(   row=6,  column=1, sticky=W )
        lbl_rjuser.grid(        row=6,  column=2, sticky=E )
        self.ent_rjuser.grid(   row=6,  column=3, sticky=W )

        lbl_run.grid(           row=7,  column=0, sticky=W )
        lbl_timer.grid(         row=8,  column=2, sticky=E )
        self.combo_timer.grid(  row=8,  column=3, sticky=W )
        self.chk_noBeep.grid(   row=8,  column=4 )
        self.btn_go.grid(       row=8,  column=5 )

        self.lbl_msg.grid(      row=9,  column=0, columnspan=6, sticky=W )

        # RESIZING BEHAVIOR
        root.rowconfigure(      0, weight=1)
        root.columnconfigure(   0, weight=1)
        for i in range(8):
            content.rowconfigure(   i, weight=1)
        for i in range(3):
            content.columnconfigure(i, weight=1)


    def handle_keypressed(self, event):
        print(f'a key "{event.char}" was pressed')


    def go(self):

        self.lbl_msg['text'] = 'RUNNING ...'

        cap         =   self.combo_cap.get()
        pbk         =   self.combo_pbk.get()
        ch          =   self.combo_ch.get()
        fs          =   int(self.combo_fs.get())
        takes       =   int(self.combo_meas.get())
        Scho        =   float(self.ent_scho.get())
        noBeep      =   self.noBeep.get()
        rjaddr      =   self.ent_rjaddr.get()
        rjuser      =   self.ent_rjuser.get()

        print(f'cap:        {cap}')
        print(f'pbk:        {pbk}')
        print(f'ch:         {ch}')
        print(f'fs:         {fs}')
        print(f'takes:      {takes}')
        print(f'Schroeder:  {Scho}')
        print(f'noBeep:     {noBeep}')
        print(f'rjaddr:     {rjaddr}')
        print(f'rjuser:     {rjuser}')

        rm.LS.fs = fs

        # PREPARING things as per given options:
        # - Preparing beeps:
        rm.beepL = rm.tools.make_beep(f=880, fs=rm.LS.fs)
        rm.beepR = rm.tools.make_beep(f=932, fs=rm.LS.fs)

        # - Preparing log-sweep as per the updated LS parameters
        rm.LS.prepare_sweep()

        # - Prepare a positive frequencies vector as per the selected N value.
        rm.freq = rm.np.linspace(0, int(rm.LS.fs/2), int(rm.LS.N/2))

        # Requesting the user to focus on this window
        #if not timer:
        #    user_focus_request()

        # MAIN measure procedure and SAVING
        rm.do_meas_loop()

        # COMPUTE the average from all raw measurements
        self.lbl_msg['text'] = 'COMPUTING AVERAGES ...'
        rm.do_averages()
        rm.do_save_averages()

        # Plotting prepared curves
        self.lbl_msg['text'] = 'GRAPHS ...'
        rm.LS.plt.show()

        # END
        self.lbl_msg['text'] = 'END.'


if __name__ == '__main__':

    cap_devs = [ x['name'] for x in rm.LS.sd.query_devices()[:] \
                           if x['max_input_channels'] >= 2 ]
    pbk_devs = [ x['name'] for x in rm.LS.sd.query_devices()[:] \
                           if x['max_output_channels'] >= 2 ]
    srates   = ['44100', '48000']
    channels = ['C', 'L', 'R', 'LR']
    takes    = list(range(1,21))
    sweeplen = [2**14, 2**15, 2**16, 2**17]
    timers   = ['1','2','3','4','5','manual']

    root = Tk()
    app = RoommeasureGUI(root)
    root.mainloop()

#!/usr/bin/env python3
""" This is a Tkinter based GUI to running DRC/roommeasure.py
"""
from tkinter import *
from tkinter import ttk
import threading
import roommeasure as rm


class RoommeasureGUI(Tk):

    ### MAIN WINDOW
    def __init__(self):

        super().__init__()  # this initiates the parent class Tk in order to
                            # make self a typical root = Tk()

        self.title('DRC/roommeasure.py GUI')
        self.geometry('+250+100')
        content =  ttk.Frame( self, padding=(10,10,12,12) )

        ### EVENTS HANDLING
        self.bind('<Key>', self.handle_keypressed)

        ### AVAILABLE COMBOBOX OPTIONS
        cap_devs = [ x['name'] for x in rm.LS.sd.query_devices()[:] \
                               if x['max_input_channels'] >= 2 ]
        pbk_devs = [ x['name'] for x in rm.LS.sd.query_devices()[:] \
                               if x['max_output_channels'] >= 2 ]
        srates   = ['44100', '48000']
        channels = ['C', 'L', 'R', 'LR']
        takes    = list(range(1,21))
        sweeps   = [2**15, 2**16, 2**17]
        timers   = ['manual', '3', '5', '10']

        ### VARS
        self.var_beep     = IntVar()

        ### VARS SHARED WITH rm.do_meas_loop()
        self.meas_trigger = threading.Event()
        self.var_msg      = StringVar()

        ### WIDGETS
        # - SOUND CARD SECTION
        lbl_scard        = ttk.Label(content, text='SOUND CARD:')
        lbl_cap          = ttk.Label(content, text='IN')
        self.cmb_cap     = ttk.Combobox(content, values=cap_devs, width=15)
        lbl_pbk          = ttk.Label(content, text='OUT')
        self.cmb_pbk     = ttk.Combobox(content, values=pbk_devs, width=15)
        lbl_fs           = ttk.Label(content, text='rate')
        self.cmb_fs      = ttk.Combobox(content, values=srates, width=8)

        # - MEASURE SECTION
        lbl_meastitle    = ttk.Label(content, text='MEASURE:')
        lbl_ch           = ttk.Label(content, text='channels')
        self.cmb_ch      = ttk.Combobox(content, values=channels, width=4)
        lbl_meas         = ttk.Label(content, text='meas / ch')
        self.cmb_meas    = ttk.Combobox(content, values=takes,    width=4)
        lbl_sweep        = ttk.Label(content, text='sweep length')
        self.cmb_sweep   = ttk.Combobox(content, values=sweeps, width=7)
        lbl_scho         = ttk.Label(content, text='Smooth Schroeder')
        self.ent_scho    = ttk.Entry(content,                     width=5)

        # - REMOTE JACK SECTION
        lbl_rjack        = ttk.Label(content, text='Remote JACK:')
        lbl_rjaddr       = ttk.Label(content, text='addr:')
        self.ent_rjaddr  = ttk.Entry(content,                     width=15)
        lbl_rjuser       = ttk.Label(content, text='user:')
        self.ent_rjuser  = ttk.Entry(content,                     width=15)
        self.ent_rjuser.insert(0, 'paudio')

        # - RUN AREA
        lbl_run          = ttk.Label(content, text='RUN:')
        lbl_timer        = ttk.Label(content, text='auto timer (s):')
        self.cmb_timer   = ttk.Combobox(content, values=timers, width=7)
        self.chk_beep    = ttk.Checkbutton(content, text='beep',
                                                    variable=self.var_beep)
        self.btn_close   = ttk.Button(content, text='close', command=self.destroy)
        self.btn_go      = ttk.Button(content, text='Go!', command=self.go)

        # - BOTTOM MESSAGES SECTION
        frm_msg          = ttk.Frame(content, borderwidth=2, relief='solid')
        self.lbl_msg     = ttk.Label(frm_msg, textvariable=self.var_msg,
                                              font=(None, 32))

        ### GRID ARRANGEMENT
        content.grid(           row=0,  column=0, sticky=(N, S, E, W) )

        lbl_scard.grid(         row=0,  column=0, sticky=W, pady=5 )
        lbl_cap.grid(           row=1,  column=0, sticky=E )
        self.cmb_cap.grid(      row=1,  column=1)
        lbl_pbk.grid(           row=1,  column=2, sticky=E )
        self.cmb_pbk.grid(      row=1,  column=3)
        lbl_fs.grid(            row=1,  column=4, sticky=E )
        self.cmb_fs.grid(       row=1,  column=5)

        lbl_meastitle.grid(     row=2,  column=0, sticky=W, pady=5 )
        lbl_ch.grid(            row=3,  column=0, sticky=E )
        self.cmb_ch.grid(       row=3,  column=1, sticky=W )
        lbl_meas.grid(          row=3,  column=2, sticky=E )
        self.cmb_meas.grid(     row=3,  column=3, sticky=W )
        lbl_sweep.grid(         row=3,  column=4, sticky=E )
        self.cmb_sweep.grid(    row=3,  column=5, sticky=W )
        lbl_scho.grid(          row=4,  column=4, sticky=E )
        self.ent_scho.grid(     row=4,  column=5, sticky=W )

        lbl_rjack.grid(         row=5,  column=0, sticky=W, pady=5 )
        lbl_rjaddr.grid(        row=6,  column=0, sticky=E )
        self.ent_rjaddr.grid(   row=6,  column=1, sticky=W )
        lbl_rjuser.grid(        row=6,  column=2, sticky=E )
        self.ent_rjuser.grid(   row=6,  column=3, sticky=W )

        lbl_run.grid(           row=7,  column=0, sticky=W, pady=5 )
        lbl_timer.grid(         row=8,  column=1, sticky=E )
        self.cmb_timer.grid(    row=8,  column=2, sticky=W )
        self.chk_beep.grid(     row=8,  column=3 )
        self.btn_close.grid(    row=8,  column=4 )
        self.btn_go.grid(       row=8,  column=5 )

        frm_msg.grid(           row=9,  column=0, columnspan=6, pady=5, sticky=W+E )
        self.lbl_msg.grid(                        sticky=W )

        ### GRID RESIZING BEHAVIOR
        self.rowconfigure(      0, weight=1)
        self.columnconfigure(   0, weight=1)
        ncolumns, nrows = content.grid_size()
        for i in range(nrows):
            content.rowconfigure(   i, weight=1)
        for i in range(ncolumns):
            content.columnconfigure(i, weight=1)


    def handle_keypressed(self, event):
        print(f'(GUI) A key "{event.char}" was pressed: setting meas_trigger')
        self.meas_trigger.set()


    # MAIN MEAS procedure and SAVING of curves
    def do_measure_process(self, e_trigger, msg):

        # Disabling the GO! & CLOSE buttons while measuring
        self.btn_go['state'] = 'disabled'
        self.btn_close['state'] = 'disabled'

        # This is already disabled in rm, just a reminder,
        # becasue matplotlib cannot be threaded.
        rm.doPlot = False

        # Ordering the meas loop:
        rm.do_meas_loop(e_trigger, msg)

        # Smoothing curve and saving to disk:
        self.var_msg.set('SMOOTHING AND SAVING TO DISK ...')
        rm.do_averages()
        rm.do_save_averages()
        self.var_msg.set('DONE')

        # Re enabling the GO! & CLOSE button
        self.btn_go['state'] = 'normal'
        self.btn_close['state'] = 'normal'
        self.btn_close.focus_set()


    # CONFIGURE OPTIONS AND START MEASURING
    def go(self):

        # Optional printing rm.LS after configured
        def print_rm_LS_info():
            cap = rm.LS.sd.query_devices(rm.LS.sd.default.device[0])["name"]
            pbk = rm.LS.sd.query_devices(rm.LS.sd.default.device[1])["name"]
            print(f'cap:            {cap}')
            print(f'pbk:            {pbk}')
            print(f'fs:             {rm.LS.fs}')
            print(f'sweep length:   {rm.LS.N}')
            print(f'ch to meas:     {rm.channels}')
            print(f'takes:          {rm.numMeas}')
            print(f'auto timer:     {rm.timer}')
            print(f'Beep:           {rm.doBeep}')
            print(f'Schroeder:      {rm.Scho} (for smoothed meas curve)')

        # Configure roommeasure.LS STUFF as per given options
        def configure_rm_LS():

            # READING OPTIONS from main window
            cap         =   self.cmb_cap.get()
            pbk         =   self.cmb_pbk.get()
            fs          =   int(self.cmb_fs.get())

            channels    =   self.cmb_ch.get()
            takes       =   int(self.cmb_meas.get())
            sweeplength =   int(self.cmb_sweep.get())
            Scho        =   float(self.ent_scho.get())

            rjaddr      =   self.ent_rjaddr.get()
            rjuser      =   self.ent_rjuser.get()

            timer       =   self.cmb_timer.get()


            # PREPARING roommeasure.LS stuff as per given options:

            # - sound card
            rm.LS.fs = fs
            if not rm.LS.test_soundcard(cap, pbk):
                self.meas_running.set('SOUND CARD ERROR :-/')
                return

            # - measure
            rm.channels  = [c for c in channels]
            rm.numMeas   = takes
            rm.LS.N      = sweeplength

            # - smoothing
            rm.Scho         = Scho

            # - beeps:
            rm.beepL = rm.tools.make_beep(f=880, fs=rm.LS.fs)
            rm.beepR = rm.tools.make_beep(f=932, fs=rm.LS.fs)

            # - log-sweep as per the updated LS parameters
            rm.LS.prepare_sweep()

            # - a positive frequencies vector as per the selected N value.
            rm.freq = rm.np.linspace(0, int(rm.LS.fs/2), int(rm.LS.N/2))

            # - timer
            if timer.isdigit():
                rm.timer = int(timer)
            elif timer == 'manual':
                rm.timer = 0

            # - alert beeps
            if not self.var_beep.get():
                rm.doBeep = False


        # Configure roommeasure.LS STUFF as per given options
        configure_rm_LS()

        # Console info
        print_rm_LS_info()

        # THREADING THE MEAS PROCRESS (threading avoids blocking the Tk event loop)
        job_meas = threading.Thread( target = self.do_measure_process,
                                     args   = (self.meas_trigger,
                                               self.var_msg),
                                     daemon = True )
        job_meas.start()


if __name__ == '__main__':

    app = RoommeasureGUI()

    ### DEFAULT GUI PARAMETERS
    # - Sound card:
    app.cmb_cap.set(rm.LS.sd.query_devices( rm.LS.sd.default.device[0] )['name'])
    app.cmb_pbk.set(rm.LS.sd.query_devices( rm.LS.sd.default.device[1] )['name'])
    app.cmb_fs.set('48000')
    # - Logsweep length:
    app.cmb_sweep.set(str(2**15))
    # - Channels to measure:
    app.cmb_ch.set('LR')
    # - Takes per channel:
    app.cmb_meas.set('2')
    # - Auto timer for measuring progress:
    app.cmb_timer.set('3')
    # - Alert before measuring:
    app.var_beep.set(1)
    # - Schroeder freq for smoothing result curve:
    app.ent_scho.insert(0, '200')

    # LAUNCH GUI
    app.mainloop()

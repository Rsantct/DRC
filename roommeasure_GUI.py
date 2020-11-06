#!/usr/bin/env python3
""" This is a Tkinter based GUI to running DRC/roommeasure.py
"""
import os
UHOME = os.path.expanduser("~")

from tkinter import *
from tkinter import ttk

# https://tkdocs.com/tutorial/fonts.html#images
from PIL import ImageTk, Image

import threading

import roommeasure as rm

# https://matplotlib.org/faq/howto_faq.html#working-with-threads
# We need to call matplotlib.use('Agg') to replace the regular display backend
# (e.g. 'Mac OSX') by the dummy one 'Agg' in order to avoid incompatibility
# when threading the matplotlib from the imported rm.LS on this GUI.
# Notice below that we dont order plt.show() but plt.close('all').
rm.LS.matplotlib.use('Agg')


class RoommeasureGUI(Tk):

    ### MAIN WINDOW
    def __init__(self):

        super().__init__()  # this initiates the parent class Tk in order to
                            # make self a typical root = Tk()

        self.screenW = self.winfo_screenwidth()
        self.screenH = self.winfo_screenheight()

        #  Main window location
        self.xpos = int(self.screenW / 12)
        self.ypos = int(self.screenH / 12)
        self.geometry(f'+{self.xpos}+{self.ypos}')
        self.title('DRC/roommeasure.py GUI')

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
        sweeps   = [2**15, 2**16, 2**17, 2**18]
        timers   = ['manual', '3', '5', '10']

        ### VARS
        self.var_beep     = IntVar()

        ### VARS SHARED WITH rm.do_meas_loop()
        self.meas_trigger = threading.Event()
        self.var_msg      = StringVar()

        ### MAIN CONFIG WIDGETS FRAME
        content =  ttk.Frame( self, padding=(10,10,12,12) )

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
        lbl_meas         = ttk.Label(content, text='mic locations')
        self.cmb_meas    = ttk.Combobox(content, values=takes,    width=4)
        lbl_sweep        = ttk.Label(content, text='sweep length')
        self.cmb_sweep   = ttk.Combobox(content, values=sweeps, width=7)
        lbl_scho         = ttk.Label(content, text='Smooth Schroeder')
        self.ent_scho    = ttk.Entry(content,                     width=5)

        # - REMOTE JACK SECTION
        lbl_rjack        = ttk.Label(content, text='REMOTE JACK\nLOUDSPEAKER:')
        lbl_rjaddr       = ttk.Label(content, text='addr')
        self.ent_rjaddr  = ttk.Entry(content,                     width=15)
        lbl_rjuser       = ttk.Label(content, text='user')
        self.ent_rjuser  = ttk.Entry(content,                     width=15)
        self.ent_rjuser.insert(0, 'paudio')
        lbl_rjpass       = ttk.Label(content, text='passwd')
        self.ent_rjpass  = ttk.Entry(content, show='*',           width=15)

        # - RUN AREA
        lbl_run          = ttk.Label(content, text='RUN:')
        lbl_folder       = ttk.Label(content, text='output folder: ~/rm/')
        self.ent_folder  = ttk.Entry(content,                     width=15)
        lbl_timer        = ttk.Label(content, text='auto timer (s)')
        self.cmb_timer   = ttk.Combobox(content, values=timers, width=6)
        self.chk_beep    = ttk.Checkbutton(content, text='beep',
                                                    variable=self.var_beep)
        self.btn_help    = ttk.Button(content, text='help', command=self.help)
        self.btn_close   = ttk.Button(content, text='close', command=self.destroy)
        self.btn_go      = ttk.Button(content, text='Go!', command=self.go)

        #### BOTTOM MESSAGES SECTION FRAME
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
        lbl_rjpass.grid(        row=6,  column=4, sticky=E )
        self.ent_rjpass.grid(   row=6,  column=5, sticky=W )

        lbl_run.grid(           row=7,  column=0, sticky=W, pady=5 )
        lbl_timer.grid(         row=8,  column=0, sticky=E )
        self.cmb_timer.grid(    row=8,  column=1, sticky=W )
        self.chk_beep.grid(     row=8,  column=2 )
        lbl_folder.grid(        row=8,  column=4, sticky=E )
        self.ent_folder.grid(   row=8,  column=5, sticky=W )
        self.btn_help.grid(     row=9,  column=3, sticky=E, pady=15  )
        self.btn_close.grid(    row=9,  column=4, sticky=E )
        self.btn_go.grid(       row=9,  column=5, sticky=E )

        frm_msg.grid(           row=10, column=0, columnspan=6, pady=10, sticky=W+E )
        self.lbl_msg.grid(                        sticky=W )

        ### GRID RESIZING BEHAVIOR
        self.rowconfigure(      0, weight=1)
        self.columnconfigure(   0, weight=1)
        ncolumns, nrows = content.grid_size()
        for i in range(nrows):
            content.rowconfigure(   i, weight=1)
        for i in range(ncolumns):
            content.columnconfigure(i, weight=1)


    # Display help in a new window
    def help(self):

        def arakiri():
            self.btn_help['state'] = 'normal'
            whlp.destroy()

        bgcolor     = 'light grey'
        bgcolortxt  = 'snow2'

        help_fname  = __file__.replace('_GUI.py', '.hlp')
        # this is for Mac OS users having renamed this script file
        help_fname  = help_fname.replace('_GUI.command', '.hlp')

        with open(help_fname, 'r') as f:
            tmp = f.read()

        whlp = Toplevel(bg=bgcolor)
        whlp.geometry('+250+100')

        fhlp = Frame(whlp, bg=bgcolor)
        fhlp.grid(row=0, column=0)

        txt_help = Text( fhlp, width=100, height=40, wrap=None, bg=bgcolortxt)
        txt_help.insert('end', tmp)
        yscroll  = ttk.Scrollbar(fhlp, orient='vertical',   command=txt_help.yview)
        xscroll  = ttk.Scrollbar(fhlp, orient='horizontal', command=txt_help.xview)
        txt_help['yscrollcommand'] = yscroll.set
        txt_help['xscrollcommand'] = xscroll.set

        but_ok   = Button(fhlp, text='OK', command=arakiri,
                                           highlightbackground=bgcolor)

        txt_help.grid(  row=0,  column=0,   pady=5 )
        but_ok.grid(    row=1,  column=0,   pady=5 )
        self.btn_help['state'] = 'disabled'


    # Show the rm.LS saved graphs, arranged on the screen
    def do_show_rm_LS_graphs(self):
        """ Showing the rm.LS saved graphs, arranged on the screen
        """

        def do_show_image(imagePath, row=0, col=0):
            """ displays an image
                row and col allows to array the image on the screen
            """
            # https://tkdocs.com/tutorial/fonts.html#images

            # Image window and container frame
            wimg = Toplevel()
            #wimg.title(os.path.basename(rm.folder))
            fimg = Frame(wimg)
            fimg.grid(row=0, column=0)

            # Resizing image to a reasonable height
            image = Image.open(imagePath)#.convert("RGB")
            iw, ih = image.size
            iaspect = iw / ih
            ih2 = int(self.screenH / 3)
            iw2 = int(ih2 * iaspect)
            image2 = image.resize((iw2, ih2), Image.ANTIALIAS)
            imageObj = ImageTk.PhotoImage(image2)

            # Arranging
            xoffset = self.xpos + 50
            yoffset = self.ypos
            wimg.geometry(f'+{xoffset + iw2 * col}+{yoffset + ih2 * row}')

            # http://effbot.org/pyfaq/why-do-my-tkinter-images-not-appear.htm (*)
            lbl_image = Label(fimg, image=imageObj)
            lbl_image.image = imageObj              # (*) trick: keep the reference
            lbl_image.grid(row=0, column=0)


        fnames = os.listdir(rm.folder)
        fnames.sort()
        row = 0
        col = 0
        found = False
        for ch in 'C', 'L', 'R':
            for fname in fnames:
                if fname[-4:] == '.png' and fname[0] == ch:
                    imagePath = f'{rm.folder}/{fname}'
                    do_show_image(imagePath, row, col)
                    found = True
                    col += 1
            if found:
                row +=1
                col = 0
                found = False


    def handle_keypressed(self, event):
        # Sets to True the event flag 'meas_trigger', so that a threaded
        # measuring in awaiting state could be triggered.
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

        # Ending the rm.LS dummy Agg backend plotting
        rm.LS.plt.close('all')

        # Showing the rm.LS saved graphs, arranged on the screen
        self.do_show_rm_LS_graphs()

        # Re enabling the GO! & CLOSE button
        self.btn_go['state'] = 'normal'
        self.btn_close['state'] = 'normal'
        self.btn_close.focus_set()


    # CONFIGURE OPTIONS AND START MEASURING
    def go(self):

        # Optional printing rm after configured
        def print_rm_info():
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
            print(f'Output folder   {rm.folder}')


        # Configure roommeasure stuff as per given options
        def configure_rm():

            # READING OPTIONS from main window
            cap         =   self.cmb_cap.get()
            pbk         =   self.cmb_pbk.get()
            fs          =   int(self.cmb_fs.get())

            channels    =   self.cmb_ch.get()
            takes       =   int(self.cmb_meas.get())
            sweeplength =   int(self.cmb_sweep.get())
            Scho        =   float(self.ent_scho.get())
            folder      =   self.ent_folder.get()

            rjaddr      =   self.ent_rjaddr.get()
            rjuser      =   self.ent_rjuser.get()
            rjpass      =   self.ent_rjpass.get()

            timer       =   self.cmb_timer.get()


            # PREPARING roommeasure.LS stuff as per given options:

            # - sound card
            rm.LS.fs = fs
            if not rm.LS.test_soundcard(cap, pbk):
                self.var_msg.set('SOUND CARD ERROR :-/')
                return

            # - measure
            rm.channels  = [c for c in channels]
            rm.numMeas   = takes
            rm.LS.N      = sweeplength

            # - smoothing
            rm.Scho         = Scho

            # - output folder
            if folder:
                rm.folder = f'{UHOME}/rm/{folder}'
            rm.prepare_frd_folder()
            #   updates the GUI w/ the real folder because subindex could be added
            self.ent_folder.delete(0, END)
            self.ent_folder.insert(0, os.path.basename(rm.folder))

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

            # - Remote Jack enabling
            if rjaddr and rjuser and rjpass:
                if rm.connect_to_remote_JACK(rjaddr, rjuser, rjpass):
                    self.var_msg.set('CONNECTED TO REMOTE JACK')
                else:
                    self.var_msg.set('UNABLE TO CONNECT TO REMOTE JACK')
                    return False

            return True


        # Configure roommeasure.LS STUFF as per given options
        if not configure_rm():
            return

        # Console info
        print_rm_info()

        # THREADING THE MEAS PROCRESS
        # (i) threading avoids blocking the Tk event-listen mainloop
        job_meas = threading.Thread( target = self.do_measure_process,
                                     args   = (self.meas_trigger,
                                               self.var_msg),
                                     daemon = True )
        job_meas.start()


class TestLogSweep2TFGUI(Tk):
    pass

if __name__ == '__main__':

    app = RoommeasureGUI()

    ### DEFAULT GUI PARAMETERS
    # - Sound card:
    app.cmb_cap.set(rm.LS.sd.query_devices( rm.LS.sd.default.device[0] )['name'])
    app.cmb_pbk.set(rm.LS.sd.query_devices( rm.LS.sd.default.device[1] )['name'])
    app.cmb_fs.set('48000')
    # - Logsweep length:
    app.cmb_sweep.set(str(2**17))
    # - Channels to measure ('L' or 'R' or 'LR')
    app.cmb_ch.set('LR')
    # - Locations per channel:
    app.cmb_meas.set('3')
    # - Auto timer for measuring progress ('manual' or 'N' seconds)
    app.cmb_timer.set('manual')
    # - Alert before measuring: ('1' or '0')
    app.var_beep.set(1)
    # - Schroeder freq for smoothing result curve:
    app.ent_scho.insert(0, '200')
    # - Output folder
    app.ent_folder.insert(0, 'meas')

    # LAUNCH GUI
    app.mainloop()

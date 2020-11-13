#!/usr/bin/env python3
""" This is a Tkinter based GUI to running DRC scripts
"""
from subprocess import Popen
from time import sleep
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
        self.title('DRC - GUI')

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
        self.var_validate = IntVar()
        self.var_poseq    = IntVar()

        ### VARS SHARED WITH rm.do_meas_loop()
        self.meas_trigger = threading.Event()
        self.var_msg      = StringVar()

        ### MAIN CONFIG WIDGETS FRAME
        content =  ttk.Frame( self, padding=(10,10,12,12) )

        # - SOUND CARD SECTION
        lbl_scard        = ttk.Label(content, text='SOUND CARD:',
                                              font=(None, 0, 'bold') )
        self.chk_validate= ttk.Checkbutton(content, text='validate test',
                                                    variable=self.var_validate,
                                                    command=self.enable_Go)
        lbl_cap          = ttk.Label(content, text='IN')
        self.cmb_cap     = ttk.Combobox(content, values=cap_devs, width=15)
        lbl_pbk          = ttk.Label(content, text='OUT')
        self.cmb_pbk     = ttk.Combobox(content, values=pbk_devs, width=15)
        lbl_fs           = ttk.Label(content, text='sample rate')
        self.cmb_fs      = ttk.Combobox(content, values=srates, width=8)
        btn_tsweep       = ttk.Button(content, text='test sweep',
                                               command=self.test_logsweep)

        # - MEASURE SECTION
        lbl_meas         = ttk.Label(content, text='MEASURE:',
                                              font=(None, 0, 'bold') )
        lbl_ch           = ttk.Label(content, text='channels')
        self.cmb_ch      = ttk.Combobox(content, values=channels, width=4)
        lbl_locat        = ttk.Label(content, text='mic locations')
        self.cmb_locat    = ttk.Combobox(content, values=takes,    width=4)
        lbl_sweep        = ttk.Label(content, text='sweep length')
        self.cmb_sweep   = ttk.Combobox(content, values=sweeps, width=7)

        # - PLOT SECTION
        lbl_plot         = ttk.Label(content, text='PLOT:',
                                              font=(None, 0, 'bold') )
        lbl_schro        = ttk.Label(content, text='smooth Schroeder')
        self.ent_schro   = ttk.Entry(content,                     width=5)

        # - REMOTE JACK SECTION
        lbl_rjack        = ttk.Label(content, text='MANAGE JACK\nLOUDSPEAKER:',
                                              font=(None, 0, 'bold') )
        lbl_rjaddr       = ttk.Label(content, text='addr')
        self.ent_rjaddr  = ttk.Entry(content,                     width=15)
        lbl_rjuser       = ttk.Label(content, text='user')
        self.ent_rjuser  = ttk.Entry(content,                     width=15)
        self.ent_rjuser.insert(0, 'paudio')
        lbl_rjpass       = ttk.Label(content, text='passwd')
        self.ent_rjpass  = ttk.Entry(content, show='*',           width=15)

        # - RUN AREA
        lbl_run          = ttk.Label(content, text='RUN:',
                                              font=(None, 0, 'bold') )
        lbl_folder       = ttk.Label(content, text='output folder: ~/rm/')
        self.ent_folder  = ttk.Entry(content,                     width=15)
        lbl_timer        = ttk.Label(content, text='auto timer (s)')
        self.cmb_timer   = ttk.Combobox(content, values=timers, width=6)
        self.chk_beep    = ttk.Checkbutton(content, text='beep',
                                                    variable=self.var_beep)
        self.btn_help    = ttk.Button(content, text='help', command=self.help)
        self.btn_close   = ttk.Button(content, text='close', command=self.destroy)
        self.btn_go      = ttk.Button(content, text='Go!', command=self.go)
        # needs to check [ ]validate
        self.btn_go['state'] = 'disabled'

        #### MESSAGES SECTION
        frm_msg          = ttk.Frame(content, borderwidth=2, relief='solid')
        self.lbl_msg     = ttk.Label(frm_msg, textvariable=self.var_msg,
                                              font=(None, 32))

        #### FILTER CALCULATION SECTION
        taps             = [2**14, 2**15, 2**16]

        lbl_drc          = ttk.Label(content, text='DRC-EQ FILTER:',
                                              font=(None, 0, 'bold') )
        lbl_reflev       = ttk.Label(content, text='ref. level (dB)')
        self.ent_reflev  = ttk.Entry(content,                 width=7)
        lbl_drcsch       = ttk.Label(content, text='Schroeder for smoothing transition')
        self.ent_drcsch  = ttk.Entry(content,                     width=5)
        lbl_poseq        = ttk.Label(content, text='allow positive limited EQ:')
        self.chk_poseq   = ttk.Checkbutton(content, variable=self.var_poseq)
        lbl_drcfs        = ttk.Label(content, text='FIR sample rate')
        self.cmb_drcfs   = ttk.Combobox(content, values=srates, width=8)
        lbl_drctaps      = ttk.Label(content, text='FIR taps')
        self.cmb_drctaps = ttk.Combobox(content, values=taps, width=7)
        self.btn_drc     = ttk.Button(content, text='calculate', command=self.drc)


        ### GRID ARRANGEMENT
        content.grid(           row=0,  column=0, sticky=(N, S, E, W) )

        lbl_scard.grid(         row=0,  column=0, sticky=W, pady=5 )
        btn_tsweep.grid(        row=0,  column=1, sticky=W, pady=5 )
        self.chk_validate.grid( row=0,  column=2 )
        lbl_cap.grid(           row=1,  column=0, sticky=E )
        self.cmb_cap.grid(      row=1,  column=1)
        lbl_pbk.grid(           row=1,  column=2, sticky=E )
        self.cmb_pbk.grid(      row=1,  column=3)
        lbl_fs.grid(            row=1,  column=4, sticky=E )
        self.cmb_fs.grid(       row=1,  column=5, sticky=W)
        lbl_sweep.grid(         row=2,  column=4, sticky=E )
        self.cmb_sweep.grid(    row=2,  column=5, sticky=W )

        lbl_meas.grid(          row=3,  column=0, sticky=W, pady=10 )
        lbl_ch.grid(            row=4,  column=0, sticky=E )
        self.cmb_ch.grid(       row=4,  column=1, sticky=W )
        lbl_locat.grid(         row=4,  column=2, sticky=E )
        self.cmb_locat.grid(    row=4,  column=3, sticky=W )

        lbl_plot.grid(          row=3,  column=4, sticky=W )
        lbl_schro.grid(         row=4,  column=4, sticky=E )
        self.ent_schro.grid(    row=4,  column=5, sticky=W )

        lbl_rjack.grid(         row=5,  column=0, sticky=W, pady=10 )
        lbl_rjaddr.grid(        row=6,  column=0, sticky=E )
        self.ent_rjaddr.grid(   row=6,  column=1, sticky=W )
        lbl_rjuser.grid(        row=6,  column=2, sticky=E )
        self.ent_rjuser.grid(   row=6,  column=3, sticky=W )
        lbl_rjpass.grid(        row=6,  column=4, sticky=E )
        self.ent_rjpass.grid(   row=6,  column=5, sticky=W )

        lbl_run.grid(           row=7,  column=0, sticky=W, pady=10 )
        lbl_timer.grid(         row=8,  column=0, sticky=E )
        self.cmb_timer.grid(    row=8,  column=1, sticky=W )
        self.chk_beep.grid(     row=8,  column=2 )
        lbl_folder.grid(        row=8,  column=4, sticky=E )
        self.ent_folder.grid(   row=8,  column=5, sticky=W )
        self.btn_help.grid(     row=9,  column=3, sticky=E, pady=15  )
        self.btn_close.grid(    row=9,  column=4, sticky=E )
        self.btn_go.grid(       row=9,  column=5, sticky=E )

        frm_msg.grid(           row=10, column=0, sticky=W+E, columnspan=6, pady=10 )
        self.lbl_msg.grid(                        sticky=W )

        lbl_drc.grid(           row=11, column=0, sticky=W, pady=10 )
        lbl_poseq.grid(         row=11, column=3, sticky=E, columnspan=2 )
        self.chk_poseq.grid(    row=11, column=5, sticky=W )
        lbl_reflev.grid(        row=12, column=0, sticky=E )
        self.ent_reflev.grid(   row=12, column=1, sticky=W )
        lbl_drcsch.grid(        row=12, column=2, sticky=E, columnspan=2 )
        self.ent_drcsch.grid(   row=12, column=4, sticky=W )
        lbl_drcfs.grid(         row=13, column=0, sticky=E, pady=10 )
        self.cmb_drcfs.grid(    row=13, column=1, sticky=W )
        lbl_drctaps.grid(       row=13, column=2, sticky=E )
        self.cmb_drctaps.grid(  row=13, column=3, sticky=W )
        self.btn_drc.grid(      row=13, column=5, sticky=E )



        ### GRID RESIZING BEHAVIOR
        self.rowconfigure(      0, weight=1)
        self.columnconfigure(   0, weight=1)
        ncolumns, nrows = content.grid_size()
        for i in range(nrows):
            content.rowconfigure(   i, weight=1)
        for i in range(ncolumns):
            content.columnconfigure(i, weight=1)


    def tmp_msgs(self, msgs, timeout=5, clear=False):
        """ simply displays a temporary messages sequence
        """
        for msg in msgs:
            self.var_msg.set(msg)
            sleep(timeout)
            if clear:
                self.var_msg.set('')


    def enable_Go(self):
        if self.var_validate.get():
            self.btn_go['state'] = 'normal'
        else:
            self.btn_go['state'] = 'disabled'


    def handle_keypressed(self, event):
        # Sets to True the event flag 'meas_trigger', so that a threaded
        # measuring in awaiting state could be triggered.
        self.meas_trigger.set()


    # Individual windows images display
    def do_show_image_at(self, imagePath, row=0, col=0, extraX=0, extraY=0,
                               resize=True):
        """ displays an image
            row and col allows to array the image on the screen,
            referred to the main window position.
        """
        print('(GUI) plotting', f'row:{row}', f'col:{col}', imagePath)

        # https://tkdocs.com/tutorial/fonts.html#images

        # Image window and container frame
        wimg = Toplevel()
        wimg.title(os.path.basename(imagePath))
        fimg = Frame(wimg)
        fimg.grid(row=0, column=0)

        # Resizing image to a reasonable height
        image = Image.open(imagePath)
        iw, ih = image.size
        iaspect = iw / ih
        if resize:
            ih2 = int(self.screenH / 3)
            iw2 = int(ih2 * iaspect)
            image2 = image.resize((iw2, ih2), Image.ANTIALIAS)
            imageObj = ImageTk.PhotoImage(image2)
        else:
            imageObj = ImageTk.PhotoImage(image)

        # On screen arranging
        xoffset = self.xpos + extraX
        yoffset = self.ypos + extraY
        if resize:
            wimg.geometry(f'+{xoffset + iw2 * col}+{yoffset + ih2 * row}')
        else:
            wimg.geometry(f'+{xoffset + iw  * col}+{yoffset + ih  * row}')

        # http://effbot.org/pyfaq/why-do-my-tkinter-images-not-appear.htm (*)
        lbl_image = Label(fimg, image=imageObj)
        lbl_image.image = imageObj              # (*) trick: keep the reference
        lbl_image.grid(row=0, column=0)


    # Joined images window display
    def do_show_images(self, png_tuples, wtitle=''):
        """ png_tuples:     A list of png tuples (pngPath, row, column)
            wtitle:         Container window title
        """

        # Joined images window and container frame
        wimg = Toplevel()
        if wtitle:
            wimg.title(wtitle)
        fimg = Frame(wimg)
        fimg.grid(row=0, column=0)

        for png_tuple in png_tuples:

            image_path, row, column = png_tuple

            # Resizing image to a reasonable height
            image = Image.open(image_path)
            iw, ih = image.size
            iaspect = iw / ih
            ih2 = int(self.screenH / 3)
            iw2 = int(ih2 * iaspect)
            image2 = image.resize((iw2, ih2), Image.ANTIALIAS)
            imageObj = ImageTk.PhotoImage(image2)

            # http://effbot.org/pyfaq/why-do-my-tkinter-images-not-appear.htm (*)
            lbl = ttk.Label(fimg, image=imageObj)
            lbl.image = imageObj              # (*) trick: keep the reference
            lbl.grid(row=row, column=column)


    def test_logsweep(self):

        def do_test():

            self.var_msg.set('TESTING SWEEP RECORDING ... (please wait)')
            self.btn_go['state'] = 'disabled'
            self.btn_close['state'] = 'disabled'

            rm.LS.do_meas()

            # Checking TIME CLEARANCE:
            if not rm.LS.TimeClearanceOK:
                self.var_msg.set('POOR TIME CLEARANCE! check sweep length')

            # Checking SPECTRUM LEVEL
            maxdB = max( 20 * rm.np.log10( rm.LS.DUT_FR ) )

            if  maxdB > 0.0:
                self.var_msg.set(f'CLIPPING DETECTED: +{round(maxdB,1)} dB')
            elif maxdB > -3.0:
                self.var_msg.set(f'CLOSE TO CLIPPING: {round(maxdB,1)} dB')
            elif maxdB < -20.0:
                self.var_msg.set(f'TOO LOW: {round(maxdB,1)} dB')
            else:
                self.var_msg.set(f'LEVEL OK: {round(maxdB,1)} dB')

            # Plotting test signals
            rm.LS.plot_system_response( png_folder=f'{UHOME}/rm/' )
            rm.LS.plt.close('all')

            self.btn_close['state'] = 'normal'
            #self.var_msg.set('')
            self.do_show_image_at( imagePath=f'{UHOME}/rm/system_response.png',
                                    resize=False )


        def configure_LS():

            # READING OPTIONS from main window
            cap         =   self.cmb_cap.get()
            pbk         =   self.cmb_pbk.get()
            fs          =   int(self.cmb_fs.get())
            sweeplength =   int(self.cmb_sweep.get())
            folder      =   self.ent_folder.get()

            # PREPARING roommeasure.LS stuff as per given options:
            # - sound card
            rm.LS.fs    = fs
            if not rm.LS.test_soundcard(cap, pbk):
                self.var_msg.set('SOUND CARD ERROR :-/')
                return False

            # - log-sweep as per the selected LS parameters
            rm.LS.N     = sweeplength
            rm.LS.prepare_sweep()

            # - Includes time clearance test
            rm.LS.checkClearence = True

            return True


        if not configure_LS():
            return

        # THREADING THE TEST PROCRESS
        # (i) threading avoids blocking the Tk event-listen mainloop
        job_test = threading.Thread( target = do_test,
                                     daemon = True )
        job_test.start()


    # Display help in a new window
    def help(self):

        def arakiri():
            self.btn_help['state'] = 'normal'
            whlp.destroy()

        bgcolor     = 'light grey'
        bgcolortxt  = 'snow2'

        help_fname  = f'{os.path.dirname(__file__)}/roommeasure.hlp'
        # this is for Mac OS users having renamed this script file
        help_fname  = help_fname.replace('_GUI.command', '.hlp')

        with open(help_fname, 'r') as f:
            tmp = f.read()

        whlp = Toplevel(bg=bgcolor)
        whlp.geometry('+350+100')

        fhlp = Frame(whlp, bg=bgcolor)
        fhlp.grid(row=0, column=0)

        txt_help = Text( fhlp, width=100, height=40, wrap=None, bg=bgcolortxt)
        txt_help.insert('end', tmp)
        yscroll  = ttk.Scrollbar(fhlp, orient='vertical',   command=txt_help.yview)
        xscroll  = ttk.Scrollbar(fhlp, orient='horizontal', command=txt_help.xview)
        txt_help['yscrollcommand'] = yscroll.set
        txt_help['xscrollcommand'] = xscroll.set
        txt_help.grid( row=0, column=0, pady=5 )

        fbtn = Frame(whlp, bg=bgcolor)
        fbtn.grid( row=1, column=0 )

        btn_ok   = Button(fbtn, text='OK', command=arakiri,
                                           highlightbackground=bgcolor)
        btn_ok.grid(    row=1,  column=0,   pady=5 )
        self.btn_help['state'] = 'disabled'


    # Show the rm.LS saved graphs, arranged on the screen
    def do_show_rm_LS_graphs(self, joined=False):
        """ Showing the rm.LS saved graphs, arranged on the screen
        """
        png_tuples = []
        fnames = os.listdir(rm.folder)
        fnames.sort()
        row = 0
        col = 0
        found = False
        for ch in 'C', 'L', 'R':
            for fname in fnames:
                if fname[-4:] == '.png' and fname[0] == ch:
                    imagePath = f'{rm.folder}/{fname}'
                    if not joined:
                        self.do_show_image_at(imagePath, row, col, extraX=50)
                    else:
                        png_tuples.append( (imagePath, row, col) )
                    found = True
                    row += 1
            if found:
                col +=1
                row = 0
                found = False


        # OPC: Individual images display
        if not joined:
            return

        # OPC: Joined images window and container frame
        else:
            self.do_show_images( png_tuples,
                                 wtitle=f'~/rm/{os.path.basename(rm.folder)}' )


    # MAIN MEAS procedure and SAVING of curves
    def do_measure_process(self, e_trigger, msg):

        # Disabling the GO! & CLOSE buttons while measuring
        self.btn_go['state'] = 'disabled'
        self.btn_close['state'] = 'disabled'

        # Ordering the meas loop:
        rm.do_meas_loop(e_trigger, msg)

        # Smoothing curve and saving to disk:
        self.var_msg.set('SMOOTHING AND SAVING TO DISK ...')
        rm.do_averages()
        self.var_msg.set('DONE')

        # Ending the rm.LS dummy Agg backend plotting
        rm.LS.plt.close('all')

        # Showing the rm.LS saved graphs, arranged on the screen
        self.do_show_rm_LS_graphs(joined=True)

        # Re enabling the GO! & CLOSE button
        self.btn_go['state'] = 'normal'
        self.btn_close['state'] = 'normal'
        self.btn_close.focus_set()


    # CONFIGURE OPTIONS AND START MEASURING
    def go(self):

        # Optional printing rm settings
        def print_rm_info():
            cap = rm.LS.sd.query_devices( rm.LS.sd.default.device[0],
                                          kind='input'                )['name']
            pbk = rm.LS.sd.query_devices(rm.LS.sd.default.device[1],
                                          kind='output'                )['name']
            print(f'cap:            {cap}')
            print(f'pbk:            {pbk}')
            print(f'fs:             {rm.LS.fs}')
            print(f'sweep length:   {rm.LS.N}')
            print(f'ch to meas:     {rm.channels}')
            print(f'takes:          {rm.numMeas}')
            print(f'auto timer:     {rm.timer}')
            print(f'Beep:           {rm.doBeep}')
            print(f'Schroeder:      {rm.Schro} (for smoothed meas curve)')
            print(f'Output folder   {rm.folder}')


        # Configure roommeasure and LS stuff as per given options
        def configure_rm():

            # READING OPTIONS from main window
            cap         =   self.cmb_cap.get()
            pbk         =   self.cmb_pbk.get()
            fs          =   int(self.cmb_fs.get())

            channels    =   self.cmb_ch.get()
            takes       =   int(self.cmb_locat.get())
            sweeplength =   int(self.cmb_sweep.get())
            Schro       =   float(self.ent_schro.get())
            folder      =   self.ent_folder.get()

            rjaddr      =   self.ent_rjaddr.get()
            rjuser      =   self.ent_rjuser.get()
            rjpass      =   self.ent_rjpass.get()

            timer       =   self.cmb_timer.get()


            # PREPARING roommeasure.LS stuff as per given options:

            # - sound card
            rm.LS.fs        = fs
            test_sc = rm.LS.test_soundcard(cap, pbk)
            if test_sc != 'ok':
                self.var_msg.set( test_sc )
                return

            # - measure
            rm.channels     = [c for c in channels]
            rm.numMeas      = takes
            rm.LS.N         = sweeplength

            # - smoothing
            rm.Schro         = Schro

            # - output folder
            if folder:
                rm.folder   = f'{UHOME}/rm/{folder}'
            rm.prepare_frd_folder()
            #   updates the GUI w/ the real folder because subindex could be added
            self.ent_folder.delete(0, END)
            self.ent_folder.insert(0, os.path.basename(rm.folder))

            # - beeps:
            rm.beepL        = rm.tools.make_beep(f=880, fs=rm.LS.fs)
            rm.beepR        = rm.tools.make_beep(f=932, fs=rm.LS.fs)

            # - log-sweep as per the updated LS parameters
            rm.LS.prepare_sweep()

            # - timer
            if timer.isdigit():
                rm.timer    = int(timer)
            elif timer == 'manual':
                rm.timer    = 0

            # - alert beeps
            if not self.var_beep.get():
                rm.doBeep   = False

            # - Remote Jack enabling
            if rjaddr and rjuser and rjpass:
                if rm.connect_to_remote_JACK(rjaddr, rjuser, rjpass):
                    self.var_msg.set('CONNECTED TO REMOTE JACK')
                else:
                    self.var_msg.set('UNABLE TO CONNECT TO REMOTE JACK')
                    return False

            return True


        # Configure roommeasure and LS stuff as per given options
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


    # CALCULATE DRC
    def drc(self):

        # fs
        fs      = self.cmb_drcfs.get()

        # taps
        tmp    = self.cmb_drctaps.get()
        taps_exp = int( rm.np.log2( int(tmp) ) )

        # ref level
        if self.ent_reflev.get() == 'auto':
            reflev = 0

        elif self.ent_reflev.get().replace('.','') \
             .replace('+','').replace('-','').isdecimal():
            reflev  = self.ent_reflev.get()

        else:
            self.ent_reflev.delete(0, END)
            self.ent_reflev.insert(0, 'auto')
            print(f'(GUI) bad ref. level (dB)')
            return

        # Schroedr freq
        if self.ent_drcsch.get().replace('.','').isdecimal:
            schro  = self.ent_drcsch.get()
        else:
            self.ent_drcsch.delete(0, END)
            self.ent_drcsch.insert(0, '200')
            schro  = 200

        # positive limited eq
        if self.var_poseq.get():
            noPos = False
        else:
            noPos = True

        # Channels
        tmp= self.cmb_ch.get()
        channels = [c for c in tmp]

        # roomEQ command line args
        args = f'-fs={fs} -e={taps_exp} -schro={schro} -doFIR'

        if reflev:
            args += f' -ref={reflev}'

        if noPos:
            args += f' -noPos'

        rEQ_path = f'{UHOME}/DRC/roomEQ.py'

        frd_paths = ''
        for ch in channels:
            frd_paths += f' "{UHOME}/rm/{self.ent_folder.get()}/{ch}_avg.frd"'

        cmdline = f'{rEQ_path} {frd_paths.strip()} {args}'

        # display temporary messages
        msgs = (f'running roomEQ ...',
                f'DRC FIR saved under ~/rm/{self.ent_folder.get()}'
                f'/{self.cmb_drcfs.get()}' )

        job_tmp_msgs = threading.Thread( target=self.tmp_msgs,
                                        args=(msgs, 5),
                                        daemon=True               )
        job_tmp_msgs.start()

        # Running roomEQ.py in a shell in backgroung ... ...
        print( f'(GUI) running: {cmdline}' )
        Popen( cmdline, shell=True)


if __name__ == '__main__':

    app = RoommeasureGUI()

    ### DEFAULT GUI PARAMETERS

    # - Sound card:
    app.cmb_cap.set(rm.LS.sd.query_devices( rm.LS.sd.default.device[0],
                                            kind = 'input'             )['name'])
    app.cmb_pbk.set(rm.LS.sd.query_devices( rm.LS.sd.default.device[1],
                                            kind = 'output'            )['name'])
    app.cmb_fs.set('48000')

    # - Logsweep length:
    app.cmb_sweep.set(str(2**17))
    # - Channels to measure ('L' or 'R' or 'LR')
    app.cmb_ch.set('LR')
    # - Locations per channel:
    app.cmb_locat.set('3')
    # - Auto timer for measuring progress ('manual' or 'N' seconds)
    app.cmb_timer.set('manual')
    # - Alert before measuring: ('1' or '0')
    app.var_beep.set(1)
    # - Schroeder freq for smoothing result curve:
    app.ent_schro.insert(0, '200')
    # - Output folder
    app.ent_folder.insert(0, 'meas')

    # - DRC:
    app.cmb_drcfs.set('44100')
    app.cmb_drctaps.set(str(2**15))
    app.ent_reflev.insert(0, 'auto')
    app.ent_drcsch.insert(0, '200')
    app.var_poseq.set(1)

    # LAUNCH GUI
    app.mainloop()

#!/usr/bin/env python3
""" This is a Tkinter based GUI to running Rsantct/DRC scripts
"""
from tkinter import *
from tkinter import ttk, filedialog, messagebox, font
# https://tkdocs.com/tutorial/fonts.html#images
from PIL import ImageTk, Image

from subprocess import Popen
import threading
from time import sleep
import glob
import os
import sys
import platform

UHOME = os.path.expanduser("~")
sys.path.append(f'{UHOME}/DRC')

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

        # Getting default font size for late relative usage
        f = font.nametofont('TkTextFont')
        self.curr_font_size = f.actual()['size']

        # A patch to set background colors for children windows working in Mac OS
        # https://stackoverflow.com/questions/1529847/how-to-change-the-foreground-or-background-colour-of-a-tkinter-button-on-mac-os
        self.bgcolor = self['background']
        ttk.Style().configure('bgPatch.TFrame',  background=self.bgcolor)
        ttk.Style().configure('bgPatch.TButton', background=self.bgcolor)
        # bold button
        ttk.Style().configure('bbPatch.TButton', font=(None, 0, 'bold'))

        #  Main window location
        self.screenW = self.winfo_screenwidth()
        self.screenH = self.winfo_screenheight()
        self.xpos = int(self.screenW / 12)
        self.ypos = int(self.screenH / 12)
        self.geometry(f'+{self.xpos}+{self.ypos}')
        self.title('Rsantct/DRC')

        ### EVENTS HANDLING
        self.bind('<Key>', self.handle_keypressed)

        ### AVAILABLE COMBOBOX OPTIONS
        cap_devs = [ x['name'] for x in rm.LS.sd.query_devices()[:] \
                               if x['max_input_channels'] >= 2 ]
        pbk_devs = [ x['name'] for x in rm.LS.sd.query_devices()[:] \
                               if x['max_output_channels'] >= 2 ]
        srates   = ['44100', '48000', '88200', '96000']
        channels = ['C', 'L', 'R', 'LR']
        takes    = list(range(1,21))
        sweeps   = [2**15, 2**16, 2**17, 2**18]
        timers   = ['manual', '3', '5', '10']
        taps     = [2**13, 2**14, 2**15, 2**16]

        ### VARS
        self.var_beep       = IntVar()
        self.var_validate   = IntVar()
        self.var_poseq      = IntVar()
        self.var_wLowSpan   = IntVar()
        self.var_wHighSpan  = IntVar()
        self.var_wLowFc     = IntVar()
        self.var_wHighFc    = IntVar()

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
        lbl_sweep        = ttk.Label(content, text='sweep length')
        self.cmb_sweep   = ttk.Combobox(content, values=sweeps, width=7)
        lbl_pbk          = ttk.Label(content, text='OUT')
        self.cmb_pbk     = ttk.Combobox(content, values=pbk_devs, width=15)
        lbl_fs           = ttk.Label(content, text='sample rate')
        self.cmb_fs      = ttk.Combobox(content, values=srates, width=8)
        btn_tsweep       = ttk.Button(content, text='test sweep',
                                               command=self.test_logsweep)

        # - REMOTE JACK SECTION
        lbl_rjack        = ttk.Label(content, text='MANAGE JACK LOUDSPEAKER:',
                                              font=(None,
                                                    self.curr_font_size - 2,
                                                    'bold') )
        lbl_rjaddr       = ttk.Label(content, text='addr')
        self.ent_rjaddr  = ttk.Entry(content,                     width=15)
        lbl_rjuser       = ttk.Label(content, text='user')
        self.ent_rjuser  = ttk.Entry(content,                     width=15)
        self.ent_rjuser.insert(0, 'paudio')
        lbl_rjpass       = ttk.Label(content, text='passwd')
        self.ent_rjpass  = ttk.Entry(content, show='*',           width=15)

        # - MEASURE SECTION
        lbl_meas         = ttk.Label(content, text='MEASURE:',
                                              font=(None, 0, 'bold') )
        lbl_ch           = ttk.Label(content, text='channels')
        self.cmb_ch      = ttk.Combobox(content, values=channels, width=6)
        lbl_locat        = ttk.Label(content, text='mic locations')
        self.cmb_locat   = ttk.Combobox(content, values=takes,    width=4)

        # - PLOT SECTION
        lbl_plot         = ttk.Label(content, text='PLOT:',
                                              font=(None,
                                                    self.curr_font_size - 2,
                                                    'bold') )
        lbl_schro        = ttk.Label(content, text='smooth Schroeder')
        self.ent_schro   = ttk.Entry(content,                     width=5)

        # - RUN SECTION
        btn_selfol       = ttk.Button(content, text='RESULTS FOLDER:',
                                               command=self.selectfolder,
                                               style='bbPatch.TButton' )
        self.ent_folder  = ttk.Entry(content,                     width=18)
        lbl_timer        = ttk.Label(content, text='auto timer (s)')
        self.cmb_timer   = ttk.Combobox(content, values=timers, width=6)
        self.chk_beep    = ttk.Checkbutton(content, text='beep',
                                                    variable=self.var_beep)
        self.btn_help    = ttk.Button(content, text='help', command=self.help_meas)
        self.btn_close   = ttk.Button(content, text='close', command=self.destroy)
        self.btn_go      = ttk.Button(content, text='Go!', command=self.go)
        # needs to check [ ]validate
        self.btn_go['state'] = 'disabled'

        #### MESSAGES SECTION
        frm_msg          = ttk.Frame(content, borderwidth=2, relief='solid')
        self.lbl_msg     = ttk.Label(frm_msg, textvariable=self.var_msg,
                                              font=(None, 32))

        #### FILTER CALCULATION SECTION
        lbl_drc          = ttk.Label(content, text='DRC-EQ FILTER:',
                                              font=(None, 0, 'bold') )
        lbl_reflev       = ttk.Label(content, text='ref. level (dB)')
        self.ent_reflev  = ttk.Entry(content,                 width=6)
        lbl_drcsch       = ttk.Label(content, text='Schroeder for smoothing transition')
        self.ent_drcsch  = ttk.Entry(content,                     width=5)
        lbl_poseq        = ttk.Label(content, text='allow positive limited EQ:')
        self.chk_poseq   = ttk.Checkbutton(content, variable=self.var_poseq)
        self.btn_eqhlp   = ttk.Button(content, text='help', command=self.help_eq)
        btn_eqlim        = ttk.Button(content, text='EQ limits', command=self.eq_limits)
        lbl_drcfs        = ttk.Label(content, text='FIR sample rate')
        self.cmb_drcfs   = ttk.Combobox(content, values=srates, width=6)
        lbl_drctaps      = ttk.Label(content, text='FIR taps')
        self.cmb_drctaps = ttk.Combobox(content, values=taps, width=7)
        lbl_wavbits      = ttk.Label(content, text='wav bit depth')
        self.cmb_wavbits = ttk.Combobox(content, values=(16,32), width=6)
        self.btn_drc     = ttk.Button(content, text='calculate', command=self.drc)


        ### GRID ARRANGEMENT
        content.grid(           row=0,  column=0, sticky=(N, S, E, W) )

        # sound card
        lbl_scard.grid(         row=0,  column=0, sticky=W, pady=6 )
        btn_tsweep.grid(        row=0,  column=1, sticky=W)
        self.chk_validate.grid( row=0,  column=2 )
        lbl_cap.grid(           row=1,  column=0, sticky=E )
        self.cmb_cap.grid(      row=1,  column=1)
        lbl_pbk.grid(           row=1,  column=2, sticky=E )
        self.cmb_pbk.grid(      row=1,  column=3)
        lbl_fs.grid(            row=1,  column=4, sticky=E )
        self.cmb_fs.grid(       row=1,  column=5, sticky=W)
        lbl_sweep.grid(         row=2,  column=4, sticky=E )
        self.cmb_sweep.grid(    row=2,  column=5, sticky=W )

        # manage jack
        lbl_rjack.grid(         row=3,  column=0, sticky=W, columnspan=2, pady=6 )
        lbl_rjaddr.grid(        row=4,  column=0, sticky=E )
        self.ent_rjaddr.grid(   row=4,  column=1, sticky=W )
        lbl_rjuser.grid(        row=4,  column=2, sticky=E )
        self.ent_rjuser.grid(   row=4,  column=3, sticky=W )
        lbl_rjpass.grid(        row=4,  column=4, sticky=E )
        self.ent_rjpass.grid(   row=4,  column=5, sticky=W )

        # measure
        lbl_meas.grid(          row=5,  column=0, sticky=W, pady=6 )
        lbl_ch.grid(            row=6,  column=0, sticky=E )
        self.cmb_ch.grid(       row=6,  column=1, sticky=W )
        lbl_locat.grid(         row=6,  column=2, sticky=E )
        self.cmb_locat.grid(    row=6,  column=3, sticky=W )

        # plot
        lbl_plot.grid(          row=5,  column=4, sticky=W )
        lbl_schro.grid(         row=6,  column=4, sticky=E )
        self.ent_schro.grid(    row=6,  column=5, sticky=W )

        # run
        lbl_timer.grid(         row=8,  column=0, sticky=E, pady=6)
        self.cmb_timer.grid(    row=8,  column=1, sticky=W )
        self.chk_beep.grid(     row=8,  column=3, sticky=W )
        btn_selfol.grid(        row=9,  column=0, sticky=E, pady=6 )
        self.ent_folder.grid(   row=9,  column=1, sticky=W )
        self.btn_help.grid(     row=9,  column=4, sticky=W )
        self.btn_go.grid(       row=9,  column=5, sticky=E )
        self.btn_close.grid(    row=10, column=5, sticky=E, pady=6 )

        # messages window
        frm_msg.grid(           row=11, column=0, sticky=W+E, columnspan=6,
                                                              pady=12 )
        self.lbl_msg.grid(                        sticky=W )

        # drc eq
        lbl_drc.grid(           row=12, column=0, sticky=W, pady=6 )
        lbl_poseq.grid(         row=12, column=1, sticky=E, columnspan=2 )
        self.chk_poseq.grid(    row=12, column=3, sticky=W )
        btn_eqlim.grid(         row=12, column=3, sticky=E )
        lbl_reflev.grid(        row=13, column=0, sticky=E )
        self.ent_reflev.grid(   row=13, column=1, sticky=W )
        lbl_drcsch.grid(        row=13, column=2, sticky=E, columnspan=2 )
        self.ent_drcsch.grid(   row=13, column=4, sticky=W )
        lbl_drcfs.grid(         row=14, column=0, sticky=E )
        self.cmb_drcfs.grid(    row=14, column=1, sticky=W )
        lbl_drctaps.grid(       row=14, column=2, sticky=E )
        self.cmb_drctaps.grid(  row=14, column=3, sticky=W )
        lbl_wavbits.grid(       row=15, column=0, sticky=E )
        self.cmb_wavbits.grid(  row=15, column=1, sticky=W )
        self.btn_eqhlp.grid(    row=15, column=4, sticky=W )
        self.btn_drc.grid(      row=15, column=5, sticky=E )


        ### GRID RESIZING BEHAVIOR
        self.rowconfigure(      0, weight=1)
        self.columnconfigure(   0, weight=1)
        ncolumns, nrows = content.grid_size()
        for i in range(nrows):
            content.rowconfigure(   i, weight=1)
        for i in range(ncolumns):
            content.columnconfigure(i, weight=1)


    def open_file_manager(self, path):
        if platform.system() == "Darwin":
            Popen(["open", path])
        else:
            Popen(["xdg-open", path])


    def tmp_msgs(self, msgs, timeout=5, clear=False):
        """ simply displays a temporary messages sequence
        """
        for msg in msgs:
            self.var_msg.set(msg)
            sleep(timeout)
            if clear:
                self.var_msg.set('')


    def selectfolder(self):
        tmp = filedialog.askdirectory(initialdir=f'{UHOME}')
        if tmp:
            rm.folder = tmp
            # updates the GUI
            self.ent_folder.delete(0, END)
            self.ent_folder.insert(0, rm.folder.replace(UHOME, '')[1:])
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
            image2 = image.resize((iw2, ih2), Image.LANCZOS)
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
            image2 = image.resize((iw2, ih2), Image.LANCZOS)
            imageObj = ImageTk.PhotoImage(image2)

            # http://effbot.org/pyfaq/why-do-my-tkinter-images-not-appear.htm (*)
            lbl = ttk.Label(fimg, image=imageObj)
            lbl.image = imageObj              # (*) trick: keep the reference
            lbl.grid(row=row, column=column)


    def test_logsweep(self):

        def do_test(png_folder):

            self.var_msg.set('TESTING SWEEP RECORDING ... (please wait)')
            self.btn_go['state'] = 'disabled'
            self.btn_close['state'] = 'disabled'

            rm.LS.do_meas()

            # Checking TIME CLEARANCE:
            if not rm.LS.TimeClearanceOK:
                self.var_msg.set('POOR TIME CLEARANCE! check sweep length')

            # Checking SPECTRUM LEVEL
            _, mag = rm.LS.DUT_FRD
            maxdB = max( 20 * rm.np.log10( mag ) )

            if  maxdB > 0.0:
                self.var_msg.set(f'CLIPPING DETECTED: +{round(maxdB,1)} dB')
            elif maxdB > -3.0:
                self.var_msg.set(f'CLOSE TO CLIPPING: {round(maxdB,1)} dB')
            elif maxdB < -20.0:
                self.var_msg.set(f'TOO LOW: {round(maxdB,1)} dB')
            else:
                self.var_msg.set(f'LEVEL OK: {round(maxdB,1)} dB')

            # Plotting test signals to png
            rm.LS.plot_system_response( png_folder=png_folder )
            rm.LS.plt.close('all')

            self.btn_close['state'] = 'normal'
            #self.var_msg.set('')
            self.do_show_image_at( imagePath=f'{png_folder}/sweep_response.png',
                                    resize=False )


        def configure_LS():

            # READING OPTIONS from main window
            cap         =   self.cmb_cap.get()
            pbk         =   self.cmb_pbk.get()
            fs          =   int(self.cmb_fs.get())
            sweeplength =   int(self.cmb_sweep.get())

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


        # Prepare results png folder
        folder = self.ent_folder.get()

        if not folder:
            self.var_msg.set('Please set  [ RESULTS FOLDER: ]')
            return

        folder = f'{UHOME}/{folder}'
        if not os.path.exists(folder):
            os.makedirs(folder)

        # Configure LS
        if not configure_LS():
            return

        # Do test
        # (i) threading avoids blocking the Tk event-listen mainloop
        job_test = threading.Thread( target = do_test,
                                     args   = (folder,),
                                     daemon = True )
        job_test.start()


    # Help for measure
    def help_meas(self):
        self.helpW( help_text=rm.__doc__, disable_items=[self.btn_help])


    # Displays help in a new window
    def helpW(self, help_text, disable_items=[]):

        def normalize_items(dummy=None):
            for item in disable_items:
                item['state'] = 'normal'

        def arakiri():
            normalize_items()
            whlp.destroy()

        bgcolor     = self.bgcolor
        bgcolortxt  = 'snow2'

        whlp = Toplevel(bg=bgcolor)
        whlp.geometry('+350+100')
        whlp.bind('<Destroy>', normalize_items)

        fhlp = ttk.Frame( whlp, style='bgPatch.TFrame' )
        fhlp.grid(row=0, column=0)

        txt_help = Text( fhlp, width=100, height=40, wrap=None, bg=bgcolortxt)
        txt_help.insert('end', help_text)

        yscroll  = ttk.Scrollbar(fhlp, orient='vertical',   command=txt_help.yview)
        xscroll  = ttk.Scrollbar(fhlp, orient='horizontal', command=txt_help.xview)
        txt_help['yscrollcommand'] = yscroll.set
        txt_help['xscrollcommand'] = xscroll.set

        btn_ok   = ttk.Button(fhlp, text='OK', command=arakiri,
                                               style='bgPatch.TButton' )

        txt_help    .grid(   row=0, column=0, pady=5 )
        btn_ok      .grid(   row=1, column=0, pady=5 )

        for item in disable_items:
            item['state'] = 'disabled'


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
                                 wtitle=f'~/{os.path.basename(rm.folder)}' )


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
        self.var_msg.set('DONE! Ready to calculate the DRC-EQ filters below')

        # Ending the rm.LS dummy Agg backend plotting
        rm.LS.plt.close('all')

        # Showing the rm.LS saved graphs, arranged on the screen
        self.do_show_rm_LS_graphs(joined=True)

        # Open desktop file manager
        self.open_file_manager(f'{UHOME}/{self.ent_folder.get()}')

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
                rm.folder   = f'{UHOME}/{folder}'
                # - alerting on existing .frd files under <folder>
                if os.path.exists(rm.folder):
                    if glob.glob(f'{rm.folder}/*.frd'):
                        ans = messagebox.askyesno(
                            message='Are you sure to overwrite *.frd files?',
                            icon='question',
                            title=f'Output folder: {rm.folder}')
                        if not ans:
                            return False
                else:
                    rm.prepare_frd_folder()
            else:
                self.var_msg.set('Please set  [ RESULTS FOLDER: ]')
                return False


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


    # Help for DRC-EQ
    def help_eq(self):
        from roomEQ import __doc__ as eq_doc
        self.helpW( help_text=eq_doc, disable_items=[self.btn_eqhlp])


    # Configure DRC EQ LIMITS (roomEQ command line args)
    def eq_limits(self):

        def update_and_close():
            self.var_wLowSpan   .set( int(self.cmb_eqwLspan.get() ) )
            self.var_wHighSpan  .set( int(self.cmb_eqwHspan.get() ) )
            self.var_wLowFc     .set( int(self.ent_eqwLFc.get()   ) )
            self.var_wHighFc    .set( int(self.ent_eqwHFc.get()   ) )
            wEq.destroy()


        wEq = Toplevel( bg=self.bgcolor )
        wEq.geometry( f'+{self.xpos}+{self.ypos}' )

        fEq = ttk.Frame( wEq, style='bgPatch.TFrame', padding=(10,10,12,12) )
        fEq.grid()

        # widgets (using gray text color for unusual settings)
        lbl_eqwLspan        = ttk.Label(fEq, text='w_low left span (def: 5 octaves)',
                                             foreground='gray33')
        self.cmb_eqwLspan   = ttk.Combobox(fEq, values=(5, 10, 15, 20), width=4)

        lbl_eqwHspan        = ttk.Label(fEq, text='w_high right span (def: 5 octaves)')
        self.cmb_eqwHspan   = ttk.Combobox(fEq, values=(5, 10, 15, 20), width=4)

        lbl_eqwLFc          = ttk.Label(fEq, text='window low Fc (def: 1000 Hz)',
                                             foreground='gray33',
                                             font=(None, 10, ''))
        self.ent_eqwLFc     = ttk.Entry(fEq, width=5,
                                             font=(None, 10, ''))

        lbl_eqwHFc          = ttk.Label(fEq, text='window high Fc (def: 1000 Hz)',
                                             foreground='gray33',
                                             font=(None, 10, ''))
        self.ent_eqwHFc     = ttk.Entry(fEq, width=5,
                                             font=(None, 10, ''))

        btn_ok              = ttk.Button( fEq, text='OK', command=update_and_close,
                                                          style='bgPatch.TButton' )

        # grid arrangement
        lbl_eqwLspan        .grid( row=0,  column=0, sticky=E, pady=5 )
        self.cmb_eqwLspan   .grid( row=0,  column=1, sticky=W )

        lbl_eqwLFc          .grid( row=1,  column=0, sticky=E, pady=5 )
        self.ent_eqwLFc     .grid( row=1,  column=1, sticky=W )

        lbl_eqwHFc          .grid( row=2,  column=0, sticky=E, pady=5 )
        self.ent_eqwHFc     .grid( row=2,  column=1, sticky=W )

        lbl_eqwHspan        .grid( row=3,  column=0, sticky=E, pady=5 )
        self.cmb_eqwHspan   .grid( row=3,  column=1, sticky=W )

        btn_ok              .grid( row=4,  column=1, pady=5 )

        # auto fill values as per global variables
        self.cmb_eqwLspan.set( self.var_wLowSpan.get() )
        self.cmb_eqwHspan.set( self.var_wHighSpan.get() )
        self.ent_eqwLFc.insert(0, self.var_wLowFc.get() )
        self.ent_eqwHFc.insert(0, self.var_wHighFc.get() )


    # CALCULATE DRC
    def drc(self):

        # fs
        fs      = self.cmb_drcfs.get()

        # taps
        taps     = int(self.cmb_drctaps.get())
        taps_exp = int( rm.np.log2(taps) )

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

        # Schroeder freq
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
        args =  f'-fs={fs} -e={taps_exp} -schro={schro} -doPCM -doWAV'
        args += f' -WAVfmt=int{self.cmb_wavbits.get()}'
        args += f' -wLoct={self.var_wLowSpan.get()}'
        args += f' -wLfc={self.var_wLowFc.get()}'
        args += f' -wHfc={self.var_wHighFc.get()}'
        args += f' -wHoct={self.var_wHighSpan.get()}'

        if reflev:
            args += f' -ref={reflev}'

        if noPos:
            args += f' -noPos'

        rEQ_path = __file__.replace( os.path.basename(__file__), 'roomEQ.py')

        frd_paths = ''
        for ch in channels:
            frd_path   = f'{UHOME}/{self.ent_folder.get()}/{ch}_avg.frd'
            if os.path.isfile(frd_path):
                frd_paths += f' "{frd_path}"'
            else:
                self.var_msg.set(f'\'{ch}\' channel avg freq. response file NOT found')
                return

        cmdline = f'{rEQ_path} {frd_paths.strip()} {args}'

        # display temporary messages
        msgs = (f'running roomEQ ...',
                f'DRC FIRs at: {self.ent_folder.get().split("/")[-1]}'
                f'/{self.cmb_drcfs.get()}'
                f'_{int(taps/1024)}Ktaps'
                )

        job_tmp_msgs = threading.Thread( target=self.tmp_msgs,
                                        args=(msgs, 5),
                                        daemon=True               )
        job_tmp_msgs.start()

        # Running roomEQ.py in a shell in backgroung ... ...
        print( f'(GUI) running: {cmdline}' )
        Popen( cmdline, shell=True)

        # Open desktop file manager
        self.open_file_manager(f'{UHOME}/{self.ent_folder.get()}')


def macOS_launcher_patch():
    cmd =   'osascript -e'
    cmd +=  ' \'tell application "Terminal" to set miniaturized of'
    cmd +=  ' every window whose name contains "DRC_GUI" to true\''
    Popen(cmd, shell=True)


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
    #app.ent_folder.insert(0, 'roommeas')

    # - DRC:
    app.cmb_drcfs.set('44100')
    app.cmb_drctaps.set(str(2**15))
    app.ent_reflev.insert(0, 'auto')
    app.ent_drcsch.insert(0, '200')
    app.var_poseq.set(1)
    app.var_wLowSpan.set(5)
    app.var_wHighSpan.set(5)
    app.var_wLowFc.set(1000)    # Low window midband centered at 1000 Hz
    app.var_wHighFc.set(1000)   # idem
    app.cmb_wavbits.set(32)


    ### A DESKTOP PATCH to minimize the terminal launcher
    if platform.system() == 'Darwin':
        macOS_launcher_patch()
    elif platform.system() == 'Linux':
        # pending
        pass


    # LAUNCH GUI
    app.mainloop()

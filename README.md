# DRC

Yet another DRC FIR toolkit ;-)

This soft is intended to measure a loudspeaker's in-room response, then calculate a FIR filter to perform DRC equalization (digital room correction).

The applied test signal will be a **log sweep** chirp.

You'll ned to use a convolver inserted in the loudspeakers signal path, as **Brutefir** in Linux, or a generic **reverb plugin** as Wave's IR1 in a DAW, or into a hardware convolver as miniDSP.

For more details, see **[doc folder](https://github.com/Rsantct/DRC/tree/master/doc)**


<img src="https://github.com/Rsantct/DRC/blob/master/doc/images/roommeasure_GUI_screen_1.png" width="640">


<img src="https://github.com/Rsantct/DRC/blob/master/doc/images/roomEQ_hard-modes.png" width="800">


<img src="https://github.com/Rsantct/DRC/blob/master/doc/images/file_manager.png" width="400">


<img src="https://github.com/Rsantct/DRC/blob/master/doc/images/DRC_in_action.png" width="480">







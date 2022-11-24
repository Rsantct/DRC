## The measurement MIC

You need some sound card + measurement MIC in order to take in room measurements.

My current setup is a cheap Behringer UM-2 USB sound card and ECM800 mic.

Wiring is as indicated running `logsweep2TF.py --help`:

    out L ------>-------  DUT (loudspeaker analog line input)

    in  L ------<-------  MIC
    
    out R --->---+
                 |        Optional reference loop for
    in  R ---<---+        time clearance checkup.


## Laptop built-in MIC

I recently tested a 2021 Macbook Pro built-in microphone, and the recording is actually decent compared to an ECM800 for unsophisticated room measurements.

You only need to face the Mac keyboard left plane towards the speaker.

So I updated `logsweep2TF.py` to accept a mono input sound device, like the MBP built-in microphone.

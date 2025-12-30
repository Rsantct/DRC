#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'Rsantct.DRC', yet another DRC FIR toolkit.

"""
    Generates a set of optimized Parametric EQ from a given target filter.

    The target filter can be given in 3 flavours:

        - FRD: freq response data (mag vs freq text file)

        - FIR: a pcm impulse response previously windowed

                - a raw float32 file (for example .bin .pcm .f32)
                - a wav file (.wav)

    Usage:

        filter2peq.py  --frd=path/to/FRDfile  [more options]

        filter2peq.py  --fir=path/to/FIRfile  [more options]

            more options are:

                --fs=FS
                     FS     default 44100 (mandatory option for raw PCM files)

                --ch=C      L,R,0,1 needed if a .wav FIR is given

                --offset=N  force N dB to move the magnitude curve to set its
                            flat region at 0 dB. Default is automatic offset.

                --numpeq=N
                      -n=N  number of PEQ sections, default to 6

                --mg=G      minimum gain to include a PEQ filter in the set,
                            default is 0.0

                --plot
                 -p         show plot (always will save plot .png to disk)

                --silent
                 -s         omit terminal json printout

    Output:

        All output files are placed in the same directory as the given filter file path.

        - PEQ set file .json
        - plot of results and its .png figure file
        - stdout will also printout the json result
"""

import  os
import  sys
import  json
import  yaml
import  numpy as np
import  scipy.signal    as      signal
from    scipy.optimize  import  minimize     # woooooow!
from    scipy.io        import  wavfile
import  matplotlib.pyplot as    plt
from    fmt import Fmt

VALID_FS = (44100, 88200, 48000, 96000, 192000)


def detect_channel_from_filter_filename():
    """ returns 'L', 'R' or 'chX'
    """

    ch = ''

    tmp = set_name.split('.')

    if 'L' in tmp:
        ch = 'L'
    elif 'R' in tmp:
        ch = 'R'

    if not ch:

        tmp = set_name.split('_')

        if 'L' in tmp:
            ch = 'L'
        elif 'R' in tmp:
            ch = 'R'
        else:
            ch = 'chX'

    return ch


def get_PEQ_mag(freq, fc, Q, gain_db, fs):
    """ Calculate the magnitude curve in dB of a Peaking EQ filter.

        freq: a dense, preferable logarithmic frequency axis to render the curve
    """

    # A must be lineal
    A = 10**(gain_db / 40)
    w0 = 2 * np.pi * fc / fs
    alpha = np.sin(w0) / (2 * Q)

    # Filter coeffs (RBJ Cookbook)
    b = [1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A]
    a = [1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A]

    w_eval = 2 * np.pi * freq / fs
    _, h = signal.freqz(b, a, worN=w_eval)

    return 20 * np.log10( np.maximum(np.abs(h), 1e-5) )


def get_PEQ_pha(freq, fc, Q, gain_db, fs):
    """ Calculate the phase curve of a Peaking EQ filter, in degrees.

        freq: a dense, preferable logarithmic frequency axis to render the curve
    """
    A = 10**(gain / 40)
    w0 = 2 * np.pi * fc / fs
    alpha = np.sin(w0) / (2 * Q)

    b = [1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A]
    a = [1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A]

    w_eval = 2 * np.pi * freq / fs
    _, h = signal.freqz(b, a, worN=w_eval)

    return np.degrees( np.angle(h) )


def get_PEQs_mag(freq, peq_list, fs):
    """ Calculate the total magnitude response curve accumulated
        from a list of PEQ filters, in dB.

        freq: a dense, preferable logarithmic frequency axis to render the curve
    """

    mag = np.zeros_like(freq)

    for peq in peq_list:
        fc, Q, gain = peq['fc'], peq['q'], peq['gain']
        mag += get_PEQ_mag(freq, fc, Q, gain, fs)

    return mag


def get_PEQs_pha(freq, peq_list, fs):
    """ Calculate the total phase curve accumulated
        from a list of PEQ filters, in degrees.

        freq: a dense, preferable logarithmic frequency axis to render the curve
    """
    phase = np.zeros_like(freq)

    for peq in peq_list:
        fc, Q, gain = peq['fc'], peq['q'], peq['gain']
        phase += get_PEQ_mag(freq, fc, Q, gain, fs)

    return phase


def objective_function(params, f_target, m_target, fs, num_peqs):

    total_mag = np.zeros_like(f_target)

    for i in range(num_peqs):
        fc, Q, gain = params[i*3 : (i+1)*3]
        total_mag += get_PEQ_mag(f_target, fc, Q, gain, fs)

    # --- WEIGHTS: The core of low-frequency resolution ---
    # A vector of weights that decays with frequency
    weights = 1.0 / np.log10(f_target)
    # Extra reinforcement for sub-bass (< 100Hz)
    weights[f_target < 100] *= 5.0

    error = np.sum(weights * (m_target - total_mag)**2)

    return error


def get_optimized_peqs_from_frd(frd, fs, num_peqs):
    """ frd:        a magnitude vs freq response curve np.array [Hz : dB]
        fs:         freq of sampling
        num_peqs:   desired number of peqs tu emulate the frd
    """

    def params_to_json(params, min_gain=min_gain):
        """ Convert the parameters into an organized JSON.

            params: Array shaped (num_peqs, 3), each row having [Fc, Q, Gain]

            gain_
        """

        eq_config = {

            "metadata": {
                "description": "Peaking EQ filters",
                "fs": fs,
                "max num of PEQ sections": num_peqs,
                "mini PEQ gain": min_gain,
                "comments": f'Magnitude curve has been moved {moved_dB} dB to set the flat region at 0 dB'
            },

            "filters": []
        }

        i = 1
        for p in params:

            filter_data = {
                "type": "peaking",
                "fc":   round(float(p[0]), 2),
                "q":    round(float(p[1]), 3),
                "gain": round(float(p[2]), 2)
            }

            if abs( filter_data['gain'] ) > min_gain:
                filter_data["id"] = i
                eq_config["filters"].append(filter_data)
                i += 1

        eq_config["metadata"]["final num of PEQ sections"] = i

        return eq_config


    def add_eq_config_advanced(eq_config, freq, target):

        comments = """
            rmse_bass_db: if very low (e.g., < 0.2 dB), it means the bass emulation is almost perfect. rmse_treble_db: if higher, it reflects the 'permission' you gave the algorithm to be less accurate in the high frequencies.
        """

        def calculate_metrics(freq, target, calc):
            """Calcula el error cuadrático medio por bandas."""
            error = target - calc

            # Máscaras para graves y agudos
            mask_low   = freq < 200
            mask_high  = freq >= 200

            rmse_total = np.sqrt(np.mean(error**2))
            rmse_low   = np.sqrt(np.mean(error[mask_low]**2))
            rmse_high  = np.sqrt(np.mean(error[mask_high]**2))

            return {
                "rmse_total_db":  round(float(rmse_total), 4),
                "rmse_bass_db":   round(float(rmse_low),   4),      # < 200Hz
                "rmse_treble_db": round(float(rmse_high),  4)       # > 200Hz
            }


        mag_calc  = get_PEQs_mag(freq, eq_config['filters'], fs)
        # pha_calc = get_PEQs_pha(freq, eq_config['filters'], fs)  # unused

        metrics = calculate_metrics(freq, target, mag_calc)

        eq_config['analysis'] = {
            'residual_error':    metrics,
            'units':            'decibels (dB)',
            'comments':         comments.strip()
        }

        return eq_config


    def add_pAudio_format(eq_config, ch):
        """ pAudio lspk.yml block, example:

                drc:

                    mesa-SoundID:

                        type:       fir
                        flat_gain:  -5.5
                        posit_gain:  0.0


                    mesa-IIR:

                        L:
                            0:
                                type: Biquad
                                parameters:
                                    type:   Peaking
                                    freq:   40
                                    gain:   3.0
                                    q:      1.0
                            1:
                                ...
                            ...
                        R:
                            ...

        """

        drc_name = set_name

        if drc_name.lower() == 'drc':
            drc_name += '_NO_NAME'

        pAudio = {  'info':         'pAudio YAML filters',
                    'drc_name':     drc_name,
                    'yaml_block':   ''
                 }

        if ch != 'chX':
            pAudio['comments'] = f'channel \'{ch}\' detected from filter filename'
        else:
            pAudio['comments'] = 'channel not detected from filter filename'

        # tmp is a dict to be converted in a yaml_block
        tmp = { 'drc': {drc_name: { ch: {} } } }

        for i, peq in enumerate(eq_config['filters']):

            fc, Q, gain = peq['fc'], peq['q'], peq['gain']

            tmp['drc'][drc_name][ch][i] = {
                'type': 'Biquad',
                'parameters': {
                    'type':   'Peaking',
                    'freq':   fc,
                    'gain':   gain,
                    'q':      Q
                }
            }

        pAudio['yaml_notice'] = 'Use the parser \'jq -r .pAudio.yaml_block\' to dump the yaml_block'
        pAudio['yaml_block'] = yaml.dump(tmp, indent=4, sort_keys=False, default_flow_style=False)
        # debug
        #print(pAudio['yaml_block'])

        eq_config['pAudio'] = pAudio


    def add_CamillaDSP_format(eq_config, ch):
        """ pAudio lspk.yml block, example:

                filters:
                  drc_mesa-IIR_L_0:
                    description: null
                    parameters:
                      freq: 40.0
                      gain: 3.0
                      q: 1.0
                      type: Peaking
                    type: Biquad
                  drc_mesa-IIR_L_1:
                    ..
                  drc_mesa-IIR_L_2:
                    ..
                  ..
        """

        drc_name = set_name

        if drc_name.lower() == 'drc':
            drc_name += '_NO_NAME'

        CamillaDSP = { 'info':      'CamillaDSP YAML filters',
                    'drc_name':     drc_name,
                    'yaml_block':   ''
                    }

        if ch != 'chX':
            CamillaDSP['comments'] = f'channel \'{ch}\' detected from filter filename'
        else:
            CamillaDSP['comments'] = 'channel not detected from filter filename'


        # tmp is a dict to be converted in a yaml_block
        tmp = { 'filters': {} }

        for i, peq in enumerate(eq_config['filters']):

            fc, Q, gain = peq['fc'], peq['q'], peq['gain']

            tmp['filters'][f'{drc_name}_{i}'] = {
                'type': 'Biquad',
                'parameters': {
                    'type':   'Peaking',
                    'freq':   fc,
                    'gain':   gain,
                    'q':      Q
                }
            }

        CamillaDSP['yaml_notice'] = 'Use the parser \'jq -r .CamillaDSP.yaml_block\' to dump the yaml_block'
        CamillaDSP['yaml_block'] = yaml.dump(tmp, indent=2, sort_keys=False, default_flow_style=False)
        # debug
        #print(CamillaDSP['yaml_block'])

        eq_config['CamillaDSP'] = CamillaDSP


    # <frd> is a 2 columns np.array [Hz : dB]
    hz_raw = frd[:, 0]
    db_raw = frd[:, 1]

    # 1. f_target debe estar en escala logarítmica para balancear el peso
    f_target = np.geomspace(20, 20000, 500)
    m_target = np.interp(f_target, hz_raw, db_raw)

    # 2. Inicialización inteligente (Repartir fc por octavas)
    initial_guess = []
    f_centers = np.geomspace(50, 15000, num_peqs)
    for fc in f_centers:
        initial_guess.extend([fc, 1.4, 0.0]) # [fc, Q, gain]

    # 3. Restricciones (Bounds) para mantener los filtros "musicales"
    bounds = []
    for _ in range(num_peqs):
        bounds.append((   20,  20000))  # fc
        bounds.append((  0.1,  7.2  ))  # Q 7.2 ~ BW_oct 0.2 enough for room modes correction
        bounds.append((-18.0,  3.0  ))  # Gain: -18 dB to +3 dB

    # 4. Optimización
    #    The optimization result is represented as a OptimizeResult object.
    #    Important attributes are:
    #        - x the solution array,
    #        - success a Boolean flag indicating if the optimizer exited successfully
    #        - message which describes the cause of the termination.
    res = minimize(
        objective_function,
        initial_guess,
        args=(f_target, m_target, fs, num_peqs),
        bounds=bounds,
        method='L-BFGS-B',
        options={'ftol': 1e-9}
    )

    # Extraer los resultados que se encuentran en `res.x`
    # vienen dados en forma de un array de valores float
    # de longitud = num_peqs * 3, que deberemos agrupar
    # para tener las tuplas (Fc ,Q , Gain) de cada filtro
    res_params = res.x.reshape(num_peqs, 3)
    eq_config  = params_to_json( res_params )

    add_eq_config_advanced(eq_config, f_target, m_target)

    add_pAudio_format(eq_config, ch)

    add_CamillaDSP_format(eq_config, ch)

    return eq_config


def visualize_eq_results(frd, peq_set):
    """ Compare and plot both responses:
            frd:        a magnitude vs freq response curve
            peq_set:    a set o Peaking EQ that emulates 'frd'
    """

    # the span in dB for the Error graph
    db_error_span = 4.0

    # extract freq and mag dB from the given frd 2 columns array
    freq  = frd[:, 0]
    mag   = frd[:, 1]

    # Fs and peaking EQ filters
    fs    = peq_set.get('metadata', {}).get('fs', 0)
    peqs  = peq_set["filters"]

    # 2. Reconstruir la respuesta total
    # A dense, logarithmic frequency axis for the graph
    f_plot  = np.geomspace(20, 20000, 1000)
    mag_peq = get_PEQs_mag(f_plot, peqs, fs)


    # 3. Interpolar la original para calcular el error exacto en f_plot
    mag_interp = np.interp(f_plot, freq, mag)
    error = mag_peq - mag_interp

    # 4. Crear la visualización OJO se comparte el eje X
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=False,
                                   gridspec_kw={'height_ratios': [3, 1]})

    # Gráfica Principal: Magnitud
    ax1.semilogx(freq,   mag,     label='Target curve',  color='gray', alpha=0.5, linewidth=2)
    ax1.semilogx(f_plot, mag_peq, label='PEQ emulation', color='blue', linestyle='--')
    ax1.set_xlim(20, 20000)
    ax1.set_xticks([20, 50, 100, 500, 1000, 5000, 10000, 20000])
    ax1.set_xticklabels([20, 50, 100, 500, 1000, 5000, 10000, 20000])
    ax1.tick_params(labelbottom=True)
    ax1.set_ylim(-36, 12)
    ax1.set_xlabel('Freq (Hz)')
    ax1.set_ylabel('Gain (dB)')
    tmp = ' auto' if not mag_offset else ''
    ax1.set_title(f'Emulation with PEQ and low freq accuracy (ch: {ch}, offset {moved_dB} dB{tmp})')
    ax1.grid(True, which="both", linestyle="-", alpha=0.3)
    ax1.legend()

    # Gráfica de Error (Residuo)
    ax2.semilogx(f_plot, error, color='red', linewidth=1)
    ax2.set_xlim(20, 20000)
    ax2.tick_params(labelbottom=False)
    ax2.set_ylim([-db_error_span, db_error_span])
    ax2.set_ylabel('Error (dB)')
    ax2.fill_between(f_plot, error, color='red', alpha=0.1)
    ax2.grid(True, which="both", linestyle="-", alpha=0.3)
    ax2.set_title('Residual error', fontsize=10)

    plt.tight_layout()

    # will be dumped after closing plots
    plt.savefig(f'{json_path}.png')

    if do_plot:
        plt.show()
    else:
        plt.close('all')


def load_wav(filepath, ch, normalize = True):

    if ch == 'L':
        ch = 0
    elif ch == 'R':
        ch = 1
    else:
        ch = int(ch)

    fs, data = wavfile.read(filepath)

    if len(data.shape) == 1:
        fir_coeffs = data
    else:
        fir_coeffs = data[:, ch]

    if normalize:

        if data.dtype == np.int16:
            fir_coeffs = fir_coeffs / 32768.0

        elif data.dtype == np.int32:
            fir_coeffs = fir_coeffs / 2147483648.0

    return fir_coeffs, fs


def load_fir_file(fir_path, ch):
    """ 'ch' only used for wav channel selection
    """

    # fs will be set from the wav file if so
    global fs

    fname, fext = os.path.splitext( os.path.basename(fir_path) )

    if fext == '.wav':

        h, fs = load_wav(fir_path, ch)

    else:
        # for PCM raw FIRs, fs must be explicited at command line
        if not fs in VALID_FS:
            print(__doc__)
            print(f'FS must be in {VALID_FS}')
            sys.exit()

        with open(fir_path, 'rb') as f:
            h = np.fromfile(f, dtype=np.float32)

    return h


def fir2frd(h, fs, freq=None):

    if not freq:
        n_points = 1000
        freq = np.logspace(np.log10(10), np.log10(fs / 2), n_points)
    else:
        n_points = freq.size

    w_rad = 2 * np.pi * freq / fs

    w, h_resp = signal.freqz(h, worN=w_rad)

    mag_db  = 20 * np.log10(np.abs(h_resp))
    pha_deg = np.angle(h_resp, deg=True)

    return freq, mag_db, pha_deg


def get_avg_flat_region(frd, hz_ini=300, hz_end=3000):
    """
        <frd>   a 2D columns array  [ Hz : dB ]

        returns the avg flat region value in dB into the given freq range
    """

    # Create 500 log points from  `hz_ini` to `hz_end`
    hz_interp = np.geomspace(hz_ini, hz_end, 100)

    # Interpolate the dB values ​​for those new points
    hz = frd[:,0]
    db = frd[:,1]

    # As log spaced audio freq points can be widely separated, it is
    # preferred to interpolate over the logarithm of the frequency.
    db_interp = np.interp(np.log10(hz_interp), np.log10(hz), db)

    # Average the interpolated values
    avg = np.mean(db_interp)

    return avg


def move_flat_region(frd):

    flat_offset_dB = get_avg_flat_region(frd, 200, 4000)
    frd[:, 1] -= flat_offset_dB

    return frd, round(-flat_offset_dB, 2)


if __name__ == "__main__":

    # Read commmand line options
    mag_offset  = 0.0
    num_peqs    = 6                 # Number of Peaking EQ bands
    min_gain    = 0.0               # Gain threshold to discard a PEQ
    fs          = 0
    frd_path    = ''
    fir_path    = ''
    ch          = ''                # Needed for .wav FIR files
    do_plot     = False
    silent      = False

    try:
        for opc in sys.argv[1:]:

            if '-s' in opc:
                silent = True

            elif '-offset=' in opc:
                mag_offset = float(opc.split('=')[-1])

            elif '-mg=' in opc:
                min_gain = float(opc.split('=')[-1])

            elif '-ch=' in opc:
                ch = opc.split('=')[-1]

            elif '-n=' in opc:
                num_peqs = int( opc.split('=')[-1] )

            elif '-frd=' in opc:
                frd_path = opc.split('frd=')[-1]

            elif '-fir=' in opc:
                fir_path = opc.split('fir=')[-1]

            elif '-fs=' in opc:
                fs = int( opc.split('fs=')[-1] )

            elif '-p' in opc:
                do_plot = True

            else:

                if opc.isdigit():
                    fs = int( opc )

                else:
                    print(f'BAD option: {opc}')
                    sys.exit()

    except Exception as e:
        print(f'BAD option \'{opc}\': {str(e)}')
        sys.exit()


    # Check file path
    if frd_path:

        if os.path.isfile( frd_path ):

            frd = np.loadtxt(frd_path)

            if not fs:
                fs = 48000

            json_dir  = os.path.dirname(frd_path)
            set_name  = os.path.splitext( os.path.basename(frd_path) )[0]
            json_path = f'{json_dir}/{set_name}.json'

        else:
            print(__doc__)
            print('Needs a FRD file')
            sys.exit()

    elif fir_path:

        if os.path.isfile( fir_path ):

            fir = load_fir_file( fir_path, ch )

            fir_freq, fir_mag, _ = fir2frd(fir, fs)

            frd = np.column_stack((fir_freq, fir_mag))

            json_dir  = os.path.dirname(fir_path)
            set_name  = os.path.splitext( os.path.basename(fir_path) )[0]
            json_path = f'{json_dir}/{set_name}.json'

        else:
            print(__doc__)
            print('Needs a pcm FIR file')
            sys.exit()

    else:
        print(__doc__)
        sys.exit()


    # Check FS
    if not fs in VALID_FS:
        print(f'FS must be in {VALID_FS}')
        sys.exit()

    # Check channel
    if not ch:
        ch = detect_channel_from_filter_filename()

    valid_channels = ('L', 'R')

    if not ch in valid_channels:
        print(__doc__)
        print(f'\nA valid channel {valid_channels} is needed for .wav FIR\n')
        sys.exit()


    if mag_offset:
        frd[:, 1] += mag_offset
        moved_dB = mag_offset
    else:
        frd, moved_dB = move_flat_region(frd)


    ########################
    # Solve the optimization
    peq_config = get_optimized_peqs_from_frd(frd, fs, num_peqs)
    ########################


    # Terminal printout
    if not silent:
        print(json.dumps(peq_config, indent=4))

    # Graph results vs original curve
    visualize_eq_results(frd, peq_config)

    # Save to JSON file
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(peq_config, f, indent=4, ensure_ascii=False)


#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'Rsantct.DRC', yet another DRC FIR toolkit.

import  os
import  sys
import  json
import  yaml
import  numpy               as      np
import  scipy.signal        as      signal
from    scipy.io            import  wavfile
import  matplotlib.pyplot   as      plt
from    fmt                 import  Fmt

VALID_FS        = (44100, 88200, 48000, 96000, 192000)
VALID_CHANNELS  = ('L', 'R')


def detect_channel_from_set_name(set_name):
    """ returns 'L', 'R' or '-'
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
            ch = '-'

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

    return np.column_stack((freq, mag_db, pha_deg))


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


def load_frd(frd_path):
    """ direct load a np colum stack of frequencies and magnitudes
    """
    return np.loadtxt(frd_path)


def load_fir_file(fir_path, ch, fs):
    """ 'ch' only used for wav channel selection
    """

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

    return h, fs


def load_peq_file(peq_path):

    with open(peq_path, 'r') as f:
        d = json.loads( f.read() )

    return d


def plot_peqs_vs_frd(frd, moved_dB, peqs, fs, ch='-', emulation_method='', png_path='',
                     do_plot=True, target_name='', peqs_name=''):
    """ Compare and plot both responses:

            frd:        A magnitude vs freq response curve

            moved_db:   dBs the original frd was moved
                        to perform the PEQ emulation

            peqs:       A set o Peaking EQ that emulates the frd.
                        Dict with values {'fc':  , 'q':   , 'gain':   }

            fs:         Fs to compute the PEQ responses

            ch:         Channel identifier (optional)
    """

    def get_points_peq(peqs):

        f = []
        m  = []
        for p in peqs:
            f.append(p['fc'])
            m.append(p['gain'])

        return f, m


    # the span in dB for the Error graph
    db_error_span = 5.0

    # extract freq and mag dB from the given frd 2 columns array
    freq  = frd[:, 0]
    mag   = frd[:, 1]

    # 2. Reconstruir la respuesta total
    # A dense, logarithmic frequency axis for the graph
    f_plot  = np.geomspace(20, 20000, 1000)
    mag_peq = get_PEQs_mag(f_plot, peqs, fs)

    peqs_f, peqs_m = get_points_peq(peqs)


    # 3. Interpolar la original para calcular el error exacto en f_plot
    mag_interp = np.interp(f_plot, freq, mag)
    error = mag_peq - mag_interp

    # 4. Crear la visualización OJO se comparte el eje X
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(7.5, 6),
        #sharex=False,
        gridspec_kw={'height_ratios': [3, 1]}
    )

    # Gráfica Principal: Magnitud
    offset_info = f', frd offset {moved_dB} dB' if moved_dB else ''
    emulation_method = f' ({emulation_method})' if emulation_method else ''

    ax1.semilogx(peqs_f, peqs_m,  'o', label=f'PEQs (tot {len(peqs_f)})', color='black')
    ax1.semilogx(freq,   mag,     label='Target curve',  color='gray', alpha=0.5, linewidth=2)
    ax1.semilogx(f_plot, mag_peq, label='PEQ emulation', color='blue', linestyle='--')
    ax1.set_xlim(20, 20000)
    ax1.set_xticks([20, 50, 100, 500, 1000, 5000, 10000, 20000])
    ax1.set_xticklabels([20, 50, 100, 500, 1000, 5000, 10000, 20000])
    ax1.set_ylim(-36, 12)
    ax1.set_xlabel('Freq (Hz)')
    ax1.set_ylabel('Gain (dB)')
    ax1.set_title(f'PEQ emulation{emulation_method} (ch: {ch}{offset_info})')
    ax1.grid(True, which="both", linestyle="-", alpha=0.3)

    if target_name:
        ax1.text(
            0.95, 0.13,                 # Coordenadas (x, y) de 0 a 1
            target_name,                # El contenido
            transform=ax1.transAxes,    # Clave: usa coordenadas del subplot, no de los datos
            ha='right',                 # Alineación horizontal a la derecha
            va='bottom',                # Alineación vertical inferior
            fontsize=10,                # Tamaño de fuente
            color='gray',               # Color
            bbox=dict(facecolor='white', alpha=0.5, edgecolor='none')   # Opcional: fondo
        )
    if peqs_name:
        ax1.text(
            0.95, 0.08,                 # Coordenadas (x, y) de 0 a 1
            peqs_name,                  # El contenido
            transform=ax1.transAxes,    # Clave: usa coordenadas del subplot, no de los datos
            ha='right',                 # Alineación horizontal a la derecha
            va='bottom',                # Alineación vertical inferior
            fontsize=10,                # Tamaño de fuente
            color='royalblue',          # Color
            bbox=dict(facecolor='white', alpha=0.5, edgecolor='none')   # Opcional: fondo
        )

    # ax1 barra estado recuperar las coordenadas x que se han perdido por los xticks
    ax1.fmt_xdata = lambda x: f"{x:g}"
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
    if png_path:
        plt.savefig(f'{png_path}.png')

    if do_plot:
        plt.show()
    else:
        plt.close('all')


def sort_peqs_list(list_of_peqs):

    # Sorted by Fc
    list_of_peqs.sort(key=lambda d: d["fc"])

    # Sequential id
    for i, _ in enumerate(list_of_peqs):
        list_of_peqs[i]["id"] = i

    return list_of_peqs


def add_pAudio_format(eq_config, drc_name, ch):
    """ pAudio lspk.yml block, example:

            drc:

                mesa-SoundID:

                    type:       fir
                    flat_gain:  -5.5
                    posit_gain:  0.0


                mesa-IIR:

                    L:
                        1:
                            type: Biquad
                            parameters:
                                type:   Peaking
                                freq:   40
                                gain:   3.0
                                q:      1.0
                        2:
                            ...
                        ...
                    R:
                        ...

    """

    pAudio = {  'info':         'pAudio YAML filters',
                'drc_name':     drc_name,
                'yaml_block':   ''
             }

    if ch in ('L', 'R'):
        pAudio['comments'] = f'channel \'{ch}\' detected from filter filename'
    else:
        pAudio['comments'] = 'channel not detected from filter filename'

    # tmp is a dict to be converted in a yaml_block
    tmp = { 'drc': {drc_name: { ch: {} } } }

    for i, peq in enumerate(eq_config['filters']):

        fc, Q, gain = peq['fc'], peq['q'], peq['gain']

        tmp['drc'][drc_name][ch][i + 1] = {
            'type': 'Biquad',
            'parameters': {
                'type':   'Peaking',
                'freq':   fc,
                'gain':   gain,
                'q':      Q
            }
        }

    pAudio['yaml_notice'] = 'Use the parser \'jq -r .pAudio.yaml_block\' to extract the yaml_block'
    pAudio['yaml_block'] = yaml.dump(tmp, indent=4, sort_keys=False, default_flow_style=False)
    # debug
    #print(pAudio['yaml_block'])

    eq_config['pAudio'] = pAudio


def add_CamillaDSP_format(eq_config, drc_name, ch):
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

    CamillaDSP = { 'info':      'CamillaDSP YAML filters',
                'drc_name':     drc_name,
                'yaml_block':   ''
                }

    if ch in ('L', 'R'):
        CamillaDSP['comments'] = f'channel \'{ch}\' detected from filter filename'
    else:
        CamillaDSP['comments'] = 'channel not detected from filter filename'


    # tmp is a dict to be converted in a yaml_block
    tmp = { 'filters': {} }

    for i, peq in enumerate(eq_config['filters']):

        fc, Q, gain = peq['fc'], peq['q'], peq['gain']

        tmp['filters'][f'drc_{drc_name}_{i + 1}'] = {
            'type': 'Biquad',
            'parameters': {
                'type':   'Peaking',
                'freq':   fc,
                'gain':   gain,
                'q':      Q
            }
        }

    CamillaDSP['yaml_notice'] = 'Use the parser \'jq -r .CamillaDSP.yaml_block\' to extract the yaml_block'
    CamillaDSP['yaml_block'] = yaml.dump(tmp, indent=2, sort_keys=False, default_flow_style=False)
    # debug
    #print(CamillaDSP['yaml_block'])

    eq_config['CamillaDSP'] = CamillaDSP


def make_eq_config_dict(filters_list, fs, moved_dB=0.0, ch='-', set_name='no_set_name'):

    if moved_dB:
        comments = f'Magnitude curve has been moved {moved_dB} dB to set the flat region at 0 dB'
    else:
        comments = ''

    # For pAudio and CamillaDSP yaml fields
    drc_name = set_name
    if len(drc_name) > 6:
        if drc_name[:4] == 'drc.' and drc_name[4:6] in ('L.', 'R.'):
            drc_name = drc_name[6:]

    eq_config = {

        "metadata": {
            "description": "Peaking EQ filters",
            "fs": fs,
            "num of PEQ sections": len(filters_list),
            "set_name": set_name,
            "comments": comments
        },

        "filters": filters_list
    }

    add_pAudio_format(eq_config, drc_name, ch)

    add_CamillaDSP_format(eq_config, drc_name, ch)

    return eq_config



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

                --opt=OPTIMIZER

                            ls      --> least_squares
                            ls_bass --> least_squares bass
                            min     --> minimize (default)
                            diff    --> differential_evolution (pending too slow)

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
from    scipy.optimize  import  minimize, least_squares, differential_evolution
from    fmt import Fmt
import  common as cm


def objective_function(params, f_target, m_target, fs, num_peqs):

    # The magnitude of all PEQ filters combined
    total_mag = np.zeros_like(f_target)
    for i in range(num_peqs):
        fc, Q, gain = params[i*3 : (i+1)*3]
        total_mag += cm.get_PEQ_mag(f_target, fc, Q, gain, fs)

    # --- WEIGHTS: The core of low-frequency resolution ---
    # A vector of weights that decays with frequency
    weights = 1.0 / np.log10(f_target)
    # Extra reinforcement for sub-bass (< 100Hz)
    weights[f_target < 100] *= 5.0

    error = np.sum(weights * (m_target - total_mag)**2)

    return error


def objective_function_ultra_bass(params, f_target, m_target, fs, num_peqs):

    # The magnitude of all PEQ filters combined
    total_mag = np.zeros_like(f_target)
    for i in range(num_peqs):
        fc, Q, gain = params[i*3 : (i+1)*3]
        total_mag += cm.get_PEQ_mag(f_target, fc, Q, gain, fs)

    # Peso hiper-agresivo: decaimiento potencial de la importancia
    # 20Hz tendrá un peso de (20000/20)^1.2 = 4000 aprox.
    # 20kHz tendrá un peso de 1.
    weights = (20000 / f_target)**1.2

    # Añadimos una penalización extra si el error en graves supera 0.5 dB
    error_vec = np.abs(m_target - total_mag)
    heavy_penalty = np.where((f_target < 200) & (error_vec > 0.5), 10.0, 1.0)

    error = np.sum(weights * 1 * (m_target - total_mag)**2)
    return error


def residuals(params, f, target, fs, num_peqs, weights):

    model = np.zeros_like(f)

    for i in range(num_peqs):
        fc, Q, gain = params[i*3 : (i+1)*3]
        model += cm.get_PEQ_mag(f, fc, Q, gain, fs)

    return (model - target) * weights


def get_optimized_peqs_from_frd(frd, fs, num_peqs):
    """ frd:        a magnitude vs freq response curve np.array [Hz : dB]
        fs:         freq of sampling
        num_peqs:   desired number of peqs tu emulate the frd
    """

    def make_eq_config_dict(params_list):

        def optimized_params_as_dict(params):

            d = []

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
                    d.append(filter_data)
                    i += 1

            return d


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


            mag_calc  = cm.get_PEQs_mag(freq, eq_config['filters'], fs)
            # pha_calc = cm.get_PEQs_pha(freq, eq_config['filters'], fs)  # unused

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

                tmp['filters'][f'{drc_name}_{i + 1}'] = {
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


        filters_list = optimized_params_as_dict(params_list)

        eq_config = {

            "metadata": {
                "description": "Peaking EQ filters",
                "fs": fs,
                "max num of PEQ sections":   num_peqs,
                "mini PEQ gain":             min_gain,
                "final num of PEQ sections": len(filters_list),
                "comments": f'Magnitude curve has been moved {moved_dB} dB to set the flat region at 0 dB'
            },

            "filters": filters_list
        }

        add_eq_config_advanced(eq_config, f_target, m_target)

        add_pAudio_format(eq_config, ch)

        add_CamillaDSP_format(eq_config, ch)

        return eq_config


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

    if optimizer == 'minimize':
        res = minimize(
            objective_function,
            initial_guess,
            args=(f_target, m_target, fs, num_peqs),   # extra arguments for objetive funcion
            bounds=bounds,
            method='L-BFGS-B',
            options={'ftol': 1e-9}
        )

    # ** do not use, too slow, pending to review **
    elif optimizer == 'differential_evolution':

        print(f'{Fmt.BOLD}differential_evolution is VERY SLOW, pending to review.{Fmt.END}')

        res = differential_evolution(
            objective_function_ultra_bass,
            bounds,
            args=(f_target, m_target, fs, num_peqs),
            strategy='best1bin',
            popsize=15,
            tol=0.01,
            mutation=(0.5, 1),
            recombination=0.7
        )

    elif optimizer == 'least_squares_bass':

        # ETAPA 1: Ajuste agresivo en GRAVES (20 - 400 Hz)
        mask_bass = f_target < 500
        f_bass = f_target[mask_bass]
        m_bass = m_target[mask_bass]
        w_bass = np.ones_like(f_bass)

        # Inicialización centrada en graves
        init_bass = []
        for fc in np.geomspace(30, 400, num_peqs):
            init_bass.extend([fc, 1.0, 0.0])

        res_bass = least_squares(
            residuals, init_bass,
            args=(f_bass, m_bass, fs, num_peqs, w_bass),
            bounds=([20, 0.1, -20] * num_peqs, [20000, 15, 20] * num_peqs),
            method='trf', ftol=1e-4
        )

        # 3. ETAPA 2: Ajuste GLOBAL usando la etapa 1 como semilla
        # Pesos: Graves pesan 5x más que el resto para asegurar < 0.5 dB
        weights_global = np.where(f_target < 500, 5.0, 1.0)

        # resultado final final
        res = least_squares(
            residuals, res_bass.x, # Empezamos donde terminó el ajuste de graves
            args=(f_target, m_target, fs, num_peqs, weights_global),
            bounds=([20, 0.1, -24] * num_peqs, [20000, 15, 24] * num_peqs),
            method='trf',
            x_scale='jac',
            ftol=1e-7
        )

    elif optimizer == 'least_squares':

        # Un peso que baja, pero nunca es menor a 0.5
        # Esto mantiene la "exigencia" en graves pero no ignora los agudos.
        weights_balanced = np.maximum((500 / f_target)**0.5, 0.5)

        # Refuerzo específico para que los graves sigan siendo la prioridad
        weights_balanced[f_target < 200] *= 2.0

        # Forzamos que los filtros empiecen cubriendo todo el espectro
        # para que el optimizador no tenga que "moverlos" desde muy lejos.
        init_spread = []
        f_centers = np.geomspace(30, 15000, num_peqs)
        for fc in f_centers:
            init_spread.extend([fc, 1.2, 0.0])

        # OPTIMIZACIÓN
        Fmin, Fmax =  20  ,  15e3
        Gmin, Gmax = -18.0, +6.0
        Qmin, Qmax =   0.1,  9

        res = least_squares(
            residuals, init_spread, # reparto inicial amplio
            args=(f_target, m_target, fs, num_peqs, weights_balanced),
            bounds=([Fmin, Qmin, Gmin] * num_peqs, [Fmax, Qmax, Gmax] * num_peqs),
            method='trf',
            x_scale='jac',
            ftol=1e-8
        )

    else:
        print(f'{Fmt.BOLD}optimizer not available: {optimizer}{Fmt.END}')
        sys.exit()

    # Extraer los resultados, que están dispobibles en `res.x`.
    # Vienen dados en forma de un array de valores float
    # de longitud = num_peqs * 3, que deberemos agrupar
    # para tener las tuplas (Fc ,Q , Gain) de cada filtro
    res_params = res.x.reshape(num_peqs, 3)

    eq_config  = make_eq_config_dict( res_params )

    return eq_config


if __name__ == "__main__":

    optimizer = 'minimize'

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
        for opt in sys.argv[1:]:

            if '-s' in opt:
                silent = True

            elif '-op=' in opt:
                tmp = opt.split('=')[-1]
                if tmp == 'diff':
                    optimizer = 'differential_evolution'
                elif tmp == 'min':
                    optimizer = 'minimize'
                elif tmp == 'ls_bass':
                    optimizer = 'least_squares_bass'
                elif tmp == 'ls':
                    optimizer = 'least_squares'

            elif '-offset=' in opt:
                mag_offset = float(opt.split('=')[-1])

            elif '-mg=' in opt:
                min_gain = float(opt.split('=')[-1])

            elif '-ch=' in opt:
                ch = opt.split('=')[-1]

            elif '-n=' in opt:
                num_peqs = int( opt.split('=')[-1] )

            elif '-frd=' in opt:
                frd_path = opt.split('frd=')[-1]

            elif '-fir=' in opt:
                fir_path = opt.split('fir=')[-1]

            elif '-fs=' in opt:
                fs = int( opt.split('fs=')[-1] )

            elif '-p' in opt:
                do_plot = True

            else:

                if opt.isdigit():
                    fs = int( opt )

                else:
                    print(f'BAD option: {opt}')
                    sys.exit()

    except Exception as e:
        print(f'BAD option \'{opt}\': {str(e)}')
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

            fir, fs = cm.load_fir_file( fir_path, ch, fs )

            frd = cm.fir2frd(fir, fs)

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
    if not fs in cm.VALID_FS:
        print(f'FS must be in {cm.VALID_FS}')
        sys.exit()

    # Check channel
    if not ch:
        ch = cm.detect_channel_from_set_name(set_name)

    valid_channels = ('L', 'R')

    if not ch in valid_channels:
        print(__doc__)
        print(f'\nA valid channel {valid_channels} is needed for .wav FIR\n')
        sys.exit()


    if mag_offset:
        frd[:, 1] += mag_offset
        moved_dB = mag_offset
    else:
        # auto detect flat region
        frd, moved_dB = cm.move_flat_region(frd)


    ########################
    # Solve the optimization
    peq_config = get_optimized_peqs_from_frd(frd, fs, num_peqs)
    ########################


    # Terminal printout
    if not silent:
        print(json.dumps(peq_config, indent=4))

    # Save to JSON file
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(peq_config, f, indent=4, ensure_ascii=False)

    # Graph results vs original curve
    cm.plot_frd_vs_peqs(frd, moved_dB, peq_config['filters'],
                        fs, ch=ch, emulation_method=optimizer,
                        png_path=json_path, do_plot=do_plot)

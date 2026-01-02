#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'Rsantct.DRC', yet another DRC FIR toolkit.

"""
    Generate a set of optimized Parametric EQ from a given target filter.
     - OR -
    Compare a PEQ set vs a given target filter.

    The target filter can be given in 3 flavours:

        - FRD: freq response data (mag vs freq text file)

        - FIR: a pcm impulse response previously windowed

                - a raw float32 file (for example .bin .pcm .f32)
                - a wav file (.wav)

    A) Usage for automatic optimization:

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


    A) Usage for manual compare a PEQ set vs a filter curve:

        filter2peq.py  --frd=path/to/FRDfile --peq=path/to/JSONfile  [more options]

            more options are the same as above except:
                --numpeq    )
                --opt       ) not needed
                --mg        )


    Output:

        All output files are placed in the same directory as the given filter file path.

        - PEQ set file .json
        - plot of results and its .png figure file
        - stdout will also printout the json result
"""

import  os
import  sys
import  json
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

    def optimized_params_as_dict(params):

        list_of_peqs = []

        for p in params:

            filter_data = {
                "type": "peaking",
                "fc":   round(float(p[0]), 2),
                "q":    round(float(p[1]), 3),
                "gain": round(float(p[2]), 2)
            }

            if abs( filter_data['gain'] ) > min_gain:
                list_of_peqs.append(filter_data)

        return cm.sort_peqs_list( list_of_peqs )


    def add_eq_config_analysis(eq_config, freq, target):

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


        mag_peqs  = cm.get_PEQs_mag(freq, eq_config['filters'], fs)
        # pha_peqs = cm.get_PEQs_pha(freq, eq_config['filters'], fs)  # unused

        metrics = calculate_metrics(freq, target, mag_peqs)

        eq_config['analysis'] = {
            'residual_error':    metrics,
            'units':            'decibels (dB)',
            'comments':         comments.strip()
        }


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

        # OPTIMIZACIÓN
        Fmin, Fmax =  20  ,  15e3
        Gmin, Gmax = -18.0, +6.0
        Qmin, Qmax =   0.1,  9

        res_bass = least_squares(
            residuals, init_bass,
            args=(f_bass, m_bass, fs, num_peqs, w_bass),
            bounds=([Fmin, Qmin, Gmin] * num_peqs, [Fmax, Qmax, Gmax] * num_peqs),
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

    # Format each peq into a to dictionary
    filters_list = optimized_params_as_dict( res_params )

    eq_config  = cm.make_eq_config_dict(filters_list, fs, moved_dB=moved_dB, ch=ch, set_name=set_name)

    add_eq_config_analysis(eq_config, f_target, m_target)

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
    peq_path    = ''

    ch          = ''                # Needed for .wav FIR files
    do_plot     = False
    silent      = False
    target_name = ''
    peqs_name   = ''

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

            elif '-peq=' in opt:
                peq_path = opt.split('peq=')[-1]

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


    # Get frd from the given filter file
    if frd_path:

        if os.path.isfile( frd_path ):

            frd = cm.load_fdr(frd_pat)

            if not fs:
                fs = 48000

            json_dir  = os.path.dirname(frd_path)
            set_name  = os.path.splitext( os.path.basename(frd_path) )[0]
            json_path = f'{json_dir}/{set_name}.json'

            target_name = os.path.basename(frd_path)

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

            target_name = os.path.basename(fir_path)

        else:
            print(__doc__)
            print('Needs a pcm FIR file')
            sys.exit()

    else:
        print(__doc__)
        sys.exit()


    # Get PEQ set from a file (trial with peq values)
    if peq_path:

        if os.path.isfile( peq_path ):

            json_dir  = os.path.dirname(peq_path)
            set_name  = os.path.splitext( os.path.basename(peq_path) )[0]
            json_path = f'{json_dir}/{set_name}.json'

            peqs_name = os.path.basename(peq_path)

            tmp = cm.load_peq_file(peq_path)

            if 'filters' in tmp:
                peq_config = tmp

            # It accepts a json with only a list of peq,
            # but it creates a 'filters' json section for them.
            else:
                peq_config = {}
                peq_config["filters"] = tmp

        else:
            print(__doc__)
            print(f'Not found: {peq_path}')
            sys.exit()

    else:
        peq_config = {}


    # Check FS
    if not fs in cm.VALID_FS:
        print(f'FS must be in {cm.VALID_FS}')
        sys.exit()

    # Check channel
    if not ch:
        ch = cm.detect_channel_from_set_name(set_name)

    if not ch in cm.VALID_CHANNELS:
        print(__doc__)
        print(f'\nA valid channel {cm.VALID_CHANNELS} is needed for .wav FIR\n')
        sys.exit()

    # Flat response region offset
    if mag_offset:
        frd[:, 1] += mag_offset
        moved_dB = mag_offset
    else:
        # auto detect flat region
        frd, moved_dB = cm.move_flat_region(frd)

    # Calculate PEQ
    if not peq_config:
        ########################
        # Solve the optimization
        peq_config = get_optimized_peqs_from_frd(frd, fs, num_peqs)
        ########################

        peqs_name = os.path.basename(json_path)

        # Terminal printout
        if not silent:
            print(json.dumps(peq_config, indent=4))


    # Already have a PEQ set from the command line
    else:
        # May have edited PEQ parameters in the command line json file,
        # so let's update pAudio and CamillaDSP fields
        drc_name = set_name
        if len(drc_name) > 6:
            if drc_name[:4] == 'drc.' and drc_name[4:6] in ('L.', 'R.'):
                drc_name = drc_name[6:]
        cm.add_pAudio_format    (peq_config, drc_name, ch)
        cm.add_CamillaDSP_format(peq_config, drc_name, ch)
        # Reorder sections by frequency
        peq_config["filters"] = cm.sort_peqs_list( peq_config["filters"] )


    # Save to JSON file
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(peq_config, f, indent=4, ensure_ascii=False)


    # Graph PEQs vs original FRD curve
    cm.plot_peqs_vs_frd(
        frd, moved_dB, peq_config['filters'],
        fs, ch=ch, emulation_method=optimizer,
        png_path=json_path, do_plot=do_plot,
        target_name=target_name,
        peqs_name=peqs_name,
    )

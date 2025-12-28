#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'Rsantct.DRC', yet another DRC FIR toolkit.

"""
    Generates a set of optimized Parametric EQ from a given filter.

    The filter can be given in two flawors:
        - FIR (impulse response)
        - FRD (freq response data)

    Usage:

        filter2peq.py  --fir=path/to/FIRfile --fs=FS [--plot]

        filter2peq.py  --frd=path/to/FRDfile --fs=FS [--plot]

    Output:

        A JSON with the PEQ set placed in the same directory
        as the given filepath.

        (stdout will also receive the json string)

        A plot of results.
"""

import  os
import  sys
import  json
import  numpy as np
import  scipy.signal    as      signal
from    scipy.optimize  import  minimize     # Woooooow!
import  matplotlib.pyplot as    plt


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

    def params_to_json(params):
        """ Convert the parameters into an organized JSON.

            params: Array shaped (num_peqs, 3), each row having [Fc, Q, Gain]
        """

        eq_config = {

            "metadata": {
                "description": "Peaking EQ filters",
                "fs": fs
            },

            "filters": []
        }

        for i, p in enumerate(params):

            filter_data = {
                "id": i + 1,
                "type": "peaking",
                "fc":   round(float(p[0]), 2),
                "q":    round(float(p[1]), 3),
                "gain": round(float(p[2]), 2)
            }

            eq_config["filters"].append(filter_data)

        return eq_config


    def eq_config_advanced(eq_config, freq, target):

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
        pha_calc = get_PEQs_pha(freq, eq_config['filters'], fs)

        metrics = calculate_metrics(freq, target, mag_calc)

        eq_config['analysis'] = {
            'residual_error':    metrics,
            'units':            'decibels (dB)',
            'comments':         comments.strip()
        }

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
        bounds.append((20, 20000))  # fc: 20Hz a 20kHz
        bounds.append((0.1, 10.0))  # Q: De muy ancho a muy estrecho
        bounds.append((-24, 24))    # Ganancia: +/- 24 dB

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

    eq_config_advanced(eq_config, f_target, m_target)

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
    ax1.set_title('Response curve emulation with PEQ and low freq accuracy')
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

    plt.savefig(f'{json_path}.png')

    plt.show()


def load_pcm_fir_file(fir_path):
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


if __name__ == "__main__":

    # Read commmand line options
    num_peqs = 6                    # Número de bandas Peaking EQ
    fs       = 0
    frd_path = ''
    fir_path = ''
    doplot   = False

    for opc in sys.argv[1:]:

        if '-frd=' in opc:
            frd_path = opc.split('frd=')[-1]

        if '-fir=' in opc:
            fir_path = opc.split('fir=')[-1]

        if '-fs=' in opc:
            fs = int( opc.split('fs=')[-1] )

        elif '-p' in opc:
            doplot = True


    if not fs:
        fs = 44100

    if frd_path:

        if os.path.isfile( frd_path ):

            frd = np.loadtxt(frd_path)

            json_dir = os.path.dirname(frd_path)
            json_name = os.path.splitext( os.path.basename(frd_path) )[0]
            json_path = f'{json_dir}/{json_name}.json'

        else:
            print('Needs a FRD file')
            print(__doc__)
            sys.exit()

    elif fir_path:

        if os.path.isfile( fir_path ):

            fir = load_pcm_fir_file( fir_path )

            fir_freq, fir_mag, _ = fir2frd(fir, fs)

            frd = np.column_stack((fir_freq, fir_mag))

            json_dir = os.path.dirname(fir_path)
            json_name = os.path.splitext( os.path.basename(fir_path) )[0]
            json_path = f'{json_dir}/{json_name}.json'

        else:
            print('Needs a pcm FIR file')
            print(__doc__)
            sys.exit()

    else:
        print(__doc__)
        sys.exit()


    # Solve the optimization
    peq_config = get_optimized_peqs_from_frd(frd, fs, num_peqs)

    print(json.dumps(peq_config, indent=4))

    # Plot results vs original curve
    if doplot:
        visualize_eq_results(frd, peq_config)

    # Save to JSON file
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(peq_config, f, indent=4, ensure_ascii=False)


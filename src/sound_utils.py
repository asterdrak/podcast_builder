""" Common utils for sounds, at least some of them found in the net. """

import numpy as np

def detect_leading_silence(sound, silence_threshold=-50.0, chunk_size=10):
    '''
    sound is a pydub.AudioSegment
    silence_threshold in dB
    chunk_size in ms

    iterate over chunks until you find the first one with sound
    '''
    trim_ms = 0  # ms

    assert chunk_size > 0  # to avoid infinite loop
    if silence_threshold == 'auto':
        silence_threshold = sound[:3000].dBFS
    while sound[trim_ms:trim_ms + chunk_size].dBFS < silence_threshold and trim_ms < len(sound):
        trim_ms += chunk_size

    return trim_ms - 300 if trim_ms > 300 else trim_ms


def detect_leading_microphone_error(sound, chunk_size=5, sample_size=5000):
    data = np.array([chunk.dBFS for chunk in sound[:sample_size:chunk_size]])
    smoothed_deriv = np.convolve(np.gradient(data), [1/3]*3)**2

    speak_start = next((i*chunk_size for (i, x) in enumerate(iter(smoothed_deriv)) if x > 0.5*np.mean(smoothed_deriv)), 0)
    # print(sound.filename, speak_start, sound.fade_in)
    return speak_start - sound.fade_in if speak_start > sound.fade_in*2 else 0

# def detect_yawning(sound, chunk_size=5, kernel=[-1, -1, 0, 1, 1]):
#     from matplotlib import pyplot as plt
#     from matplotlib.ticker import FuncFormatter

#     data = np.array([chunk.dBFS for chunk in sound[::chunk_size]])
#     # out = np.convolve(np.convolve(data, np.array(kernel)), [1/3]*5)
#     # plt.plot(out) # convolved signal
#     # plt.plot(np.logical_and(out >= -3, out <= 3)*-10) # if convolved signal is small - 1 else 0
#     plt.plot([chunk.dBFS for chunk in sound[::chunk_size]]) # raw
#     # second_derrivative = np.gradient(np.gradient(data))
#     plt.plot(np.gradient(data))
#     # plt.plot(second_derrivative)  # derivative
#     # plt.plot(np.logical_and(second_derrivative >= -1/2, second_derrivative <= 1/2)*-10)
#     plt.gca().get_xaxis().set_major_formatter(FuncFormatter(lambda x, p: format(int(x*chunk_size), ',')))
#     plt.show(block=False)

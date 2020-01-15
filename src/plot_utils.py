from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter

def plot(sound, chunk_size=10):
    plt.plot([chunk.dBFS for chunk in sound[::chunk_size]])
    plt.gca().get_xaxis().set_major_formatter(FuncFormatter(lambda x, p: format(int(x*chunk_size), ',')))
    plt.show(block=False)


def plot_many(sounds_schedule, chunk_size=10, slc=slice(0, 5000)):
    collection = sounds_schedule if isinstance(sounds_schedule, list) else sounds_schedule.schedule

    fig, axes = plt.subplots(len(collection)//6+1, 6)

    for index, (ax, sound) in enumerate(zip(axes.flatten(), collection)):
        ax.plot([chunk.dBFS for chunk in sound[slc.start:slc.stop:slc.step or chunk_size]])
        ax.set_title('{}, schedule index: {}'.format(sound.filename.rsplit('.', 1)[0], index), size='x-small')
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: format(int(x*chunk_size), ',')))

    plt.subplots_adjust(left=0.05, right=0.95, hspace=0.3)
    plt.show(block=False)


def plot_many_with_filter(sounds_schedule, kernel=[-1, 0, 1], chunk_size=10, slc=slice(0, 5000)):
    collection = sounds_schedule if isinstance(sounds_schedule, list) else sounds_schedule.schedule
    import numpy as np

    fig, axes = plt.subplots(len(collection)//6+1, 6)

    for index, (ax, sound) in enumerate(zip(axes.flatten(), collection)):
        data = np.array([chunk.dBFS for chunk in sound[slc.start:slc.stop:slc.step or chunk_size]])
        ax.plot(np.convolve(data, np.array(kernel)))
        ax.set_title('{}, schedule index: {}'.format(sound.filename.rsplit('.', 1)[0], index), size='x-small')
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: format(int(x*chunk_size), ',')))

    plt.subplots_adjust(left=0.05, right=0.95, hspace=0.3)
    plt.show(block=False)

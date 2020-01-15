from pydub.playback import play
from src.plot_utils import plot


def verification(podcast, slc=slice(0, 2000)):
    for i, sound in enumerate(podcast.schedule):
        char = 'r'
        while True:
            if char == 'r':
                print('{}:'.format(i), sound.filename)
                play(sound[slc])

            char = input('r - replay modified file, o - original (raw) file, nothing - next sound, enter to comfirm: ')
            if char == 'o':
                play(sound.raw_file[slc])
            if char == 'p':
                plot(sound[slc])
            if not char:
                break

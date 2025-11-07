import os
# import relevant libraries
import os
import pedalboard
import ipywidgets

import numpy as np
# Import audio processing library
import librosa
# We'll use this to listen to audio
from IPython.display import Audio, display
from plotly import graph_objects as go
from pedalboard import NoiseGate,LowpassFilter,HighpassFilter
from pedalboard import Compressor,Gain,Limiter


class AudioLine:
    #sampling rate는 기본값으로 어지간하면 변경금지
    def __init__(self,
                 samplingrate=44100,
                 down_sr = 8000
                 ):
        self.sample_rate = samplingrate
        self.down_duration = None
        self.downsr = down_sr
        self.noisegate = None
        self.filter = None
        self.dynamic_effect = None

    def prepare_audio_input(self,
                            auido_path = None,
                            down_sr = 16000,
                            trimdb = 40,
                            trimselect = False,
                            )->np.array: 
        self.downsr = down_sr
        self.signal, audio_sr = librosa.load(auido_path, sr=self.sample_rate)
        down_signal = librosa.resample(self.signal, orig_sr=audio_sr, target_sr=self.downsr)
        self.down_duration=librosa.get_duration(y=down_signal, sr=self.downsr)
    
        if trimselect:
            down_signal, index = librosa.effects.trim(
                    down_signal,
                    top_db=trimdb,  # 피크로부터 40dB 이하를 침묵으로 간주
                    ref=np.max   # 신호의 최대값을 기준으로
                )
            down_signal = down_signal[index[0]:index[1]]
        else:
            pass

        return down_signal

    def setNoisegate(self,
                     threshold_db: float = -100.0,
                     ratio: float = 10,
                     attack_ms: float = 1.0,
                     release_ms: float = 100.0,
                     ):
        self.noisegate = pedalboard.Pedalboard([NoiseGate(threshold_db=threshold_db,
                                                          ratio= ratio,
                                                          attack_ms = attack_ms,
                                                          release_ms = release_ms)])

    def setFilter(self,
                  use_lowpass = True,
                  use_highpass = True,
                  lowpass_cutoff=4000,
                  highpass_cutoff=100,
                  )->None:
        active_filters = []

        if use_lowpass:
            active_filters.append(LowpassFilter(cutoff_frequency_hz=lowpass_cutoff))
            
        if use_highpass:
            active_filters.append(HighpassFilter(cutoff_frequency_hz=highpass_cutoff))

        self.filter = pedalboard.Pedalboard(active_filters)

    def setDynamics(self,
                    threshold_db: float = -3,
                    ratio: float = 1,
                    attack_ms: float = 1.0,
                    release_ms: float = 100,
                    gain:float = 0,
                    limit_threshold:float = 0.3
                  )->None:

        self.dynamic_effect = pedalboard.Pedalboard([
            Compressor(
                threshold_db= threshold_db,
                ratio=ratio,
                attack_ms=attack_ms, 
                release_ms=release_ms),
            Gain(gain_db=gain),
            Limiter(threshold_db=limit_threshold),
            ])
        
    def process(self,audio_input):
        if self.noisegate is None:
            raise ValueError("NoiseGate가 초기화되지 않았습니다. (self.noisegate is None)")
        if self.filter is None:
            raise ValueError("filter가 초기화되지 않았습니다. (self.filter is None)")
        if self.dynamic_effect is None:
            raise ValueError("NoiseGate가 초기화되지 않았습니다. (self.dynamic_effect is None)")
        
        audio_input = self.noisegate(audio_input, self.downsr, reset=False)
        audio_input = self.filter(audio_input, self.downsr, reset=False)
        audio_input = self.dynamic_effect(audio_input, self.downsr, reset=False)
        return audio_input
    
def plot_audio_signal(signal, sr, title='Audio Signal', color='green', save_path=None):
    duration = len(signal) / sr
    time = np.linspace(0, duration, len(signal))
    
    layout = {
        'height': 300,
        'xaxis': {'title': 'Time (s)'},
        'yaxis': {'title': 'Amplitude'},
        'title': title,
        'margin': dict(l=0, r=0, t=40, b=0, pad=0),
    }
    
    fig = go.Figure(
        go.Scatter(
            x=time,
            y=signal,
            line={'color': color},
            name='Signal',
            hovertemplate='Time: %{x:.2f} s<br>Amplitude: %{y:.2f}<br><extra></extra>'
        ),
        layout=layout
    )
    
    if save_path:
        fig.write_html(save_path)
        print(f"Plot saved to {save_path}")
    else:
        fig.show()

def main():
    targetSr = 16000

    audioclass = AudioLine(down_sr = targetSr)
    audioclass.setNoisegate(threshold_db= -40)
    audioclass.setFilter(lowpass_cutoff=4000,highpass_cutoff=100)
    audioclass.setDynamics()

    audiofilename = 'demo/20_25_3888_220924_0017.wav'
    
    input_signal = audioclass.prepare_audio_input(auido_path=audiofilename,
                                                  trimselect=True) 
    output_signal = audioclass.process(input_signal)

    plot_audio_signal(output_signal, targetSr, save_path='output_plot.html')


if __name__ == '__main__':
    main()
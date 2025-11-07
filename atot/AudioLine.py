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


# V0
# AudioLine
# 오디오 신호처리를 위한 파이프라인 구현
# Wave file 입력및 오디오 프로세싱 처리
# 마이크 신호는 별도 모델을 작성하여 처리예정 
class AudioLine:
    
    """
    Class 초기 생성, MP3 파일 기본 샘플링 레이트하고
    다운샘플링을 위한 샘플링레이트를 초기 설정

    Args:
        samplingrate (int): 기본 오디오샘플링 레이트, 44100hz에 변경 하지 않아도 됨
        down_sr (int): 다운 샘플링해야될 샘플링 레이트, 모델에 따라 변경필요

    Returns:
        None
    """
    def __init__(self,
                 samplingrate:int=44100,
                 down_sr:int = 8000
                 )-> None:
        self.sample_rate = samplingrate
        self.down_duration = None
        self.downsr = down_sr
        self.noisegate = None
        self.filter = None
        self.dynamic_effect = None

    """
    오디오 파일을 로드하고 다운샘플링 및 트리밍 수행
    
    Args:
        auido_path (str): 입력 오디오 파일 경로
        down_sr (int): 다운샘플링 목표 샘플링 레이트 (기본값: 16000)
        trimdb (float): 트리밍 시 침묵으로 간주할 데시벨 임계값 (기본값: 40)
        trimselect (bool): 트리밍 수행 여부 (기본값: False)

    Returns:
        np.array: 다운샘플링된 오디오 신호
    """
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
    
    """
    노이즈 게이트 설정
    
    Args:
        threshold_db (float): 게이트가 열리는 임계값 데시벨 (기본값: -100.0)
        ratio (float): 게이트 감쇠 비율 (기본값: 10)
        attack_ms (float): 게이트가 열리는 속도 밀리초 (기본값: 1.0)
        release_ms (float): 게이트가 닫히는 속도 밀리초 (기본값: 100.0)

    Returns:
        None
    """
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
    
    """
    필터 설정 (로우패스 및 하이패스 필터)
    
    Args:
        use_lowpass (bool): 로우패스 필터 사용 여부 (기본값: True)
        use_highpass (bool): 하이패스 필터 사용 여부 (기본값: True)
        lowpass_cutoff (float): 로우패스 필터 컷오프 주파수 Hz (기본값: 4000)
        highpass_cutoff (float): 하이패스 필터 컷오프 주파수 Hz (기본값: 100)

    Returns:
        None
    """
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

    """
    다이나믹 이펙트 설정 (컴프레서, 게인, 리미터)
    
    Args:
        threshold_db (float): 컴프레서 임계값 데시벨 (기본값: -3)
        ratio (float): 컴프레서 압축 비율 (기본값: 1)
        attack_ms (float): 컴프레서 어택 시간 밀리초 (기본값: 1.0)
        release_ms (float): 컴프레서 릴리즈 시간 밀리초 (기본값: 100)
        gain (float): 게인 증폭량 데시벨 (기본값: 0)
        limit_threshold (float): 리미터 임계값 데시벨 (기본값: 0.3)

    Returns:
        None
    """
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
    
    """
    오디오 신호 처리 파이프라인 실행 (노이즈게이트 -> 필터 -> 다이나믹 이펙트)
    
    Args:
        audio_input (np.array): 입력 오디오 신호

    Returns:
        np.array: 처리된 오디오 신호
    """        
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

"""
오디오 신호를 시각화하는 플롯 생성

Args:
    signal (np.array): 오디오 신호 배열
    sr (int): 샘플링 레이트
    title (str): 플롯 제목 (기본값: 'Audio Signal')
    color (str): 플롯 색상 (기본값: 'green')
    save_path (str): HTML 파일 저장 경로, None이면 화면에 표시 (기본값: None)

Returns:
    None
"""    
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

"""
메인 실행 함수: 오디오 처리 파이프라인 데모

Returns:
    None
"""
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
"""
回声消除器模块
Echo Cancellation Module
"""
from collections import deque
import time
import numpy as np
from src.echo_config import EchoConfig


class EchoCanceller:
    """
    自适应回声消除器
    Adaptive Echo Cancellation (AEC) implementation
    """
    
    def __init__(self):
        """初始化回声消除器"""
        # 获取配置参数
        adaptive_params = EchoConfig.get_adaptive_params()
        buffer_params = EchoConfig.get_buffer_params()
        warmup_params = EchoConfig.get_warmup_params()
        noise_params = EchoConfig.get_noise_gate_params()
        
        # 自适应滤波器参数
        self.adaptive_filter_length = adaptive_params['filter_length']
        self.adaptive_filter = np.zeros(self.adaptive_filter_length)
        self.learning_rate = adaptive_params['learning_rate']
        
        # 缓冲区
        self.echo_buffer = deque(maxlen=buffer_params['echo_buffer_size'])
        self.input_buffer = deque(maxlen=buffer_params['input_buffer_size'])
        
        # 预热参数
        self.start_time = time.time()
        self.warmup_duration = warmup_params['duration']
        self.warmup_gain_factor = warmup_params['gain_factor']
        
        # 噪声门限参数
        self.noise_gate_threshold = noise_params['threshold']
        self.noise_gate_attenuation = noise_params['attenuation']
        self.gain_factor = EchoConfig.GAIN_FACTOR
        
        # 统计信息
        self.processed_frames = 0
        self.echo_detected_frames = 0
    
    def add_reference_audio(self, reference_audio):
        """
        添加参考音频（播放的音频）到缓冲区
        
        Args:
            reference_audio: 参考音频数据 (numpy array)
        """
        if reference_audio is not None:
            self.echo_buffer.append(reference_audio.copy())
    
    def process_audio(self, input_audio, reference_audio=None):
        """
        处理音频，执行回声消除
        
        Args:
            input_audio: 输入音频数据 (numpy array)
            reference_audio: 当前的参考音频数据 (numpy array, optional)
        
        Returns:
            numpy array: 处理后的音频数据
        """
        self.processed_frames += 1
        
        # 如果提供了参考音频，添加到缓冲区
        if reference_audio is not None:
            self.add_reference_audio(reference_audio)
        
        # 转换为float32进行处理
        audio_float = input_audio.astype(np.float32)
        
        # 执行回声消除
        cleaned_audio = self._echo_cancellation(audio_float)
        
        # 预热期间的特殊处理
        cleaned_audio = self._warmup_processing(cleaned_audio)
        
        # 转换回int16格式
        return np.clip(cleaned_audio, -32768, 32767).astype(np.int16)
    
    def _echo_cancellation(self, input_audio):
        """
        核心回声消除算法
        
        Args:
            input_audio: 输入音频数据 (float32)
        
        Returns:
            numpy array: 消除回声后的音频数据
        """
        if len(self.echo_buffer) == 0:
            # 没有参考音频时，只进行噪声门限处理
            return self._noise_gate(input_audio)
        
        # 获取最近的参考音频
        ref_data = self._get_reference_signal()
        
        if len(ref_data) < self.adaptive_filter_length:
            return self._noise_gate(input_audio)
        
        # 截取适当长度的参考信号
        ref_signal = ref_data[-self.adaptive_filter_length:]
        
        # 计算预测的回声
        predicted_echo = np.convolve(ref_signal, self.adaptive_filter, mode='valid')
        
        # 确保长度匹配并执行回声消除
        cleaned_audio = self._subtract_echo(input_audio, predicted_echo, ref_signal)
        
        # 应用噪声门限
        return self._noise_gate(cleaned_audio)
    
    def _get_reference_signal(self):
        """获取参考信号"""
        if len(self.echo_buffer) >= 10:
            return np.concatenate(list(self.echo_buffer)[-10:])
        else:
            return np.concatenate(list(self.echo_buffer))
    
    def _subtract_echo(self, input_audio, predicted_echo, ref_signal):
        """执行回声减法和滤波器更新"""
        min_len = min(len(input_audio), len(predicted_echo))
        if min_len <= 0:
            return input_audio
        
        # 回声减法
        input_segment = input_audio[:min_len]
        echo_segment = predicted_echo[:min_len]
        cleaned_audio = input_segment - echo_segment
        
        # 更新自适应滤波器 (LMS算法)
        if len(ref_signal) >= len(input_segment):
            error = cleaned_audio
            ref_segment = ref_signal[:len(error)]
            
            # 计算梯度并更新滤波器
            if len(error) <= len(self.adaptive_filter):
                gradient = self.learning_rate * error * ref_segment[:len(error)]
                self.adaptive_filter[:len(error)] += gradient
                
                # 统计回声检测
                if np.mean(np.abs(error)) < np.mean(np.abs(input_segment)) * 0.8:
                    self.echo_detected_frames += 1
        
        # 填充到原始长度
        if len(cleaned_audio) < len(input_audio):
            padding = np.zeros(len(input_audio) - len(cleaned_audio))
            cleaned_audio = np.concatenate([cleaned_audio, padding])
        
        return cleaned_audio[:len(input_audio)]
    
    def _noise_gate(self, audio_data):
        """
        噪声门限处理
        
        Args:
            audio_data: 音频数据
        
        Returns:
            numpy array: 处理后的音频数据
        """
        # 计算音频的RMS值
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        if rms < self.noise_gate_threshold:
            # 低于噪声门限时，使用配置的衰减系数
            return audio_data * self.noise_gate_attenuation
        else:
            # 高于门限时，正常处理
            return audio_data * self.gain_factor
    
    def _warmup_processing(self, input_audio):
        """
        预热期间的特殊处理
        
        Args:
            input_audio: 输入音频数据
        
        Returns:
            numpy array: 处理后的音频数据
        """
        elapsed_time = time.time() - self.start_time
        
        if elapsed_time < self.warmup_duration:
            # 预热期间，逐渐增加增益
            warmup_gain = elapsed_time / self.warmup_duration
            return input_audio * warmup_gain * self.warmup_gain_factor
        
        return input_audio
    
    def get_statistics(self):
        """
        获取统计信息
        
        Returns:
            dict: 统计信息字典
        """
        echo_detection_rate = 0
        if self.processed_frames > 0:
            echo_detection_rate = self.echo_detected_frames / self.processed_frames
        
        return {
            'processed_frames': self.processed_frames,
            'echo_detected_frames': self.echo_detected_frames,
            'echo_detection_rate': echo_detection_rate,
            'warmup_completed': time.time() - self.start_time > self.warmup_duration,
            'buffer_size': len(self.echo_buffer),
            'filter_coefficients_norm': np.linalg.norm(self.adaptive_filter)
        }
    
    def reset(self):
        """重置回声消除器状态"""
        self.adaptive_filter = np.zeros(self.adaptive_filter_length)
        self.echo_buffer.clear()
        self.input_buffer.clear()
        self.start_time = time.time()
        self.processed_frames = 0
        self.echo_detected_frames = 0

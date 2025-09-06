# 回声消除配置文件
# Echo Cancellation Configuration

class EchoConfig:
    """回声消除配置类"""
    
    # 自适应滤波器参数
    ADAPTIVE_FILTER_LENGTH = 1024  # 自适应滤波器长度
    LEARNING_RATE = 0.01  # LMS算法学习率
    
    # 缓冲区参数
    ECHO_BUFFER_SIZE = 100  # 回声缓冲区大小 (约2秒)
    INPUT_BUFFER_SIZE = 50  # 输入缓冲区大小
    
    # 预热参数
    WARMUP_DURATION = 2.0  # 预热时间(秒)
    WARMUP_GAIN_FACTOR = 0.5  # 预热期间的增益因子
    
    # 噪声门限参数
    NOISE_GATE_THRESHOLD = 500  # 噪声门限
    NOISE_GATE_ATTENUATION = 0.1  # 低于门限时的衰减系数
    
    # 音频处理参数
    GAIN_FACTOR = 1.0  # 正常增益因子
    SAMPLE_RATE = 48000  # 采样率
    
    # 客户端音频约束参数
    CLIENT_AUDIO_CONSTRAINTS = {
        "echoCancellation": True,
        "echoCancellationType": "system",  # 或 "browser"
        "noiseSuppression": True,
        "autoGainControl": True,
        "googEchoCancellation": True,
        "googAutoGainControl": True,
        "googNoiseSuppression": True,
        "googHighpassFilter": True,
        "googTypingNoiseDetection": True,
        "googAudioMirroring": False,
        "latency": 0.01,  # 10ms延迟
        "sampleRate": 48000,
        "sampleSize": 16,
        "channelCount": 1
    }
    
    @classmethod
    def get_adaptive_params(cls):
        """获取自适应滤波器参数"""
        return {
            'filter_length': cls.ADAPTIVE_FILTER_LENGTH,
            'learning_rate': cls.LEARNING_RATE
        }
    
    @classmethod
    def get_buffer_params(cls):
        """获取缓冲区参数"""
        return {
            'echo_buffer_size': cls.ECHO_BUFFER_SIZE,
            'input_buffer_size': cls.INPUT_BUFFER_SIZE
        }
    
    @classmethod
    def get_warmup_params(cls):
        """获取预热参数"""
        return {
            'duration': cls.WARMUP_DURATION,
            'gain_factor': cls.WARMUP_GAIN_FACTOR
        }
    
    @classmethod
    def get_noise_gate_params(cls):
        """获取噪声门限参数"""
        return {
            'threshold': cls.NOISE_GATE_THRESHOLD,
            'attenuation': cls.NOISE_GATE_ATTENUATION
        }

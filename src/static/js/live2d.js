/**
 * Live2D 管理器
 * 负责 Live2D 模型的初始化、嘴部动画控制等功能
 */
class Live2DManager {
    constructor() {
        this.live2dApp = null;
        this.live2dModel = null;
        this.isTalking = false;
        this.mouthAnimationId = null;
        this.mouthParam = 'ParamMouthOpenY';
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
    }

    /**
     * 初始化 Live2D
     */
    async initializeLive2D() {
        try {
            const canvas = document.getElementById('live2d-stage');

            // 供内部使用
            window.PIXI = PIXI;

            this.live2dApp = new PIXI.Application({
                view: canvas,
                height: window.innerHeight,
                width: window.innerWidth,
                resolution: window.devicePixelRatio,
                autoDensity: true,
                antialias: true,
                backgroundAlpha: 0,
            });

            // 加载 Live2D 模型
            this.live2dModel = await PIXI.live2d.Live2DModel.from('static/hiyori_pro_zh/runtime/hiyori_pro_t11.model3.json');
            this.live2dApp.stage.addChild(this.live2dModel);
            this.live2dModel.scale.set(0.35);
            this.live2dModel.x = (window.innerWidth - this.live2dModel.width) * 0.5;
            this.live2dModel.y = -50;

        } catch (err) {
            console.error('加载 Live2D 模型失败:', err);
        }
    }

    /**
     * 初始化音频分析器
     * @param {MediaStream} remoteStream - 远程音频流
     */
    initializeAudioAnalyzer(remoteStream) {
        try {
            // 创建音频上下文和分析器
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

            // 获取remoteVideo的音频轨道
            if (remoteStream) {
                const audioTracks = remoteStream.getAudioTracks();
                if (audioTracks.length > 0) {
                    const source = this.audioContext.createMediaStreamSource(remoteStream);
                    source.connect(this.analyser);
                    console.log('音频分析器初始化成功');
                }
            }
        } catch (error) {
            console.error('初始化音频分析器失败:', error);
        }
    }

    /**
     * 嘴部动画循环
     */
    animateMouth() {
        if (!this.isTalking) return;
        if (!this.live2dModel) return;
        const internal = this.live2dModel && this.live2dModel.internalModel;
        if (internal && internal.coreModel) {
            const coreModel = internal.coreModel;

            // 获取音频分贝值
            let mouthValue = 0;
            if (this.analyser && this.dataArray) {
                this.analyser.getByteFrequencyData(this.dataArray);
                const average = this.dataArray.reduce((a, b) => a + b) / this.dataArray.length;
                // 将0-255的值转换为0-1的范围，并应用一些平滑处理
                mouthValue = Math.min(1, (average / 255) * 3);
            }
            // console.log("mouthValue", mouthValue)
            coreModel.setParameterValueById(this.mouthParam, mouthValue);
            coreModel.update();
        }
        this.mouthAnimationId = requestAnimationFrame(() => this.animateMouth());
    }

    /**
     * 开始说话动画
     * @param {MediaStream} remoteStream - 远程音频流
     */
    startTalking(remoteStream) {
        if (this.isTalking || !this.live2dModel) return;

        // 确保音频分析器已初始化
        if (!this.analyser && remoteStream) {
            this.initializeAudioAnalyzer(remoteStream);
        }

        this.isTalking = true;
        this.animateMouth();
    }

    /**
     * 停止说话动画
     */
    stopTalking() {
        this.isTalking = false;
        if (this.mouthAnimationId) {
            cancelAnimationFrame(this.mouthAnimationId);
            this.mouthAnimationId = null;
        }
        if (!this.live2dModel) return;
        const internal = this.live2dModel && this.live2dModel.internalModel;
        if (internal && internal.coreModel) {
            const coreModel = internal.coreModel;
            coreModel.setParameterValueById(this.mouthParam, 0);
            coreModel.update();
        }
    }

    /**
     * 清理资源
     */
    destroy() {
        this.stopTalking();
        
        // 清理音频分析器
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        this.analyser = null;
        this.dataArray = null;

        // 清理 Live2D 应用
        if (this.live2dApp) {
            this.live2dApp.destroy(true);
            this.live2dApp = null;
        }
        this.live2dModel = null;
    }
}

// 导出全局实例
window.Live2DManager = Live2DManager;

// neoflux_ui.js

(function(global) {
    class NeoFluxController {
        constructor(canvasId) {
            this.canvas = document.getElementById(canvasId);
            this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
            this.width = this.canvas ? this.canvas.width : 300;
            this.height = this.canvas ? this.canvas.height : 50;
            this.ledCount = 30; // Default
            this.colors = ["#FF0000", "#0000FF"];
            this.mode = "spatial_wave";
            this.speed = 150;
            this.animationId = null;
            this.lastFrameTime = 0;

            if (this.canvas) {
                this.startPreview();
            }
        }

        updateConfig(config) {
            if (config.colors) this.colors = config.colors;
            if (config.mode) this.mode = config.mode;
            if (config.speed) this.speed = config.speed;
        }

        startPreview() {
            if (!this.ctx) return;
            const animate = (time) => {
                const delta = time - this.lastFrameTime;
                if (delta > (1000 / 60)) { // Cap at ~60fps
                    this.render(time);
                    this.lastFrameTime = time;
                }
                this.animationId = requestAnimationFrame(animate);
            };
            this.animationId = requestAnimationFrame(animate);
        }

        stopPreview() {
            if (this.animationId) {
                cancelAnimationFrame(this.animationId);
            }
        }

        render(time) {
            // Clear canvas
            this.ctx.fillStyle = '#000';
            this.ctx.fillRect(0, 0, this.width, this.height);

            const ledWidth = this.width / this.ledCount;

            for (let i = 0; i < this.ledCount; i++) {
                let color = this.calculateLedColor(i, time);
                this.ctx.fillStyle = color;
                this.ctx.fillRect(i * ledWidth, 5, ledWidth - 2, this.height - 10);
            }
        }

        calculateLedColor(index, time) {
            // Simple visualization simulation based on mode
            if (this.mode === 'spatial_wave') {
                const phase = (time / (20000 / this.speed)) + (index / 5);
                const r = Math.sin(phase) * 127 + 128;
                const b = Math.cos(phase) * 127 + 128;
                return `rgb(${Math.floor(r)}, 0, ${Math.floor(b)})`;
            } else if (this.mode === 'solid') {
                return this.colors[0] || '#ffffff';
            }
            return '#333';
        }

        getConfigPayload() {
            return {
                colors: this.colors,
                mode: this.mode,
                speed: this.speed
            };
        }
    }

    global.NeoFluxController = NeoFluxController;

})(window);
